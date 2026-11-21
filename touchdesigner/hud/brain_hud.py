
# NEURON SCALE brain - two-layer scale detection
#   layer 1: pitch-class SET (key signature)  -> hue   (stable, with hysteresis)
#   layer 2: tonic inside that set -> mode     -> brightness (fast, smoothed)
import math, random

IONIAN = (0, 2, 4, 5, 7, 9, 11)
# interval of tonic above the set's major root -> (mode, brightness)
MODE_OF = {0: ("Ionian", 0.83), 2: ("Dorian", 0.50), 4: ("Phrygian", 0.17),
           5: ("Lydian", 1.00), 7: ("Mixolydian", 0.67), 9: ("Aeolian", 0.33),
           11: ("Locrian", 0.00)}
MODES_DEMO = {"Lydian": (0, 2, 4, 6, 7, 9, 11), "Ionian": IONIAN, "Phrygian": (0, 1, 3, 5, 7, 8, 10),
              "Locrian": (0, 1, 3, 5, 6, 8, 10)}
NAMES = "C C# D D# E F F# G G# A A# B".split()
WINDOW = 2.5       # seconds of musical memory
BASS_WINDOW = 4.0  # bass memory is longer: the bass defines the tonic
PULSE_SEC = 0.7    # soma -> tips travel time
HOLD = 0.5         # a new key signature must win this long before switching
MIN_GAP = 0.10

S = me.parent().storage
def st(key, default):
    if key not in S:
        S[key] = default
    return S[key]

def reset():
    for k in list(S.keys()):
        del S[k]

def note_on(note, vel):
    now = absTime.seconds
    w = st('w', [0.0] * 12); b = st('bass', [0.0] * 12)
    v = vel / 127.0
    w[note % 12] += v
    if note < 60:
        b[note % 12] += v * (1.5 if note < 48 else 1.0)
    st('recent', []).append(now)
    ev = st('events', [])                          # note log for the HUD overlay
    S['ev_seq'] = st('ev_seq', 0) + 1
    ev.append([S['ev_seq'], int(note), round(v, 3)])
    if len(ev) > 64:
        del ev[:len(ev) - 64]
    if now - st('last_pulse', -9) > MIN_GAP:
        S['last_pulse'] = now
        S['last_vel'] = v

def best_set(w):
    total = sum(w)
    if total < 1e-4:
        return None
    scores = [sum(w[(r + i) % 12] for i in IONIAN) for r in range(12)]
    r = max(range(12), key=lambda k: scores[k])
    return r, scores, 1.0 - scores[r] / total

def best_tonic(r, w, b):
    members = [(r + i) % 12 for i in IONIAN]
    def score(p):
        return 2.0 * b[p] + 1.0 * w[p] + 0.35 * w[(p + 7) % 12] + 0.2 * w[(p + 4) % 12] + 0.2 * w[(p + 3) % 12]
    return max(members, key=score)

def set_demo(on=True):
    S['demo'] = on
    S['demo_t'] = absTime.seconds

def demo_step(now):
    seq = [(0, "Ionian"), (4, "Phrygian"), (6, "Lydian"), (9, "Locrian")]
    i = int((now - S.get('demo_t', 0)) / 6.0) % len(seq)
    tonic, m = seq[i]
    if now - st('demo_last', 0) > 0.24:
        S['demo_last'] = now
        n = 36 + tonic if random.random() < 0.3 else 60 + tonic + random.choice(MODES_DEMO[m])
        note_on(n, random.randint(70, 120))

def frame():
    now = absTime.seconds
    dt = max(1e-3, now - st('t_prev', now)); S['t_prev'] = now
    if S.get('demo'):
        demo_step(now)
    w = st('w', [0.0] * 12); b = st('bass', [0.0] * 12)
    dw, db = math.exp(-dt / WINDOW), math.exp(-dt / BASS_WINDOW)
    for i in range(12):
        w[i] *= dw; b[i] *= db
    c = op('ctrl')
    res = best_set(w)
    if res:
        r, scores, outside = res
        cur = S.get('set_root')
        if cur is None:
            S['set_root'] = cur = r
        elif r != cur and scores[r] > scores[cur] * 1.08:     # clearly better
            if S.get('cand') != r:
                S['cand'] = r; S['cand_t'] = now
            elif now - S['cand_t'] > HOLD:
                S['set_root'] = cur = r
        else:
            S['cand'] = None
        tonic = best_tonic(cur, w, b)
        mode, bright = MODE_OF[(tonic - cur) % 12]
        S['cur'] = (tonic, mode, bright)
        S['scale_name'] = NAMES[tonic] + ' ' + mode
        target_hue = ((cur * 7) % 12) / 12.0               # key signature on the circle of fifths
        h = st('hue', target_hue)
        target_hue += round(h - target_hue)
        k = 1 - math.exp(-dt / 0.8)
        S['hue'] = h + (target_hue - h) * k
        S['bri'] = st('bri', bright) + (bright - st('bri', bright)) * (1 - math.exp(-dt / 0.6))
        S['spike'] = st('spike', 0.1) + (min(1.0, 0.08 + outside * 3.0) - st('spike', 0.1)) * (1 - math.exp(-dt / 0.3))
    recent = [t for t in st('recent', []) if now - t < 1.0]; S['recent'] = recent
    wob = min(1.0, 0.15 + len(recent) / 8.0)
    S['wob'] = st('wob', wob) + (wob - st('wob', wob)) * (1 - math.exp(-dt / 0.6))
    since = now - st('last_pulse', -9)
    pulse = min(1.0, since / PULSE_SEC)
    inten = 0.15 + st('last_vel', 0) * max(0.0, 1.0 - since / PULSE_SEC)
    S['time'] = st('time', 0) + dt * (0.3 + S['wob'] * 2.0)
    c.par.const0value = S.get('hue', 0.52) % 1.0
    c.par.const1value = 0.55 + 0.4 * S.get('bri', 0.6)
    c.par.const2value = S.get('bri', 0.6)
    c.par.const3value = pulse
    c.par.const4value = inten
    c.par.const5value = S.get('spike', 0.1)
    c.par.const6value = S['wob']
    c.par.const7value = S['time']
    S['flow'] = st('flow', 0.0) + dt * (0.35 + S['wob'] * 1.4)     # drift through the tissue
    c.par.const8value = S['flow']
    c.par.const9value = min(since, 60.0)
    c.par.const10value = st('last_vel', 0.0)
    c.par.const11value = now
    S['fps'] = st('fps', 60.0) * 0.95 + (1.0 / dt) * 0.05
