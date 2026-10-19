"""
Sample Insurer -- Map View (Mirror)

A small local web-app mirror of the internal GIS/"Map View" tool used to look
up a property's location during underwriting review, built so a Robot
Framework + RPA.Browser.Selenium automation can be developed and tested
against it instead of a real production GIS system.

ALL data in this app is fictitious. Nothing here represents a real insurer,
real property, or real production system.

Run with:
    ~/rpa-env/bin/python app.py
Serves on http://127.0.0.1:5058 by default (override with PORT env var).
"""
import math
import os
import random

from flask import Flask, redirect, render_template, request, url_for
from markupsafe import Markup

app = Flask(__name__)

# In-memory only - resets on restart. No persistence needed for this mirror.
STATE = {
    "address": "",
    "ad_hoc_analysis": False,
    "hybrid_view": False,
    "overlay": False,
}


def build_base_map_svg():
    """Return inline-SVG markup for a fictitious neighbourhood street map.

    Purely decorative (no external tiles - the demo machine may be offline).
    One drawing serves both base maps: CSS classes on the surrounding
    container switch the palette between "Road Map" and a darker,
    satellite-ish "Hybrid" look (see map_view.html)."""
    rnd = random.Random(61)
    W, H = 1600, 1000
    out = [
        f'<svg class="base-map" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" '
        'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">',
        '<defs><filter id="mvNoise" x="0" y="0" width="100%" height="100%">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7"/>'
        '<feColorMatrix type="saturate" values="0"/></filter></defs>',
        f'<rect class="land" width="{W}" height="{H}"/>',
    ]

    # Water: a river along the top-right and a pond lower-left.
    out.append('<path class="water" d="M1330 -20 C1390 80 1440 120 1500 170 C1560 220 1600 260 1640 330 '
               'L1640 -20 Z"/>')
    out.append('<path class="water" d="M1560 520 C1585 560 1600 600 1640 640 L1640 470 C1610 480 1580 495 1560 520Z"/>')
    out.append('<ellipse class="water" cx="210" cy="905" rx="70" ry="34" transform="rotate(-18 210 905)"/>')

    # Street-block grid (rotated so the streets run diagonally, like the
    # recorded neighbourhood). Gaps between blocks read as minor streets.
    out.append('<g transform="rotate(-31 800 500)">')
    a = math.radians(-31)
    for gx in range(-700, 2300, 150):
        for gy in range(-760, 1760, 112):
            # keep only cells that end up on-screen after rotation
            cx, cy = gx + 75 - 800, gy + 56 - 500
            rx = cx * math.cos(a) - cy * math.sin(a) + 800
            ry = cx * math.sin(a) + cy * math.cos(a) + 500
            if not (-160 < rx < W + 160 and -160 < ry < H + 160):
                continue
            jitter = rnd.randint(-6, 6)
            bx, by, bw, bh = gx + 10, gy + 10 + jitter, 130, 92 - abs(jitter)
            out.append(f'<rect class="blk" x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="3"/>')
            # buildings: terraces along the long edges + the odd detached one
            n = rnd.randint(3, 6)
            slot = (bw - 8) // n
            for k in range(n):
                w = slot - rnd.randint(2, 6)
                h = rnd.randint(18, 34)
                x = bx + 4 + k * slot
                y = by + 4 if k % 2 == 0 else by + bh - h - 4
                out.append(f'<rect class="bld b{rnd.randint(1, 4)}" x="{x}" y="{y}" width="{w}" height="{h}"/>')
            if rnd.random() < .45:
                out.append(f'<rect class="bld b{rnd.randint(1, 4)}" x="{bx + rnd.randint(30, 80)}" '
                           f'y="{by + rnd.randint(30, 50)}" width="{rnd.randint(18, 36)}" height="{rnd.randint(14, 22)}"/>')
    out.append('</g>')

    # Parks / green spaces.
    for d in ('M110 300 L330 230 L370 470 L200 560 L120 480 Z',
              'M540 830 L640 790 L720 1010 L600 1010 Z',
              'M1180 760 L1290 735 L1320 820 L1205 850 Z',
              'M1420 380 L1530 350 L1560 430 L1450 465 Z'):
        out.append(f'<path class="park" d="{d}"/>')

    # Trees (only shown on the Hybrid base map).
    out.append('<g class="trees">')
    for _ in range(170):
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        for _ in range(rnd.randint(2, 5)):
            out.append(f'<circle class="t{rnd.randint(1, 3)}" cx="{x + rnd.randint(-14, 14)}" '
                       f'cy="{y + rnd.randint(-14, 14)}" r="{rnd.randint(6, 13)}"/>')
    out.append('</g>')

    # Major roads (casing first, then fill, then names).
    majors = [
        ('M-40 250 C300 300 560 380 800 470 S1300 640 1660 700', 'High St', (560, 372, 18)),
        ('M520 -30 C600 200 700 360 800 470 S980 760 1060 1040', 'Shepherds Walk', (955, 700, 58)),
        ('M-40 700 C300 640 560 600 760 560 S1200 440 1660 300', 'Church Row', (230, 655, -10)),
        ('M260 -30 C300 200 330 420 420 640 S560 900 600 1040', 'Heath St', (300, 160, 80)),
        ('M1150 -30 C1130 200 1120 330 1140 500 S1190 800 1170 1040', 'Hill Gardens', (1132, 260, 92)),
        ('M900 1040 C1100 940 1300 880 1660 820', 'Pond St', (1420, 862, -12)),
    ]
    for d, _, _ in majors:
        out.append(f'<path class="maj-c" d="{d}"/>')
    for d, _, _ in majors:
        out.append(f'<path class="maj" d="{d}"/>')
    for _, name, (x, y, r) in majors:
        out.append(f'<text class="lbl" x="{x}" y="{y}" transform="rotate({r} {x} {y})">{name}</text>')
    for x, y, r, name in ((690, 430, 52, 'Vane Cl'), (850, 560, -55, 'Rosslyn Hill'),
                          (1290, 690, 35, 'Grove'), (400, 520, -62, 'Holly Walk'),
                          (1010, 300, -30, 'Willow Rd'), (160, 380, 0, 'Gardens')):
        out.append(f'<text class="lbl sm" x="{x}" y="{y}" transform="rotate({r} {x} {y})">{name}</text>')

    # Points of interest.
    for x, y, name in ((560, 610, 'Resource Centre'), (610, 760, 'School For Boys'),
                       (230, 880, 'Sports Field'), (760, 905, 'Independent College'),
                       (1360, 640, 'Community School'), (1290, 830, 'Green')):
        out.append(f'<g class="poi"><circle cx="{x}" cy="{y}" r="9"/><circle class="in" cx="{x}" cy="{y}" r="4"/>'
                   f'<text class="lbl poi-l" x="{x + 15}" y="{y + 5}">{name}</text></g>')

    # Clustered risk markers (fictitious).
    for x, y, n in ((470, 140, 3), (720, 120, 2), (280, 520, 3), (210, 545, 2), (390, 500, 4),
                    (520, 365, 3), (1000, 120, 1), (1060, 160, 3), (1240, 380, 4), (1320, 330, 2),
                    (1080, 640, 3), (1170, 680, 2), (1420, 600, 4), (500, 690, 3), (620, 820, 2),
                    (1330, 120, 1), (1500, 470, 3)):
        out.append(f'<g class="clu"><circle cx="{x}" cy="{y}" r="15"/><text x="{x}" y="{y + 5}">{n}</text></g>')
    for x, y in ((640, 180), (880, 80), (1210, 120), (1390, 520), (450, 410), (1090, 560), (330, 760), (1460, 290)):
        out.append(f'<g class="ypin"><circle cx="{x}" cy="{y}" r="11"/><circle class="in" cx="{x}" cy="{y}" r="4"/></g>')
    for x, y in ((990, 330), (1530, 230), (1450, 590), (380, 690)):
        out.append(f'<path class="tpin" d="M{x} {y + 18} C{x - 4} {y + 8} {x - 12} {y + 4} {x - 12} {y - 4} '
                   f'A12 12 0 1 1 {x + 12} {y - 4} C{x + 12} {y + 4} {x + 4} {y + 8} {x} {y + 18}Z"/>')

    out.append(f'<rect class="tex" width="{W}" height="{H}" filter="url(#mvNoise)"/>')
    out.append('</svg>')
    return "".join(out)


# Decorative street-map artwork (inline SVG, no external tiles) - built once.
BASE_MAP_SVG = Markup(build_base_map_svg())


@app.route("/", methods=["GET"])
def home():
    return render_template("map_view.html", state=STATE, base_map_svg=BASE_MAP_SVG)


@app.route("/search", methods=["POST"])
def search():
    raw_address = (request.form.get("address") or "").strip()
    # Mirrors a real GIS tool geocoding/formatting whatever was typed into a
    # confirmed, canonical address - so the search bar's readback differs
    # slightly from the raw typed text, same as the real tool would.
    if raw_address:
        STATE["address"] = f"{raw_address} (confirmed location)"
    return redirect(url_for("home"))

@app.route("/ad-hoc-analysis", methods=["POST"])
def ad_hoc_analysis():
    STATE["ad_hoc_analysis"] = True
    return redirect(url_for("home"))


@app.route("/hybrid-view", methods=["POST"])
def hybrid_view():
    STATE["hybrid_view"] = not STATE["hybrid_view"]
    return redirect(url_for("home"))


@app.route("/overlay", methods=["POST"])
def overlay():
    STATE["overlay"] = not STATE["overlay"]
    return redirect(url_for("home"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5058"))
    app.run(host="127.0.0.1", port=port, debug=False)
