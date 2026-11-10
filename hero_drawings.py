"""Hairline drawings for the page heroes, in the same style as the SIF monogram drawing.

Each drawing is a list of strokes. Every stroke draws itself on load (pathLength=1 and a
dash offset). Strokes marked `flow` also get a "trace" copy: a short bright segment that
travels along them while the pointer is over the hero (always on touch screens).
One stroke per drawing is gold.
"""
import math

GOLD = "gold"


class Drawing:
    def __init__(self, view):
        self.view = view
        self.strokes = []  # (d, gold, flow)

    def path(self, d, gold=False, flow=False):
        self.strokes.append((d, gold, flow))

    def line(self, x1, y1, x2, y2, **kw):
        self.path(f"M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}", **kw)

    def poly(self, pts, close=False, **kw):
        d = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + ("Z" if close else "")
        self.path(d, **kw)

    def rect(self, x, y, w, h, **kw):
        self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], close=True, **kw)

    def circle(self, cx, cy, r, **kw):
        self.path(f"M{cx - r:.1f} {cy:.1f}a{r} {r} 0 1 0 {2 * r} 0a{r} {r} 0 1 0 {-2 * r} 0", **kw)

    def arc(self, cx, cy, r, a1, a2, **kw):
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
        large = 1 if abs(a2 - a1) > math.pi else 0
        sweep = 1 if a2 > a1 else 0
        self.path(f"M{x1:.1f} {y1:.1f}A{r} {r} 0 {large} {sweep} {x2:.1f} {y2:.1f}", **kw)

    def svg(self):
        n = len(self.strokes)
        out = []
        for i, (d, gold, flow) in enumerate(self.strokes):
            cls = ' class="gold"' if gold else ""
            delay = 0.3 + 1.6 * i / max(n - 1, 1)  # strokes draw in sequence over ~1.6s
            out.append(f'<path{cls} pathLength="1" style="animation-delay:{delay:.2f}s" d="{d}"/>')
        k = 0
        for d, gold, flow in self.strokes:
            if flow:
                dur = 7 + (k * 2.3) % 9  # varied speeds so the flow never looks mechanical
                cls = "trace gold-trace" if gold else "trace"
                out.append(f'<path class="{cls}" pathLength="1" style="animation-duration:{dur:.1f}s" d="{d}"/>')
                k += 1
        return f'<svg viewBox="{self.view}" preserveAspectRatio="xMaxYMid meet">{"".join(out)}</svg>'


def community():
    """The network: three rings of members, ties between neighbours and across rings.
    The gold stroke is one introduction travelling from the edge of the network to its other side."""
    g = Drawing("0 0 800 800")
    cx, cy = 400, 400
    rings = [(110, 6, 0.0), (220, 12, 0.26), (330, 18, 0.1)]
    nodes = []
    for ring, (r, n, off) in enumerate(rings):
        layer = []
        for k in range(n):
            a = off + 2 * math.pi * k / n
            layer.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        nodes.append(layer)
    # ties along each ring (not every neighbour, so it reads as a real network)
    for ring, layer in enumerate(nodes):
        for k, (x, y) in enumerate(layer):
            if (k + ring) % 3 != 2:
                x2, y2 = layer[(k + 1) % len(layer)]
                g.line(x, y, x2, y2, flow=(k % 4 == 0))
    # ties between rings: each node to its nearest neighbour on the next ring inward
    for ring in (1, 2):
        for k, (x, y) in enumerate(nodes[ring]):
            inner = min(nodes[ring - 1], key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
            g.line(x, y, inner[0], inner[1], flow=(k % 3 == 1))
    # a few long ties across the centre
    for k in range(0, 6, 2):
        a, b = nodes[0][k], nodes[0][(k + 3) % 6]
        g.line(a[0], a[1], b[0], b[1])
    # the introduction: outer -> middle -> inner -> inner -> middle -> outer
    route = [nodes[2][13], nodes[1][9], nodes[0][4], nodes[0][1], nodes[1][3], nodes[2][4]]
    g.poly(route, gold=True, flow=True)
    for ring, layer in enumerate(nodes):
        for x, y in layer:
            g.circle(x, y, (9, 7, 5.5)[ring])
    return g


def opportunities():
    """Review as four gates: many lines enter, fewer pass each gate, one leaves in gold."""
    g = Drawing("120 0 780 600")
    gates = [(290, 150), (440, 105), (590, 62), (740, 26)]  # x, half-opening
    mid = 300
    for x, half in gates:
        g.line(x, 40, x, mid - half)
        g.line(x, mid + half, x, 560)
        g.line(x - 10, mid - half, x + 10, mid - half)
        g.line(x - 10, mid + half, x + 10, mid + half)
    starts = [70 + i * 33 for i in range(14)]
    reach = [0, 1, 0, 2, 1, 0, 3, 4, 2, 1, 0, 1, 0, 0]  # how many gates each line clears
    for y0, cleared in zip(starts, reach):
        pts = [(150, y0)]
        for j, (x, half) in enumerate(gates[:cleared]):
            pts.append((x, mid + (y0 - mid) * (half / 300) * 0.8))
        if cleared < 4:
            x_stop = gates[cleared][0] - 14
            last = pts[-1]
            pts.append((x_stop, last[1]))
            g.poly(pts, flow=(cleared >= 2))
        else:
            pts.append((880, mid))
            g.poly(pts, gold=True, flow=True)
    return g


def events():
    """A room plan: a round table with twelve seats, and a door that swings open in gold."""
    g = Drawing("0 0 800 800")
    cx, cy = 420, 380
    g.rect(110, 70, 620, 620)
    g.rect(122, 82, 596, 596)
    g.circle(cx, cy, 170, flow=True)
    g.circle(cx, cy, 150)
    for k in range(12):
        a = 2 * math.pi * k / 12
        px, py = cx + 214 * math.cos(a), cy + 214 * math.sin(a)
        ux, uy = math.cos(a), math.sin(a)
        vx, vy = -uy, ux
        w, d = 26, 20
        corners = [(px + vx * w + ux * d, py + vy * w + uy * d), (px - vx * w + ux * d, py - vy * w + uy * d),
                   (px - vx * w - ux * d, py - vy * w - uy * d), (px + vx * w - ux * d, py + vy * w - uy * d)]
        g.poly(corners, close=True, flow=(k % 3 == 0))
    # door in the bottom wall: opening, leaf and the swing arc
    g.line(250, 690, 250, 590)
    g.arc(250, 690, 100, -math.pi / 2, 0, gold=True, flow=True)
    return g


def membership():
    """Two tiers, one route in: two rooms, one inside the other, and a single entrance."""
    g = Drawing("0 0 900 700")
    # outer room (Club), drawn as a double wall with one opening at the bottom
    g.poly([(380, 620), (80, 620), (80, 60), (820, 60), (820, 620), (500, 620)])
    g.poly([(380, 632), (68, 632), (68, 48), (832, 48), (832, 632), (500, 632)])
    g.line(380, 620, 380, 632)
    g.line(500, 620, 500, 632)
    g.arc(500, 626, 120, math.pi, math.pi * 1.5)
    # inner room (Founding), its own opening on the same axis
    g.poly([(410, 450), (300, 450), (300, 150), (720, 150), (720, 450), (470, 450)], flow=True)
    g.poly([(410, 462), (288, 462), (288, 138), (732, 138), (732, 462), (470, 462)])
    g.line(410, 450, 410, 462)
    g.line(470, 450, 470, 462)
    g.arc(470, 456, 60, math.pi, math.pi * 1.5)
    # the one route in
    g.poly([(440, 690), (440, 300)], gold=True, flow=True)
    g.circle(440, 300, 7)
    return g


def founding():
    """A lasting place: a column standing on its foundation, the ground line in gold."""
    g = Drawing("0 0 700 800")
    g.line(20, 720, 680, 720, gold=True, flow=True)
    g.rect(150, 680, 400, 40)
    g.rect(180, 645, 340, 35)
    g.rect(210, 612, 280, 33)
    g.rect(240, 590, 220, 22)
    g.poly([(262, 590), (272, 170), (428, 170), (438, 590)], close=True, flow=True)
    for k in range(1, 6):
        xb = 262 + k * 176 / 6
        xt = 272 + k * 156 / 6
        g.line(xb, 586, xt, 174)
    g.rect(236, 140, 228, 30)
    g.rect(210, 110, 280, 30, flow=True)
    g.line(60, 110, 640, 110)
    g.line(60, 80, 640, 80)
    return g


def club():
    """A curated view: a window onto a one-point perspective, the horizon line in gold."""
    g = Drawing("0 0 900 700")
    vx, vy = 560, 330
    g.rect(120, 80, 700, 520)
    g.rect(140, 100, 660, 480, flow=True)
    for x in (140, 260, 380, 500, 620, 740, 800):
        g.line(x, 580, vx + (x - vx) * 0.25, vy + (580 - vy) * 0.25, flow=(x in (260, 620)))
    for k in range(1, 5):
        t = 1 - k * 0.18
        y = vy + (580 - vy) * t
        g.line(vx + (140 - vx) * t, y, vx + (800 - vx) * t, y)
    for y in (100, 180):
        g.line(140, y, vx + (140 - vx) * 0.25, vy + (y - vy) * 0.25)
        g.line(800, y, vx + (800 - vx) * 0.25, vy + (y - vy) * 0.25)
    g.line(140, vy, 800, vy, gold=True, flow=True)
    return g


DRAWINGS = {
    "community": community,
    "portfolio": opportunities,
    "events": events,
    "membership": membership,
    "founding-membership": founding,
    "club-membership": club,
}
