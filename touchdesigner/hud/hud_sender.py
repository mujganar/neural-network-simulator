# HUD sender - pushes live brain state into the Web Render TOP 'hud' (Neural Network Simulator overlay)
import json

NAMES = "C C# D D# E F F# G G# A A# B".split()
B = me.parent()


def send():
    S = B.storage
    hud = B.op('hud')
    if hud is None:
        return
    cur = S.get('cur') or (0, 'Ionian', 0.83)
    last = S.get('hud_seq', 0)
    events = [[e[1], e[2]] for e in S.get('events', []) if e[0] > last]
    if S.get('events'):
        S['hud_seq'] = S['events'][-1][0]
    c = B.op('ctrl')
    d = {
        'key': NAMES[int(cur[0]) % 12], 'mode': str(cur[1]).upper(), 'tonic': int(cur[0]),
        'setRoot': int(S.get('set_root') or 0),
        'hue': round(float(c['hue'][0]), 4), 'bri': round(float(c['bri'][0]), 3),
        'spike': round(float(c['spike'][0]), 3), 'wob': round(float(c['wobble'][0]), 3),
        'flow': round(float(c['flow'][0]), 2), 'vel': round(float(c['vel'][0]), 3),
        'since': round(float(c['since'][0]), 2), 'nps': len(S.get('recent', [])),
        'fps': round(float(S.get('fps', 60.0)), 1),
        'w': [round(x, 3) for x in S.get('w', [0.0] * 12)],
        'events': events,
    }
    hud.executeJavaScript('window.hud && hud.update(%s)' % json.dumps(d))
