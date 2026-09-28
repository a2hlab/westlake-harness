#!/usr/bin/env python3
"""Generate ApkInstaller app icon (task #55).

Design: full-bleed rounded-square, diagonal blue->teal gradient, white
"package + install arrow" glyph: an open tray/box with a bold down arrow
landing into it. Rendered at 1024, then downsampled for entry media slots.
"""
from PIL import Image, ImageDraw, ImageFilter
import math, os

SIZE = 1024
FG = (255, 255, 255, 255)

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

C1 = (10, 89, 247)    # #0A59F7
C2 = (25, 194, 184)   # #19C2B8

def base_gradient(size):
    img = Image.new('RGB', (size, size))
    px = img.load()
    for y in range(size):
        for x in range(0, size, 4):
            t = (x + y) / (2 * size)
            c = lerp(C1, C2, t)
            for dx in range(4):
                if x + dx < size:
                    px[x + dx, y] = c
    return img

def rounded_mask(size, radius):
    m = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m

def draw_glyph(img, size):
    d = ImageDraw.Draw(img)
    u = size / 1024.0  # unit

    # Tray (open box): U shape
    tray_w = 560 * u
    tray_h = 210 * u
    tray_x0 = (size - tray_w) / 2
    tray_y1 = size * 0.78
    tray_y0 = tray_y1 - tray_h
    wall = 56 * u
    rad = 42 * u
    # left wall
    d.rounded_rectangle([tray_x0, tray_y0, tray_x0 + wall, tray_y1], radius=wall / 2, fill=FG)
    # right wall
    d.rounded_rectangle([tray_x0 + tray_w - wall, tray_y0, tray_x0 + tray_w, tray_y1], radius=wall / 2, fill=FG)
    # bottom
    d.rounded_rectangle([tray_x0, tray_y1 - wall, tray_x0 + tray_w, tray_y1], radius=wall / 2, fill=FG)

    # Down arrow: shaft + head, centered above tray
    cx = size / 2
    shaft_w = 84 * u
    shaft_y0 = size * 0.20
    shaft_y1 = size * 0.52
    d.rounded_rectangle([cx - shaft_w / 2, shaft_y0, cx + shaft_w / 2, shaft_y1],
                        radius=shaft_w / 2, fill=FG)
    # arrow head: triangle
    head_half = 150 * u
    head_y0 = shaft_y1 - 40 * u
    head_y1 = size * 0.68
    d.polygon([(cx - head_half, head_y0), (cx + head_half, head_y0), (cx, head_y1)], fill=FG)
    # soften the head joint with a circle at the base
    d.ellipse([cx - shaft_w / 2, head_y0 - shaft_w / 2, cx + shaft_w / 2, head_y0 + shaft_w / 2], fill=FG)

def make(size, radius_ratio=0.225):
    img = base_gradient(size)
    # subtle top highlight
    hl = Image.new('L', (size, size), 0)
    hd = ImageDraw.Draw(hl)
    hd.ellipse([-size * 0.4, -size * 0.7, size * 1.1, size * 0.5], fill=46)
    white = Image.new('RGB', (size, size), (255, 255, 255))
    img = Image.composite(white, img, hl)
    draw_glyph(img, size)
    mask = rounded_mask(size, int(size * radius_ratio))
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out

ROOT = os.path.expanduser('~/a2hlab/00.Workspace/src/apps/apkinstaller')
icon = make(1024)
icon.save(os.path.join(ROOT, 'AppScope/resources/base/media/app_icon.png'))
# entry media: icon.png + startIcon.png (foreground uses same glyph)
icon.resize((512, 512), Image.LANCZOS).save(os.path.join(ROOT, 'entry/src/main/resources/base/media/icon.png'))
icon.resize((512, 512), Image.LANCZOS).save(os.path.join(ROOT, 'entry/src/main/resources/base/media/startIcon.png'))
print('icons written')
