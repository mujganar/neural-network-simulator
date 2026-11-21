"""
SYNAPSE MONO - custom display font for the Neural Network Simulator HUD (@mujganar)
Monospace, chamfered single-line skeletons; every free stroke end carries a round
'synaptic bouton' node.  Lowercase = small caps.  Includes Turkish letters.
Builds SynapseMono-Regular.ttf and SynapseMono-Bold.ttf with fontTools + shapely.
"""
import sys
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from shapely.geometry import LineString, Point, Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.geometry.polygon import orient

UPM, ADV, CAP = 1000, 600, 700
SX, SY = 100.0, CAP / 6.0          # grid unit -> font units (grid x 0..4, y 0..6)
X0 = 100.0
XH = 0.72                          # small-caps height ratio

O_RING = [(1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 1), (3, 0), (1, 0)]
P_BOWL = [(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)]

G = {
    'A': [[(0, 0), (0, 5), (1, 6), (3, 6), (4, 5), (4, 0)], [(0, 3), (4, 3)]],
    'B': [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)], [(3, 3), (4, 2), (4, 1), (3, 0), (0, 0)]],
    'C': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1)]],
    'D': [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 1), (3, 0), (0, 0)]],
    'E': [[(4, 6), (0, 6), (0, 0), (4, 0)], [(0, 3), (3, 3)]],
    'F': [[(4, 6), (0, 6), (0, 0)], [(0, 3), (3, 3)]],
    'G': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1), (4, 3), (2, 3)]],
    'H': [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    'I': [[(1, 6), (3, 6)], [(2, 6), (2, 0)], [(1, 0), (3, 0)]],
    'J': [[(1, 6), (4, 6)], [(3, 6), (3, 1), (2, 0), (1, 0), (0, 1)]],
    'K': [[(0, 0), (0, 6)], [(4, 6), (1, 3), (0, 3)], [(1, 3), (4, 0)]],
    'L': [[(0, 6), (0, 0), (4, 0)]],
    'M': [[(0, 0), (0, 6), (2, 3), (4, 6), (4, 0)]],
    'N': [[(0, 0), (0, 6), (4, 0), (4, 6)]],
    'O': [O_RING],
    'P': [P_BOWL],
    'Q': [O_RING, [(2.6, 1.4), (4.3, -0.3)]],
    'R': [P_BOWL, [(2, 3), (4, 0)]],
    'S': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 4), (1, 3), (3, 3), (4, 2), (4, 1), (3, 0), (1, 0), (0, 1)]],
    'T': [[(0, 6), (4, 6)], [(2, 6), (2, 0)]],
    'U': [[(0, 6), (0, 1), (1, 0), (3, 0), (4, 1), (4, 6)]],
    'V': [[(0, 6), (2, 0), (4, 6)]],
    'W': [[(0, 6), (1, 0), (2, 3), (3, 0), (4, 6)]],
    'X': [[(0, 6), (4, 0)], [(4, 6), (0, 0)]],
    'Y': [[(0, 6), (2, 3), (4, 6)], [(2, 3), (2, 0)]],
    'Z': [[(0, 6), (4, 6), (0, 0), (4, 0)]],
    '0': [O_RING, [(1.2, 1.6), (2.8, 4.4)]],
    '1': [[(1, 5), (2, 6), (2, 0)], [(1, 0), (3, 0)]],
    '2': [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (0, 0), (4, 0)]],
    '3': [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (1.5, 3)], [(3, 3), (4, 2), (4, 1), (3, 0), (1, 0), (0, 1)]],
    '4': [[(3, 0), (3, 6), (0, 2), (4, 2)]],
    '5': [[(4, 6), (0, 6), (0, 3.5), (3, 3.5), (4, 2.5), (4, 1), (3, 0), (1, 0), (0, 1)]],
    '6': [[(3.5, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2.5), (3, 3.5), (0, 3.5)]],
    '7': [[(0, 6), (4, 6), (4, 5), (1.5, 0)]],
    '8': [[(1, 3), (0, 4), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (1, 3), (0, 2), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3)]],
    '9': [[(0.5, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 3.5), (1, 2.5), (4, 2.5)]],
    '.': ['dot:2,0.25'],
    ',': [[(2, 0.4), (1.4, -1.0)]],
    ':': ['dot:2,0.6', 'dot:2,3.8'],
    ';': ['dot:2,3.8', [(2, 0.6), (1.4, -0.9)]],
    '-': [[(1, 3), (3, 3)]],
    '_': [[(0, -0.6), (4, -0.6)]],
    '/': [[(0.5, -0.3), (3.5, 6.3)]],
    '\\': [[(0.5, 6.3), (3.5, -0.3)]],
    '(': [[(3, 6.6), (2, 5.6), (2, 0.4), (3, -0.6)]],
    ')': [[(1, 6.6), (2, 5.6), (2, 0.4), (1, -0.6)]],
    '[': [[(3, 6.6), (1.5, 6.6), (1.5, -0.6), (3, -0.6)]],
    ']': [[(1, 6.6), (2.5, 6.6), (2.5, -0.6), (1, -0.6)]],
    '+': [[(2, 1.5), (2, 4.5)], [(0.5, 3), (3.5, 3)]],
    '=': [[(0.5, 2), (3.5, 2)], [(0.5, 4), (3.5, 4)]],
    '#': [[(1.3, 0.3), (1.3, 5.7)], [(2.7, 0.3), (2.7, 5.7)], [(0, 2), (4, 2)], [(0, 4), (4, 4)]],
    '%': [[(0.5, 0), (3.5, 6)], 'dot:0.8,5', 'dot:3.2,1'],
    '@': [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 2)],
          [(4, 2), (2, 2), (1.5, 2.5), (1.5, 3.5), (2, 4), (3, 4), (3, 2)]],
    '&': [[(4, 0), (1, 4), (1, 5), (1.5, 6), (2.5, 6), (3, 5), (3, 4.5), (0, 2), (0, 1), (1, 0), (2.5, 0), (4, 2)]],
    "'": [[(2, 6.2), (2, 4.6)]],
    '"': [[(1.3, 6.2), (1.3, 4.6)], [(2.7, 6.2), (2.7, 4.6)]],
    '!': [[(2, 6), (2, 2)], 'dot:2,0.25'],
    '?': [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (2, 2.6), (2, 1.9)], 'dot:2,0.25'],
    '·': ['dot:2,3'],
    'µ': [[(0.5, -1.6), (0.5, 4.2)], [(0.5, 1), (1.5, 0), (2.5, 0), (3.5, 1)], [(3.5, 4.2), (3.5, 0)]],
    'ƒ': [[(3.6, 6), (2.6, 6), (1.9, 5.3), (1.9, 0.3), (1, -0.6)], [(0.8, 3.5), (3, 3.5)]],
    '→': [[(0, 3), (4, 3)], [(2.5, 4.5), (4, 3), (2.5, 1.5)]],
    '←': [[(4, 3), (0, 3)], [(1.5, 4.5), (0, 3), (1.5, 1.5)]],
    '>': [[(0.5, 5), (3.5, 3), (0.5, 1)]],
    '<': [[(3.5, 5), (0.5, 3), (3.5, 1)]],
    '|': [[(2, -1), (2, 7)]],
    '*': [[(2, 1.5), (2, 4.5)], [(0.7, 2.2), (3.3, 3.8)], [(0.7, 3.8), (3.3, 2.2)]],
    '°': [[(1.3, 6.2), (2.7, 6.2), (2.7, 4.8), (1.3, 4.8), (1.3, 6.2)]],
    'ƒ_': [],
}
# Turkish letters: base + diacritic
DIAC = {
    'cedilla': [[(2, 0), (2, -0.7), (1.2, -1.2)]],
    'breve': [[(1, 7.4), (1.5, 6.9), (2.5, 6.9), (3, 7.4)]],
    'dieresis': ['dot:1.2,7.1', 'dot:2.8,7.1'],
    'dotabove': ['dot:2,7.2'],
}
TR = {'Ç': ('C', 'cedilla'), 'Ş': ('S', 'cedilla'), 'Ğ': ('G', 'breve'), 'Ü': ('U', 'dieresis'),
      'Ö': ('O', 'dieresis'), 'İ': ('I', 'dotabove')}
del G['ƒ_']


def glyph_shape(strokes, sw, nr, yscale=1.0, extra=None):
    """strokes are scaled by yscale (small caps); extra (diacritics) are absolute."""
    lines, dots, pts = [], [], {}
    for group, ys in ((strokes, yscale), (extra or [], 1.0)):
        for s in group:
            if isinstance(s, str):
                x, y = map(float, s[4:].split(','))
                dots.append((x, y * ys))
                continue
            line = [(x, y * ys) for x, y in s]
            lines.append(line)
            for p in line:
                pts[p] = pts.get(p, 0) + 1
    geoms = []
    for line in lines:
        fu = [(X0 + x * SX, y * SY) for x, y in line]
        geoms.append(LineString(fu).buffer(sw / 2, cap_style=2, join_style=2, mitre_limit=2.5))
        if line[0] != line[-1]:
            for end in (line[0], line[-1]):
                if pts[end] == 1:                       # free end -> synaptic bouton
                    geoms.append(Point(X0 + end[0] * SX, end[1] * SY).buffer(nr, 24))
    for x, y in dots:
        geoms.append(Point(X0 + x * SX, y * SY).buffer(nr * 1.15, 24))
    return unary_union(geoms) if geoms else None


def draw(shape, glyphset):
    pen = TTGlyphPen(glyphset)
    if shape is None or shape.is_empty:
        return pen.glyph()
    polys = shape.geoms if isinstance(shape, MultiPolygon) else [shape]
    for poly in polys:
        poly = orient(poly.simplify(0.6), sign=-1.0)           # TrueType: outer clockwise
        for ring in [poly.exterior] + list(poly.interiors):
            c = [(round(x), round(y)) for x, y in list(ring.coords)[:-1]]
            dedup = [p for i, p in enumerate(c) if p != c[i - 1]]
            if len(dedup) < 3:
                continue
            pen.moveTo(dedup[0])
            for p in dedup[1:]:
                pen.lineTo(p)
            pen.closePath()
    return pen.glyph()


def build(style, sw, nr, path):
    chars = {}
    for ch, strokes in G.items():
        chars[ch] = (strokes, None, 1.0)
        if ch.isalpha() and ch.upper() == ch and ch.lower() != ch and len(ch) == 1:
            chars[ch.lower()] = (strokes, None, XH)
    for ch, (base, d) in TR.items():
        chars[ch] = (G[base], DIAC[d], 1.0)
    chars['ç'] = (G['C'], DIAC['cedilla'], XH)
    chars['ş'] = (G['S'], DIAC['cedilla'], XH)
    chars['ğ'] = (G['G'], [[(1, 5.6), (1.5, 5.1), (2.5, 5.1), (3, 5.6)]], XH)
    chars['ü'] = (G['U'], ['dot:1.2,5.3', 'dot:2.8,5.3'], XH)
    chars['ö'] = (G['O'], ['dot:1.2,5.3', 'dot:2.8,5.3'], XH)
    chars['ı'] = ([[(1, 6), (3, 6)], [(2, 6), (2, 0)], [(1, 0), (3, 0)]], None, XH)
    chars['i'] = ([[(1, 6), (3, 6)], [(2, 6), (2, 0)], [(1, 0), (3, 0)]], ['dot:2,5.6'], XH)

    names = {' ': 'space'}
    order = ['.notdef', 'space']
    cmap = {32: 'space'}
    for ch in chars:
        n = 'uni%04X' % ord(ch)
        names[ch] = n
        order.append(n)
        cmap[ord(ch)] = n

    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    glyphs = {'.notdef': TTGlyphPen(None).glyph(), 'space': TTGlyphPen(None).glyph()}
    for ch, (strokes, extra, ys) in chars.items():
        glyphs[names[ch]] = draw(glyph_shape(strokes, sw, nr, ys, extra), None)
    fb.setupGlyf(glyphs)
    metrics = {n: (ADV, 0) for n in order}
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=900, descent=-260)
    fb.setupNameTable({'familyName': 'Synapse Mono', 'styleName': style,
                       'uniqueFontIdentifier': 'SynapseMono-' + style + ' @mujganar 2026',
                       'fullName': 'Synapse Mono ' + style, 'psName': 'SynapseMono-' + style,
                       'version': 'Version 1.000', 'copyright': '(c) 2026 Mujgan Armagan Turkozu (@mujganar)',
                       'designer': '@mujganar'})
    fb.setupOS2(sTypoAscender=900, sTypoDescender=-260, usWinAscent=950, usWinDescent=300,
                sxHeight=int(CAP * XH), sCapHeight=CAP, usWeightClass=700 if style == 'Bold' else 400)
    fb.setupPost(isFixedPitch=1)
    fb.save(path)
    return len(chars)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    n1 = build('Regular', 74, 56, out + '/SynapseMono-Regular.ttf')
    n2 = build('Bold', 118, 82, out + '/SynapseMono-Bold.ttf')
    print('glyphs', n1, n2)
