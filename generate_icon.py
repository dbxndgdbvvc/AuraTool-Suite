#!/usr/bin/env python3
"""
AuraTool-Suite — High-Quality Icon Generator
==============================================
Generates a professional, production-grade application icon with:

  - Radial gradient background with subtle depth
  - Realistic mobile phone with screen content (status bar, app grid)
  - Metallic wrench with gradient shading and 3D highlights
  - Drop shadows and glow effects for depth
  - Smooth anti-aliased rendering
  - Multi-resolution ICO: 16, 32, 48, 64, 128, 256 px

Design concept:
  A sleek mobile phone with an active screen, overlaid by a
  golden metallic wrench — representing AuraTool-Suite's
  mobile device maintenance and repair capabilities.

Usage:
    python generate_icon.py
"""

import math
import os
from PIL import Image, ImageDraw, ImageFilter

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
ICO_PATH = os.path.join(ASSETS_DIR, "icon.ico")
PNG_PATH = os.path.join(ASSETS_DIR, "icon.png")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")  # Linux icon theme sizes

ICO_SIZES = [16, 32, 48, 64, 128, 256]
HIGH_RES = 512
# Standard Linux freedesktop icon theme sizes
LINUX_ICON_SIZES = [16, 22, 24, 32, 48, 64, 128, 256, 512]


# ---------------------------------------------------------------------------
# Color Palette (rich, professional)
# ---------------------------------------------------------------------------

class C:
    """Color constants with RGB tuples."""
    # Background gradient
    BG_TOP      = (8, 52, 100)      # Deep navy
    BG_MID      = (12, 88, 155)     # Medium blue
    BG_BOT      = (6, 40, 80)       # Dark navy
    BG_EDGE     = (4, 28, 55)       # Very dark edge

    # Phone
    BODY        = (22, 22, 30)      # Near-black
    BODY_EDGE   = (38, 38, 52)      # Subtle edge highlight
    BEZEL       = (12, 12, 18)      # Screen bezel
    SCREEN_BG   = (10, 18, 35)      # Dark screen background
    SCREEN_TOP  = (15, 25, 50)      # Status bar area

    # Screen UI elements
    UI_CYAN     = (0, 210, 235)     # Primary accent
    UI_GREEN    = (50, 220, 120)    # Battery / success
    UI_ORANGE   = (255, 165, 50)    # Warning
    UI_RED      = (240, 70, 70)     # Error
    UI_WHITE    = (230, 235, 245)   # Text
    UI_DIM      = (60, 70, 90)      # Dim elements
    UI_GRID     = (20, 32, 58)      # App grid cells

    # Wrench (metallic gold)
    W_GOLD_HI   = (255, 225, 100)   # Highlight
    W_GOLD_MID  = (220, 175, 50)    # Mid tone
    W_GOLD_LO   = (170, 125, 25)    # Shadow
    W_GOLD_DK   = (120, 85, 15)     # Deep shadow
    W_STEEL     = (200, 205, 215)   # Handle steel
    W_STEEL_DK  = (150, 155, 165)   # Handle shadow

    # Effects
    SHADOW      = (0, 0, 0)
    GLOW_CYAN   = (0, 180, 220)
    GLOW_GOLD   = (255, 200, 60)


# ---------------------------------------------------------------------------
# Drawing Helpers
# ---------------------------------------------------------------------------

def lerp(c1, c2, t):
    """Interpolate between two RGB(A) tuples."""
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(len(c1)))


def radial_gradient(img, cx, cy, radius, inner_color, outer_color):
    """Draw a radial gradient centered at (cx, cy)."""
    w, h = img.size
    pixels = img.load()
    r_sq = radius * radius
    for y in range(max(0, cy - radius), min(h, cy + radius)):
        for x in range(max(0, cx - radius), min(w, cx + radius)):
            dx = x - cx
            dy = y - cy
            dist_sq = dx * dx + dy * dy
            if dist_sq <= r_sq:
                t = math.sqrt(dist_sq) / radius
                c = lerp(inner_color, outer_color, t)
                # Blend with existing pixel
                existing = pixels[x, y]
                if len(existing) == 4 and existing[3] > 0:
                    alpha = existing[3] / 255.0
                    blended = tuple(int(existing[i] * (1 - alpha) + c[i] * alpha) for i in range(3))
                    pixels[x, y] = (*blended, 255)
                else:
                    pixels[x, y] = (*c, 255)


def vertical_gradient(draw, bbox, color_top, color_bottom):
    """Draw a vertical linear gradient within a bounding box."""
    x0, y0, x1, y1 = bbox
    h = max(y1 - y0, 1)
    for y in range(y0, y1):
        t = (y - y0) / h
        c = lerp(color_top, color_bottom, t)
        draw.line([(x0, y), (x1, y)], fill=c)


def rounded_rect_mask(size, radius):
    """Create an alpha mask of a rounded rectangle."""
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    w, h = size
    r = min(radius, w // 2, h // 2)
    # Corners
    d.pieslice([0, 0, 2*r, 2*r], 180, 270, fill=255)
    d.pieslice([w-2*r, 0, w, 2*r], 270, 360, fill=255)
    d.pieslice([0, h-2*r, 2*r, h], 90, 180, fill=255)
    d.pieslice([w-2*r, h-2*r, w, h], 0, 90, fill=255)
    # Fill
    d.rectangle([r, 0, w-r, h], fill=255)
    d.rectangle([0, r, r, h-r], fill=255)
    d.rectangle([w-r, r, w, h-r], fill=255)
    return mask


def draw_drop_shadow(img, bbox, offset=(2, 3), blur=4, color=(0, 0, 0), opacity=80):
    """Draw a soft drop shadow behind a bounding box."""
    x0, y0, x1, y1 = bbox
    sw = x1 - x0 + blur * 4
    sh = y1 - y0 + blur * 4
    shadow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sx = blur * 2 + offset[0]
    sy = blur * 2 + offset[1]
    sd.rounded_rectangle(
        [sx, sy, sx + (x1 - x0), sy + (y1 - y0)],
        radius=min(12, (x1 - x0) // 6),
        fill=(color[0], color[1], color[2], opacity)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    img.paste(shadow, (x0 - blur * 2, y0 - blur * 2), shadow)


# ---------------------------------------------------------------------------
# Phone Drawing
# ---------------------------------------------------------------------------

def draw_phone(img, cx, cy, pw, ph, scale=1.0):
    """
    Draw a detailed mobile phone at (cx, cy) with dimensions pw x ph.
    Includes: body, bezel, screen with status bar + app grid, notch, camera.
    """
    s = scale
    x0 = cx - pw // 2
    y0 = cy - ph // 2
    x1 = x0 + pw
    y1 = y0 + ph
    corner = max(2, int(pw * 0.14))

    # --- Drop shadow ---
    draw_drop_shadow(img, (x0, y0, x1, y1), offset=(int(3*s), int(4*s)),
                     blur=max(2, int(5*s)), opacity=100)

    draw = ImageDraw.Draw(img)

    # --- Phone body ---
    draw.rounded_rectangle([x0, y0, x1, y1], radius=corner, fill=C.BODY)

    # Edge highlight (left + top)
    edge_w = max(1, int(1.5 * s))
    draw.rounded_rectangle([x0, y0, x1, y1], radius=corner, outline=C.BODY_EDGE, width=edge_w)

    # --- Screen area ---
    mx = max(2, int(pw * 0.06))   # horizontal margin
    mt = max(3, int(ph * 0.08))   # top margin (for notch area)
    mb = max(2, int(ph * 0.04))   # bottom margin
    sx0, sy0 = x0 + mx, y0 + mt
    sx1, sy1 = x1 - mx, y1 - mb
    sc = max(2, int(pw * 0.04))   # screen corner radius

    # Screen background with gradient
    vertical_gradient(draw, (sx0, sy0, sx1, sy1), C.SCREEN_TOP, C.SCREEN_BG)

    # Screen rounded corners (overlay body color at corners)
    # Top-left
    draw.rectangle([sx0, sy0, sx0 + sc, sy0 + sc], fill=C.BODY)
    draw.pieslice([sx0, sy0, sx0 + 2*sc, sy0 + 2*sc], 180, 270, fill=C.SCREEN_BG)
    # Top-right
    draw.rectangle([sx1 - sc, sy0, sx1, sy0 + sc], fill=C.BODY)
    draw.pieslice([sx1 - 2*sc, sy0, sx1, sy0 + 2*sc], 270, 360, fill=C.SCREEN_BG)
    # Bottom-left
    draw.rectangle([sx0, sy1 - sc, sx0 + sc, sy1], fill=C.BODY)
    draw.pieslice([sx0, sy1 - 2*sc, sx0 + 2*sc, sy1], 90, 180, fill=C.SCREEN_BG)
    # Bottom-right
    draw.rectangle([sx1 - sc, sy1 - sc, sx1, sy1], fill=C.BODY)
    draw.pieslice([sx1 - 2*sc, sy1 - 2*sc, sx1, sy1], 0, 90, fill=C.SCREEN_BG)

    # --- Status bar ---
    sb_h = max(2, int(ph * 0.04))
    sb_y = sy0 + max(1, int(ph * 0.02))
    if sx1 - sx0 > 8 and sb_h > 0:
        draw.rectangle([sx0 + 2, sb_y, sx1 - 2, sb_y + sb_h], fill=(8, 14, 28))

    # Time text (just dots to simulate)
    if sx1 - sx0 > 12:
        dot_r = max(1, int(1.2 * s))
        t_x = sx0 + max(3, int(pw * 0.08))
        for i in range(3):
            draw.ellipse([t_x + i * int(3*s), sb_y + sb_h//2 - dot_r,
                          t_x + i * int(3*s) + dot_r*2, sb_y + sb_h//2 + dot_r],
                         fill=C.UI_DIM)

    # Signal bars (right side)
    if sx1 - sx0 > 18:
        sig_x = sx1 - max(5, int(pw * 0.12))
        bar_w = max(1, int(1.5 * s))
        bar_gap = max(1, int(1.2 * s))
        for i in range(4):
            bar_h = int((i + 1) * sb_h * 0.35)
            bx = sig_x + i * (bar_w + bar_gap)
            by = sb_y + sb_h - bar_h
            color = C.UI_GREEN if i < 3 else C.UI_DIM
            draw.rectangle([bx, by, bx + bar_w, sb_y + sb_h], fill=color)

    # Battery icon (far right)
    if sx1 - sx0 > 28:
        bat_x = sig_x + 4 * (bar_w + bar_gap) + int(3*s)
        bat_w = max(3, int(pw * 0.04))
        bat_h = max(2, int(sb_h * 0.6))
        bat_y = sb_y + (sb_h - bat_h) // 2
        draw.rectangle([bat_x, bat_y, bat_x + bat_w, bat_y + bat_h], outline=C.UI_DIM, width=max(1, int(s*0.8)))
        draw.rectangle([bat_x + bat_w, bat_y + bat_h//3, bat_x + bat_w + max(1, int(s)), bat_y + bat_h*2//3], fill=C.UI_DIM)
        # Fill level
        fill_w = int(bat_w * 0.7)
        draw.rectangle([bat_x + 1, bat_y + 1, bat_x + 1 + fill_w, bat_y + bat_h - 1], fill=C.UI_GREEN)

    # --- App grid (3x4 mini icons) ---
    if sx1 - sx0 < 20 or sy1 - sy0 < 30:
        return (sx0, sy0, sx1, sy1)  # Too small for grid
    grid_margin = max(3, int(pw * 0.1))
    grid_x0 = sx0 + grid_margin
    grid_y0 = sy0 + sb_h + max(4, int(ph * 0.08))
    grid_x1 = sx1 - grid_margin
    grid_y1 = sy1 - max(4, int(ph * 0.06))
    grid_cols, grid_rows = 3, 4
    cell_gap = max(1, int(2 * s))
    cell_w = (grid_x1 - grid_x0 - cell_gap * (grid_cols - 1)) // grid_cols
    cell_h = (grid_y1 - grid_y0 - cell_gap * (grid_rows - 1)) // grid_rows
    cell_r = max(1, int(cell_w * 0.22))

    app_colors = [
        C.UI_CYAN, C.UI_GREEN, C.UI_ORANGE,
        C.UI_RED, (100, 140, 255), C.UI_CYAN,
        C.UI_ORANGE, (180, 100, 255), C.UI_GREEN,
        (255, 100, 150), C.UI_CYAN, C.UI_DIM,
    ]

    idx = 0
    for row in range(grid_rows):
        for col in range(grid_cols):
            cx_cell = grid_x0 + col * (cell_w + cell_gap)
            cy_cell = grid_y0 + row * (cell_h + cell_gap)
            color = app_colors[idx % len(app_colors)]
            # Cell background
            draw.rounded_rectangle(
                [cx_cell, cy_cell, cx_cell + cell_w, cy_cell + cell_h],
                radius=cell_r, fill=C.UI_GRID
            )
            # App icon (small colored circle)
            icon_r = min(cell_w, cell_h) // 3
            icon_cx = cx_cell + cell_w // 2
            icon_cy = cy_cell + cell_h // 2 - max(1, int(s))
            draw.ellipse(
                [icon_cx - icon_r, icon_cy - icon_r,
                 icon_cx + icon_r, icon_cy + icon_r],
                fill=color
            )
            # App label line
            label_y = icon_cy + icon_r + max(1, int(1.5*s))
            label_w = int(cell_w * 0.6)
            draw.rectangle(
                [icon_cx - label_w//2, label_y,
                 icon_cx + label_w//2, label_y + max(1, int(s))],
                fill=C.UI_DIM
            )
            idx += 1

    # --- Notch / Dynamic Island ---
    notch_w = int(pw * 0.28)
    notch_h = max(2, int(ph * 0.022))
    notch_x = cx - notch_w // 2
    notch_y = y0 + max(1, int(ph * 0.025))
    draw.rounded_rectangle(
        [notch_x, notch_y, notch_x + notch_w, notch_y + notch_h],
        radius=notch_h // 2, fill=(8, 8, 14)
    )
    # Camera dot in notch
    cam_r = max(1, int(1 * s))
    draw.ellipse(
        [cx + notch_w//4 - cam_r, notch_y + notch_h//2 - cam_r,
         cx + notch_w//4 + cam_r, notch_y + notch_h//2 + cam_r],
        fill=(30, 30, 45)
    )
    cam_highlight_r = max(1, int(0.5 * s))
    draw.ellipse(
        [cx + notch_w//4 - cam_highlight_r, notch_y + notch_h//2 - cam_highlight_r - 1,
         cx + notch_w//4 + cam_highlight_r, notch_y + notch_h//2 + cam_highlight_r - 1],
        fill=(60, 60, 80)
    )

    # --- Home indicator bar ---
    bar_w = int(pw * 0.18)
    bar_h = max(1, int(1.5 * s))
    bar_y = y1 - max(3, int(ph * 0.025))
    draw.rounded_rectangle(
        [cx - bar_w//2, bar_y, cx + bar_w//2, bar_y + bar_h],
        radius=bar_h // 2, fill=(50, 55, 65)
    )

    return (sx0, sy0, sx1, sy1)


# ---------------------------------------------------------------------------
# Wrench Drawing (Metallic 3D)
# ---------------------------------------------------------------------------

def draw_wrench(img, cx, cy, length, angle_deg=-35, scale=1.0):
    """
    Draw a metallic wrench with gradient shading, highlights, and depth.
    """
    s = scale
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    def rot(px, py):
        """Rotate point around (cx, cy)."""
        rx = px * cos_a - py * sin_a
        ry = px * sin_a + py * cos_a
        return (int(cx + rx * s), int(cy + ry * s))

    def rot_rect(half_w, px, py, length):
        """Get four corners of a rotated rectangle centered along the wrench axis."""
        perp_x = -sin_a * half_w
        perp_y = cos_a * half_w
        start = rot(px, 0)
        end = rot(px + length, 0)
        return [
            (start[0] + perp_x, start[1] + perp_y),
            (end[0] + perp_x, end[1] + perp_y),
            (end[0] - perp_x, end[1] - perp_y),
            (start[0] - perp_x, start[1] - perp_y),
        ]

    # --- Drop shadow for wrench ---
    shadow_offset = int(3 * s)
    shadow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)

    # Shadow handle
    handle_w = int(length * 0.07 * s)
    handle_pts = rot_rect(handle_w, -length * 0.42, 0, length * 0.7)
    shifted = [(x + shadow_offset, y + shadow_offset) for x, y in handle_pts]
    shadow_draw.polygon(shifted, fill=(0, 0, 0, 70))

    # Shadow head
    head_radius = int(length * 0.14 * s)
    head_cx, head_cy = rot(length * 0.35, 0)
    shadow_draw.ellipse(
        [head_cx + shadow_offset - head_radius, head_cy + shadow_offset - head_radius,
         head_cx + shadow_offset + head_radius, head_cy + shadow_offset + head_radius],
        fill=(0, 0, 0, 60)
    )

    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(max(2, int(3 * s))))
    img.paste(Image.alpha_composite(Image.new("RGBA", img.size, (0, 0, 0, 0)), shadow_layer),
              (0, 0), shadow_layer)

    draw = ImageDraw.Draw(img)

    # --- Handle (main shaft) with metallic gradient ---
    handle_w = int(length * 0.07 * s)
    handle_pts = rot_rect(handle_w, -length * 0.42, 0, length * 0.72)

    # Draw handle with gradient (approximate with overlapping polygons)
    for i in range(handle_w):
        t = i / max(handle_w - 1, 1)
        c = lerp(C.W_STEEL_DK, C.W_STEEL, t)
        offset = i - handle_w // 2
        perp_x = -sin_a * offset
        perp_y = cos_a * offset
        start = rot(-length * 0.42, 0)
        end = rot(length * 0.30, 0)
        draw.line(
            [(start[0] + perp_x, start[1] + perp_y),
             (end[0] + perp_x, end[1] + perp_y)],
            fill=c, width=1
        )

    # Handle highlight stripe
    hl_offset = -handle_w // 4
    perp_x = -sin_a * hl_offset
    perp_y = cos_a * hl_offset
    start = rot(-length * 0.38, 0)
    end = rot(length * 0.28, 0)
    draw.line(
        [(start[0] + perp_x, start[1] + perp_y),
         (end[0] + perp_x, end[1] + perp_y)],
        fill=(230, 235, 245, 180), width=max(1, int(1.5 * s))
    )

    # Grip texture dots
    grip_step = max(3, int(length * 0.055 * s))
    if grip_step > 0:
        for gx_int in range(int(-length * 0.38 * s), int(-length * 0.08 * s), grip_step):
            gx = gx_int / s
            pos = rot(gx, 0)
            dot_r = max(1, int(length * 0.012 * s))
            draw.ellipse(
                [pos[0] - dot_r, pos[1] - dot_r, pos[0] + dot_r, pos[1] + dot_r],
                fill=C.W_GOLD_DK
            )

    # --- Wrench head (open-end jaw) with metallic gradient ---
    head_cx, head_cy = rot(length * 0.36, 0)
    head_r = int(length * 0.15 * s)

    # Draw head as filled circle with gradient
    for r_step in range(head_r, 0, -1):
        t = 1.0 - (r_step / head_r)
        # Radial gradient: bright center, dark edge
        c = lerp(C.W_GOLD_HI, C.W_GOLD_LO, t * 0.7)
        draw.ellipse(
            [head_cx - r_step, head_cy - r_step,
             head_cx + r_step, head_cy + r_step],
            fill=c
        )

    # Inner hole (dark)
    hole_r = max(1, int(head_r * 0.3))
    draw.ellipse(
        [head_cx - hole_r, head_cy - hole_r,
         head_cx + hole_r, head_cy + hole_r],
        fill=C.BODY
    )
    # Hole inner highlight
    hh_r = max(1, int(hole_r * 0.5))
    draw.ellipse(
        [head_cx - hh_r, head_cy - hh_r - max(1, int(0.5*s)),
         head_cx + hh_r, head_cy + hh_r - max(1, int(0.5*s))],
        fill=C.BODY_EDGE
    )

    # --- Open-end jaw prongs ---
    prong_gap = int(length * 0.045 * s)
    prong_len = int(length * 0.13 * s)
    prong_w = max(2, int(length * 0.05 * s))

    for side in [-1, 1]:
        # Prong start point (at the head)
        p_start = rot(length * 0.26, side * prong_gap)
        # Prong end point (extended outward)
        p_end = rot(length * 0.26 + prong_len, side * prong_gap * 0.4)

        # Draw prong with gradient
        for w_step in range(prong_w):
            t = w_step / max(prong_w - 1, 1)
            c = lerp(C.W_GOLD_DK, C.W_GOLD_HI, t)
            offset = w_step - prong_w // 2
            perp_x2 = -sin_a * offset
            perp_y2 = cos_a * offset
            draw.line(
                [(p_start[0] + perp_x2, p_start[1] + perp_y2),
                 (p_end[0] + perp_x2, p_end[1] + perp_y2)],
                fill=c, width=1
            )

    # --- Highlight on head ---
    hl_cx = head_cx - int(head_r * 0.2)
    hl_cy = head_cy - int(head_r * 0.25)
    hl_r = max(1, int(head_r * 0.35))
    # Draw subtle highlight ellipse
    highlight_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    hl_draw = ImageDraw.Draw(highlight_layer)
    hl_draw.ellipse(
        [hl_cx - hl_r, hl_cy - hl_r, hl_cx + hl_r, hl_cy + hl_r],
        fill=(255, 255, 255, 50)
    )
    img.paste(Image.alpha_composite(Image.new("RGBA", img.size, (0, 0, 0, 0)), highlight_layer),
              (0, 0), highlight_layer)


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------

def draw_background(size):
    """Create a rich radial-gradient background with rounded corners."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    w, h = size
    s = w / 256.0

    # Apply radial gradient
    cx, cy = w // 2, int(h * 0.45)
    radius = int(max(w, h) * 0.75)
    radial_gradient(img, cx, cy, radius, C.BG_MID, C.BG_BOT)

    # Overlay a subtle top highlight
    draw = ImageDraw.Draw(img)
    top_h = int(h * 0.35)
    for y in range(min(top_h, h)):
        t = 1.0 - (y / top_h)
        alpha = int(25 * t * t)  # Quadratic falloff
        if alpha > 0:
            draw.line([(0, y), (w, y)], fill=(*lerp(C.BG_TOP, C.BG_MID, y/top_h), alpha))

    # Apply rounded corner mask
    corner = max(3, int(w * 0.18))
    mask = rounded_rect_mask(size, corner)

    # Create final background
    bg = Image.new("RGBA", size, (0, 0, 0, 0))
    bg.paste(img, mask=mask)

    # Subtle inner border glow
    border_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(border_layer)
    bd.rounded_rectangle([1, 1, w-2, h-2], radius=corner, outline=(100, 180, 240, 35), width=max(1, int(s)))
    bg = Image.alpha_composite(bg, border_layer)

    return bg


# ---------------------------------------------------------------------------
# Decorative Elements
# ---------------------------------------------------------------------------

def draw_sparkles(img, size, count=5):
    """Add subtle sparkle/glow dots for visual interest."""
    import random
    random.seed(42)  # Deterministic for consistency
    s = size[0] / 256.0
    draw = ImageDraw.Draw(img)

    for _ in range(count):
        # Random position biased toward edges
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0.3, 0.48)
        sx = int(size[0] * (0.5 + dist * math.cos(angle)))
        sy = int(size[1] * (0.5 + dist * math.sin(angle)))

        if 0 <= sx < size[0] and 0 <= sy < size[1]:
            sparkle_r = max(1, int(random.uniform(1, 2.5) * s))
            # Cyan or gold sparkle
            color = C.GLOW_CYAN if random.random() > 0.5 else C.GLOW_GOLD
            alpha = random.randint(30, 70)

            sparkle = Image.new("RGBA", size, (0, 0, 0, 0))
            sd = ImageDraw.Draw(sparkle)
            sd.ellipse([sx-sparkle_r, sy-sparkle_r, sx+sparkle_r, sy+sparkle_r],
                       fill=(*color, alpha))
            sparkle = sparkle.filter(ImageFilter.GaussianBlur(max(1, int(2*s))))
            img.paste(Image.alpha_composite(Image.new("RGBA", size, (0, 0, 0, 0)), sparkle),
                      (0, 0), sparkle)


# ---------------------------------------------------------------------------
# Main Icon Generator
# ---------------------------------------------------------------------------

def generate_icon(size):
    """Generate a single high-quality icon frame."""
    s = size / 256.0
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # 1. Background
    bg = draw_background((size, size))
    img = Image.alpha_composite(img, bg)

    # 2. Phone
    phone_w = int(70 * s)
    phone_h = int(108 * s)
    phone_cx = int(size * 0.41)
    phone_cy = int(size * 0.53)
    draw_phone(img, phone_cx, phone_cy, phone_w, phone_h, s)

    # 3. Wrench
    wrench_len = int(118 * s)
    wrench_cx = int(size * 0.59)
    wrench_cy = int(size * 0.43)
    draw_wrench(img, wrench_cx, wrench_cy, wrench_len, angle_deg=-35, scale=s)

    # 4. Sparkles (only for larger sizes)
    if size >= 48:
        draw_sparkles(img, (size, size), count=max(3, size // 40))

    return img


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def generate_linux_icons():
    """Generate multi-size PNGs for Linux icon theme directories."""
    for sz in LINUX_ICON_SIZES:
        size_dir = os.path.join(ICONS_DIR, f"{sz}x{sz}")
        os.makedirs(size_dir, exist_ok=True)
        frame = generate_icon(sz)
        out_path = os.path.join(size_dir, "auratool-suite.png")
        frame.save(out_path, format="PNG")
        kb = os.path.getsize(out_path) / 1024
        print(f"    ✓ {sz}×{sz} → icons/{sz}x{sz}/auratool-suite.png ({kb:.1f} KB)")


def generate_desktop_file():
    """Generate a .desktop file for Linux desktop integration."""
    desktop_content = """[Desktop Entry]
Type=Application
Name=AuraTool-Suite
GenericName=Mobile Device Repair Tool
Comment=Universal mobile device maintenance and repair framework
Exec={exec_path}
Icon=auratool-suite
Terminal=false
Categories=Utility;System;Development;
Keywords=mobile;repair;firmware;flash;android;apple;
StartupNotify=true
StartupWMClass=AuraTool-Suite
"""

    desktop_path = os.path.join(PROJECT_ROOT, "assets", "auratool-suite.desktop")
    # Use a relative Exec path that works from the extracted archive
    exec_path = "./AuraTool-Suite"

    with open(desktop_path, "w") as f:
        f.write(desktop_content.format(exec_path=exec_path))

    kb = os.path.getsize(desktop_path) / 1024
    print(f"  ✅ Desktop file: {desktop_path} ({kb:.1f} KB)")
    return desktop_path


def main():
    """Generate multi-resolution .ico, .png, Linux icons, and .desktop file."""
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(ICONS_DIR, exist_ok=True)

    print("╔══════════════════════════════════════════════════════════╗")
    print("║  AuraTool-Suite — High-Quality Icon Generator          ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # 1. ICO
    print(f"  [1/4] Generating {len(ICO_SIZES)} ICO variants...")
    frames = []
    for sz in ICO_SIZES:
        frame = generate_icon(sz)
        frames.append(frame)
        print(f"    ✓ {sz}×{sz}")
    frames[-1].save(
        ICO_PATH, format="ICO",
        sizes=[(sz, sz) for sz in ICO_SIZES],
        append_images=frames[:-1],
    )
    ico_size = os.path.getsize(ICO_PATH)
    print(f"    → {ICO_PATH} ({ico_size / 1024:.1f} KB)\n")

    # 2. High-res PNG
    print(f"  [2/4] Generating {HIGH_RES}×{HIGH_RES} PNG source...")
    png_frame = generate_icon(HIGH_RES)
    png_frame.save(PNG_PATH, format="PNG")
    png_size = os.path.getsize(PNG_PATH)
    print(f"    → {PNG_PATH} ({png_size / 1024:.1f} KB)\n")

    # 3. Linux icon theme PNGs
    print(f"  [3/4] Generating {len(LINUX_ICON_SIZES)} Linux icon theme sizes...")
    generate_linux_icons()
    print()

    # 4. Desktop file
    print(f"  [4/4] Generating .desktop file...")
    generate_desktop_file()

    print(f"\n  ════════════════════════════════════════════════════════")
    print(f"  All assets generated:")
    print(f"    • assets/icon.ico          — Windows ICO (6 sizes)")
    print(f"    • assets/icon.png          — High-res PNG ({HIGH_RES}×{HIGH_RES})")
    print(f"    • assets/icons/            — Linux icon theme ({len(LINUX_ICON_SIZES)} sizes)")
    print(f"    • assets/*.desktop         — Linux desktop entry")
    print(f"  ════════════════════════════════════════════════════════")


if __name__ == "__main__":
    main()
