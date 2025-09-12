# coding: utf-8
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Survivalists Card Templates — Release Build (Art-Fit Enabled)

Features:
- 750×1050 px @ 300 dpi canvas
- Outer vignette gradient + inner faceted frame
- Raised parchment plaques: Header, Type, Rules, Stats, Footer
- Beveled transparent art box
- Serif Bold headers/rules/stats, Serif Italic flavor
- Footer: Set/Edition (left), Card ID stacked over ordinal X/Total (right)
- Faction badge: fixed-width (35% of type plaque), right-justified, sharp corners, STAG = brimstone red
- Resource cost orb + number: vertically centered in header plaque; number tight to left of orb
- Artwork auto-fit: center-crop to 640×360 and placed into the art box

Inputs:
- CSV (source of truth): srp_bitterroot_collection.csv
  Expected columns (case-insensitive): Name, Faction, Type, Subtype,
  Abilities, Flavor Text, Stats, Set/Edition, Card ID, Resource Cost, Artwork (optional path)

Optional assets:
- Orb images: orb_energy.png, orb_munitions.png, orb_faith.png, orb_supplies.png
- Artwork files in ./art/ named by Card ID or slugified Name, or a file path in CSV "Artwork" column

Outputs:
- PNGs in ./cards_full_release/ (one per row)
- Optional: you can zip them after rendering

Requires: Pillow, pandas
"""

import os, re, glob
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PX_W, PX_H = 750, 1050
DPI = 300
ART_W, ART_H = 645, 339  # art box content

# ---------- helpers ----------
def sanitize(val):
    s = str(val) if val is not None else ""
    return "" if s.lower() in ("nan","none") else s

def field(row, *aliases):
    """Return the first non-empty value found for any alias (case-insensitive)."""
    # direct hit first
    for a in aliases:
        if a in row and str(row[a]).strip():
            return str(row[a])
    # case-insensitive map
    lower_map = {str(k).lower(): k for k in row.index}
    for a in aliases:
        k = lower_map.get(str(a).lower())
        if k is not None and str(row[k]).strip():
            return str(row[k])
    return ""

def load_font(name="fonts/DejaVuSerif-Bold.ttf", size=24, fallback="fonts/DejaVuSerif.ttf"):
    try:
        return ImageFont.truetype(name, size)
    except:
        return ImageFont.truetype(fallback, size)

def vertical_gradient(size, top_rgb, bottom_rgb):
    w, h = size
    base = Image.new("RGB", size, color=top_rgb)
    col = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h-1)
        r = int(top_rgb[0] + (bottom_rgb[0]-top_rgb[0]) * t)
        g = int(top_rgb[1] + (bottom_rgb[1]-top_rgb[1]) * t)
        b = int(top_rgb[2] + (bottom_rgb[2]-top_rgb[2]) * t)
        col.putpixel((0, y), (r, g, b))
    base.paste(col.resize((w, h)))
    return base

def noise_texture(size, alpha=35):
    noise = Image.effect_noise(size, 30).convert("L")
    return Image.merge("RGBA", (noise, noise, noise, Image.new("L", size, alpha)))

def rounded_rect_mask(size, radius):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0,0,size[0],size[1]), radius=radius, fill=255)
    return m

# ---------- plaques & art box ----------
def plaque_parchment(size):
    img = vertical_gradient(size, (242,233,208), (224,212,184)).convert("RGBA")
    img.alpha_composite(noise_texture(size, alpha=22))
    return img

def draw_plaque_raised(base, rect, radius=12, elevation=10):
    x0,y0,x1,y1 = rect
    w,h = x1-x0, y1-y0

    # Shadow
    shadow = Image.new("RGBA", (PX_W, PX_H), (0,0,0,0))
    m = rounded_rect_mask((w,h), radius)
    shcut = Image.new("RGBA", (w,h), (0,0,0,160))
    shadow.paste(shcut, (x0 + elevation//2, y0 + elevation), m)
    shadow = shadow.filter(ImageFilter.GaussianBlur(elevation//2 + 4))

    # Body
    body = Image.new("RGBA", (PX_W, PX_H), (0,0,0,0))
    fill = plaque_parchment((w,h))
    body.paste(fill, (x0,y0), m)

    # Bevels
    d = ImageDraw.Draw(body, "RGBA")
    d.rounded_rectangle(rect, radius=radius, outline=(0,0,0,220), width=2)
    inset = 3
    d.rounded_rectangle((x0+inset,y0+inset,x1-inset,y1-inset),
                        radius=max(1,radius-inset), outline=(255,255,255,140), width=2)
    inset2 = 5
    d.rounded_rectangle((x0+inset2,y0+inset2,x1-inset2,y1-inset2),
                        radius=max(1,radius-inset2), outline=(0,0,0,90), width=2)

    base.alpha_composite(shadow)
    base.alpha_composite(body)

def draw_art_bevel(base, rect):
    x0,y0,x1,y1 = rect
    layer = Image.new("RGBA", (PX_W, PX_H), (0,0,0,0))
    d = ImageDraw.Draw(layer, "RGBA")
    d.rectangle(rect, outline=(0,0,0,230), width=6)
    pad = 6
    d.rectangle((x0+pad,y0+pad,x1-pad,y1-pad), outline=(255,255,255,100), width=2)
    pad2 = 10
    d.rectangle((x0+pad2,y0+pad2,x1-pad2,y1-pad2), outline=(0,0,0,90), width=2)
    base.alpha_composite(layer)

# ---------- centered rules & flavor ----------
def draw_center_wrapped_text(draw, text, box, font, fill, stroke_width=0, stroke_fill=None, line_spacing=4):
    x0,y0,x1,y1 = box
    max_w = x1 - x0 - 40
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur+" "+w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    y = y0
    for line in lines:
        tw = draw.textlength(line, font=font)
        x = x0 + (x1 - x0 - tw)//2
        if stroke_width and stroke_fill:
            draw.text((x,y), line, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        else:
            draw.text((x,y), line, font=font, fill=fill)
    bbox = draw.textbbox((0,0), "Hg", font=font)
    y += (bbox[3] - bbox[1]) + line_spacing
    return y

def draw_rules_flavor_centered(base, rules_rect, ability, flavor):
    d = ImageDraw.Draw(base, "RGBA")

    # Starting font sizes and minimums
    ability_size = 25
    flavor_size = 24
    min_ability = 18
    min_flavor = 18

    # Spacing
    ability_line_gap = 4
    para_gap = 8
    divider_gap = 12

    # Helper to load fonts
    def get_fonts(a_size, f_size):
        fa = load_font(size=a_size)
        try:
            ff = ImageFont.truetype("DejaVuSerif-Italic.ttf", f_size)
        except:
            ff = load_font(name="DejaVuSerif.ttf", size=f_size)
        return fa, ff

    # Wrap helpers
    def wrap_left(txt, font, max_w):
        words, lines, cur = txt.split(), [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if d.textlength(test, font=font) <= max_w:
                cur = test
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        return lines

    def measure(a_sz, f_sz):
        fa, ff = get_fonts(a_sz, f_sz)
        pad_top = 18
        pad_bottom = 20
        max_w = rules_rect[2]-rules_rect[0]-40
        y = pad_top

        ability_text = ability if isinstance(ability, str) else ""
        for para in ability_text.split("\n"):
            para = para.strip()
            if not para: continue
            for _ in wrap_left(para, fa, max_w):
                bbox = d.textbbox((0,0), "Hg", font=fa)
                y += (bbox[3] - bbox[1]) + ability_line_gap
            y += para_gap
        y += divider_gap

        flavor_text = flavor if isinstance(flavor, str) else ""
        if flavor_text.strip():
            for _ in wrap_left(flavor_text, ff, max_w):
                bbox = d.textbbox((0,0), "Hg", font=ff)
                y += (bbox[3] - bbox[1]) + 4
        y += pad_bottom
        return y

    available = rules_rect[3]-rules_rect[1]
    while True:
        total_h = measure(ability_size, flavor_size)
        if total_h <= available or (ability_size <= min_ability and flavor_size <= min_flavor):
            break
        if ability_size > min_ability:
            ability_size -= 1
        elif flavor_size > min_flavor:
            flavor_size -= 1
        else:
            break

    fa, ff = get_fonts(ability_size, flavor_size)
    pad_top = 18
    y = rules_rect[1] + pad_top
    max_w = rules_rect[2]-rules_rect[0]-40

    # Abilities (left-aligned, respect explicit newlines)
    ability_text = ability if isinstance(ability, str) else ""
    for para in ability_text.split("\n"):
        para = para.strip()
        if not para:
            continue
        for line in wrap_left(para, fa, max_w):
            d.text((rules_rect[0]+20, y), line, font=fa, fill=(0,0,0),
                   stroke_width=2, stroke_fill=(220,220,220))
            bbox = d.textbbox((0,0), "Hg", font=fa)
            y += (bbox[3] - bbox[1]) + ability_line_gap
        y += para_gap

    # Divider
    y += divider_gap
    d.line((rules_rect[0]+30, y, rules_rect[2]-30, y), fill=(0,0,0,200), width=2)
    y += divider_gap

    # Flavor (centered, italic)
    flavor_text = flavor if isinstance(flavor, str) else ""
    if flavor_text.strip():
        for line in wrap_left(flavor_text, ff, max_w):
            tw = d.textlength(line, font=ff)
            tx = rules_rect[0] + 20 + (max_w - tw)//2
            d.text((tx, y), line, font=ff, fill=(60,60,60))
            bbox = d.textbbox((0,0), "Hg", font=ff)
            y += (bbox[3] - bbox[1]) + 4

# ---------- cost orb & number ----------
def parse_cost_number(resource_cost):
    s = sanitize(resource_cost)
    m = re.search(r"(\d+)", s)
    return m.group(1) if m else ""

def place_orb_number_left_centered(base, name_rect, orb_img, cost_num):
    # Always render the numeric cost; render the orb if available.
    plaque_h = name_rect[3]-name_rect[1]
    target = int(plaque_h * 0.80)
    x = name_rect[2] - target - 10
    y = name_rect[1] + (plaque_h - target)//2

    layer = Image.new("RGBA", (PX_W, PX_H), (0,0,0,0))

    if orb_img is not None:
        orb = orb_img.copy().convert("RGBA").resize((target,target), Image.Resampling.LANCZOS)
        layer.paste(orb, (x,y), orb)

    cost = str(cost_num).strip()
    if cost:
        d = ImageDraw.Draw(layer, "RGBA")
        font = load_font(size=int(target*0.55))
        tw = d.textlength(cost, font=font)
        bbox = d.textbbox((0,0), "Hg", font=font)
        th = bbox[3] - bbox[1]
        tx = x - tw - 10
        ty = y + (target - th)//2
        if orb_img is None:
            tx = name_rect[2] - 20 - tw
            ty = (name_rect[1] + name_rect[3] - th)//2
        d.text((tx,ty), cost, font=font, fill=(0,0,0,255),
               stroke_width=max(2, target//18), stroke_fill=(255,255,255,220))

    base.alpha_composite(layer)

# ---------- faction badge (fixed-width, right) ----------
def draw_faction_badge(base, type_rect, faction_key, label_text, width_factor=0.35, overshoot_px=3):
    x0,y0,x1,y1 = type_rect
    h = y1 - y0
    w_total = x1 - x0
    badge_w = int(w_total * width_factor)
    rx1 = x1 + overshoot_px
    rx0 = rx1 - badge_w
    w = rx1 - rx0

    if faction_key == "espenlock":
        c1,c2 = (70,120,200),(35,70,140); txt=(255,255,255); stroke=(0,0,0)
    elif faction_key == "stag":  # brimstone red
        c1,c2 = (200,60,40),(90,20,20);   txt=(0,0,0);       stroke=(255,255,255)
    elif faction_key == "cow":
        c1,c2 = (150,60,200),(80,30,120); txt=(255,255,255); stroke=(0,0,0)
    elif faction_key == "survivor":
        c1,c2 = (220,120,40),(160,70,10); txt=(0,0,0);       stroke=(255,255,255)
    else:  # special
        c1,c2 = (240,235,225),(200,195,185); txt=(0,0,0);    stroke=(255,255,255)

    grad = Image.new("RGBA", (w, h), (0,0,0,0))
    for yy in range(h):
        for xx in range(w):
            t = (xx + yy) / float(w + h)
            r = int(c1[0] + (c2[0]-c1[0]) * t)
            g = int(c1[1] + (c2[1]-c1[1]) * t)
            b = int(c1[2] + (c2[2]-c1[2]) * t)
            grad.putpixel((xx,yy), (r,g,b,255))

    radius = max(4, int(h/6))
    mask = rounded_rect_mask((w,h), radius=radius)
    base.paste(grad, (rx0,y0), mask)

    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((rx0,y0,rx1,y1), radius=radius, outline=(0,0,0,230), width=3)
    d.rounded_rectangle((rx0+2,y0+2,rx1-2,y1-2), radius=max(1, radius-2),
                        outline=(255,255,255,90), width=2)

    font = load_font(size=26)
    tw = d.textlength(label_text, font=font)
    bbox = d.textbbox((0,0), "Hg", font=font)
    th = bbox[3] - bbox[1]
    d.text((rx0 + (w - tw)//2, y0 + (h - th)//2), label_text, font=font, fill=txt,
           stroke_width=2, stroke_fill=stroke)

# ---------- regions & footer ----------
def compute_regions():
    ART_INSET = 32
    name_rect = (ART_INSET, 50, PX_W-ART_INSET, 127)

    # Art box
    art_rect  = (ART_INSET+10, name_rect[3]+10, PX_W-ART_INSET-10, name_rect[3]+370)

    # Type line plaque
    type_rect = (ART_INSET, art_rect[3]+12, PX_W-ART_INSET, art_rect[3]+62)

    # Stats plaque (fixed location near bottom)
    stats_rect= (PX_W//2-180, PX_H-145, PX_W//2+180, PX_H-95)

    # Footer
    foot_rect = (ART_INSET, PX_H-80, PX_W-ART_INSET, PX_H-10)

    # Rules plaque expands between type and stats with equal 10px padding
    rules_rect= (ART_INSET, type_rect[3]+10, PX_W-ART_INSET, stats_rect[1]-10)

    return name_rect, art_rect, type_rect, rules_rect, stats_rect, foot_rect


def draw_footer(base, foot_rect, row, index, total_cards):
    d = ImageDraw.Draw(base, "RGBA")
    draw_plaque_raised(base, foot_rect, radius=10, elevation=10)
    font = load_font(size=22)

    # Left: Set/Edition (robust aliases)
    left = sanitize(field(row, "Set/Edition", "Set", "Edition", "Collection", "Collection/Edition", "Set Name"))
    bbox = d.textbbox((0,0), left, font=font)
    lh = bbox[3] - bbox[1]
    d.text((foot_rect[0]+20, (foot_rect[1]+foot_rect[3]-lh)//2),
           left, font=font, fill=(0,0,0), stroke_width=2, stroke_fill=(220,220,220))

    # Right: Card ID + Ordinal (robust aliases + fallbacks)
    card_id = sanitize(field(row, "Card ID", "CardID", "ID", "Card_Id", "Card Number"))
    ordinal = f"{int(index) + 1}/{int(total_cards) if total_cards is not None else 1}"

    bbox_id = d.textbbox((0,0), card_id, font=font)
    tw_id = bbox_id[2] - bbox_id[0]
    th_id = bbox_id[3] - bbox_id[1]
    bbox_ord = d.textbbox((0,0), ordinal, font=font)
    tw_ord = bbox_ord[2] - bbox_ord[0]
    th_ord = bbox_ord[3] - bbox_ord[1]
    id_ordinal_gap = 6
    total_h = th_id + th_ord + id_ordinal_gap
    top_y = (foot_rect[1]+foot_rect[3]-total_h)//2
    x_right = foot_rect[2]-20
    # Draw ordinal on top, card_id below, both right-aligned
    d.text((x_right - tw_ord, top_y), ordinal, font=font, fill=(0,0,0),
        stroke_width=2, stroke_fill=(220,220,220))
    d.text((x_right - tw_id, top_y + th_ord + id_ordinal_gap), card_id, font=font, fill=(0,0,0),
        stroke_width=2, stroke_fill=(220,220,220))

def cover_fit(image, target_w, target_h):
    iw, ih = image.size
    target_ratio = target_w / target_h
    src_ratio = iw / ih
    if src_ratio > target_ratio:
        new_w = int(ih * target_ratio)
        x0 = max(0, (iw - new_w)//2)
        image = image.crop((x0, 0, x0+new_w, ih))
    else:
        new_h = int(iw / target_ratio)
        y0 = max(0, (ih - new_h)//2)
        image = image.crop((0, y0, iw, y0+new_h))
    return image.resize((target_w, target_h), Image.Resampling.LANCZOS)

def locate_art(row):
    art_hint = sanitize(row.get("Artwork",""))
    card_id = str(row.get("Card ID", "")).lower().replace("-", "_")
    # Use the exact path as in the CSV
    artwork_path = f"source/art/bitterrootcollection/{card_id}.png"
    # print(f"[DEBUG] Checking for artwork: {artwork_path}")
    if os.path.isfile(artwork_path):
        try:
            return Image.open(artwork_path).convert("RGBA")
        except Exception as e:
            print(f"[DEBUG] Failed to open artwork: {artwork_path} ({e})")
    # Fallbacks: try art_hint, old locations, etc.
    candidates = []
    if art_hint:
        candidates.append(art_hint)
    name = sanitize(row.get("Name",""))
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if card_id:
        candidates += glob.glob(os.path.join("art", f"{card_id}.*"))
    if slug:
        candidates += glob.glob(os.path.join("art", f"{slug}.*"))
    for p in candidates:
        # print(f"[DEBUG] Checking fallback artwork: {p}")
        if os.path.isfile(p):
            try:
                return Image.open(p).convert("RGBA")
            except Exception as e:
                print(f"[DEBUG] Failed to open fallback artwork: {p} ({e})")
                continue
    # print(f"[DEBUG] No artwork found for card_id: {card_id}")
    return None

def paste_art(base, art_rect, art_img):
    if art_img is None:
        return
    x0,y0,x1,y1 = art_rect
    fitted = cover_fit(art_img, ART_W, ART_H)
    base.alpha_composite(fitted, (x0+11, y0+11))  # +10 to sit inside the bevel nicely

# ---------- card builder ----------
def build_card(row, faction_key, orb_img=None, faction_label=None, special_no_cost=False, badge_width_factor=0.35, row_index=None, total_cards=None):
    # Background
    outer = vertical_gradient((PX_W, PX_H), (40,45,55), (15,15,20)).convert("RGBA")
    outer.alpha_composite(noise_texture((PX_W,PX_H), alpha=28))

    # Frame
    frame_rect = (12,12,PX_W-12,PX_H-12)
    top_rgb, bot_rgb = {
        "espenlock": ((100,150,220),(30,60,120)),
        "stag":      ((200,60,40),(90,20,20)),
        "cow":       ((120,50,170),(45,20,80)),
        "survivor":  ((200,90,20),(100,40,5)),
        "special":   ((235,230,220),(210,205,195)),
    }.get(faction_key, ((140,140,140),(60,60,60)))

    fw, fh = frame_rect[2]-frame_rect[0], frame_rect[3]-frame_rect[1]
    fill = vertical_gradient((fw,fh), top_rgb, bot_rgb).convert("RGBA")
    fill.alpha_composite(noise_texture((fw,fh), alpha=34 if faction_key!="special" else 48))
    mask = rounded_rect_mask((fw,fh), radius=30)
    frame_layer = Image.new("RGBA", (PX_W, PX_H), (0,0,0,0))
    frame_layer.paste(fill, (frame_rect[0], frame_rect[1]), mask)
    dfl = ImageDraw.Draw(frame_layer, "RGBA")
    dfl.rounded_rectangle(frame_rect, radius=30, outline=(0,0,0,220), width=2)
    dfl.rounded_rectangle((frame_rect[0]+2,frame_rect[1]+2,frame_rect[2]-2,frame_rect[3]-2),
                          radius=28, outline=(255,255,255,80), width=2)
    outer.alpha_composite(frame_layer)

    # Regions
    name_rect, art_rect, type_rect, rules_rect, stats_rect, foot_rect = compute_regions()

    # Plaques
    for rect, rad in [(name_rect,12),(type_rect,10),(rules_rect,16),(stats_rect,14),(foot_rect,10)]:
        draw_plaque_raised(outer, rect, radius=rad, elevation=10)

    # Artwork placement (draw first, so border sits on top)
    art_img = locate_art(row)
    if art_img is not None:
        paste_art(outer, art_rect, art_img)
    # Art box outline
    draw_art_bevel(outer, art_rect)
    # Cull/make transparent the pixels inside the artwork border (no rounding, slightly inset)
    # x0, y0, x1, y1 = art_rect
    # inset = 8  # Amount to inset the rectangle so the bevel border is visible
    # mask_rect = (x0+inset, y0+inset, x1-inset+1, y1-inset+1)
    # mask_w = mask_rect[2] - mask_rect[0]
    # mask_h = mask_rect[3] - mask_rect[1]
    # art_mask = Image.new("L", (mask_w, mask_h), 0)
    # d_mask = ImageDraw.Draw(art_mask)
    # d_mask.rectangle((0, 0, mask_w, mask_h), fill=255)
    # transparent_art = Image.new("RGBA", (mask_w, mask_h), (0,0,0,0))
    # outer.paste(transparent_art, (mask_rect[0], mask_rect[1]), art_mask)

    # Header title
    d = ImageDraw.Draw(outer, "RGBA")
    font_header = load_font(size=34)
    name_text = sanitize(row.get("Name",""))[:40]
    bbox = d.textbbox((0,0), name_text, font=font_header)
    nh = bbox[3] - bbox[1]
    ny = (name_rect[1] + name_rect[3] - nh) // 2
    d.text((name_rect[0]+20, ny), name_text, font=font_header, fill=(0,0,0),
           stroke_width=2, stroke_fill=(220,220,220))

    # Orb + cost (skip for Specials)
    if not special_no_cost:
        cost_num = parse_cost_number(row.get("Resource Cost", row.get("Cost","")))
        place_orb_number_left_centered(outer, name_rect, orb_img, cost_num)

    # Type line (left)
    font_type = load_font(size=28)
    type_str = f"{sanitize(row.get('Type',''))} - {sanitize(row.get('Subtype',''))}"
    bbox = d.textbbox((0,0), type_str, font=font_type)
    th = bbox[3] - bbox[1]
    ty = (type_rect[1] + type_rect[3] - th) // 2
    d.text((type_rect[0]+20, ty), type_str[:60], font=font_type, fill=(0,0,0),
           stroke_width=2, stroke_fill=(220,220,220))

    # Faction badge (right)
    draw_faction_badge(outer, type_rect, faction_key, faction_label or "",
                       width_factor=badge_width_factor, overshoot_px=3)

    # Stats row
    font_stats = load_font(size=24)
    try:
        parts = [p.strip() for p in sanitize(row.get("Stats","")).split('/')]
        vals = {p.split(':')[0].strip().lower(): int(p.split(':')[1]) for p in parts}
        hp, atk, deff = vals.get('hp',10), vals.get('atk',2), vals.get('def',1)
    except:
        hp,atk,deff = 10,2,1
    stats_texts = [f"HP: {hp}", f"ATK: {atk}", f"DEF: {deff}"]
    widths = [d.textlength(t, font=font_stats) for t in stats_texts]
    spacing = 10
    total_w = sum(widths) + spacing*2
    start_x = (stats_rect[0]+stats_rect[2]-total_w)//2
    row_y = (stats_rect[1]+stats_rect[3])//2 - 12
    for i,t in enumerate(stats_texts):
        d.text((start_x, row_y), t, font=font_stats, fill=(0,0,0),
               stroke_width=2, stroke_fill=(220,220,220))
        start_x += widths[i] + spacing

    # Footer
    if total_cards is None:
        try:
            total_cards = int(os.environ.get("SURV_TOTAL", "1"))
        except Exception:
            total_cards = 1
    draw_footer(outer, foot_rect, row, int(row_index) if row_index is not None else (int(row.name) if hasattr(row, "name") and row.name is not None else 0), total_cards)

    # Rules + Flavor
    ability = sanitize(row.get("Abilities",""))
    flavor  = sanitize(row.get("Flavor Text",""))
    draw_rules_flavor_centered(outer, rules_rect, ability, flavor)

    return outer

# ---------- main ----------
def faction_key_from_text(text):
    s = str(text).lower()
    if "espen" in s:   return "espenlock"
    if "stag" in s:    return "stag"
    if "cow" in s or "warlock" in s: return "cow"
    if "survivor" in s:return "survivor"
    if "special" in s: return "special"
    return "survivor"

import argparse

def main(csv_path="srp_bitterroot_collection.csv", outdir="release", rownum=None):
    df = pd.read_csv(csv_path).reset_index(drop=True)
    os.environ["SURV_TOTAL"] = str(len(df))  # for footer ordinal

    # Orbs
    orb_energy   = Image.open("./source/icons/resources/orb_energy.png").convert("RGBA")    if os.path.exists("./source/icons/resources/orb_energy.png")    else None
    orb_bullets  = Image.open("./source/icons/resources/orb_munitions.png").convert("RGBA") if os.path.exists("./source/icons/resources/orb_munitions.png") else None
    orb_faith    = Image.open("./source/icons/resources/orb_faith.png").convert("RGBA")     if os.path.exists("./source/icons/resources/orb_faith.png")     else None
    orb_supplies = Image.open("./source/icons/resources/orb_supplies.png").convert("RGBA")  if os.path.exists("./source/icons/resources/orb_supplies.png")  else None
    orb_map = {"espenlock": orb_energy, "stag": orb_bullets, "cow": orb_faith, "survivor": orb_supplies, "special": None}

    if rownum is not None:
        # rownum is a list of row numbers
        rows = []
        for r in rownum:
            if not (0 <= r < len(df)):
                print(f"Row number {r} is out of range (0 to {len(df)-1})")
            else:
                rows.append((r, df.iloc[r]))
        if not rows:
            print("No valid row numbers provided.")
            return
    else:
        rows = list(df.iterrows())

    for idx, row in rows:
        fkey = faction_key_from_text(row.get("Faction",""))
        img = build_card(row,
                         fkey,
                         orb_img=orb_map[fkey],
                         faction_label=str(row.get("Faction","")),
                         special_no_cost=(fkey=="special"),
                         badge_width_factor=0.35,
                         row_index=idx,
                         total_cards=len(df))
        # Determine set/edition/collection folder
        set_name = sanitize(field(row, "Set/Edition", "Set", "Edition", "Collection", "Collection/Edition", "Set Name"))
        if not set_name:
            set_name = "UnknownSet"
        set_folder = re.sub(r"[^a-zA-Z0-9]+", "_", set_name).strip("_")[:60]
        set_outdir = os.path.join(outdir, set_folder)
        os.makedirs(set_outdir, exist_ok=True)
        # filename: prefer Card ID; fallback to slugified name
        card_id = sanitize(row.get("Card ID",""))
        if card_id:
            base = re.sub(r"[^a-zA-Z0-9]+", "_", card_id).strip("_")[:80].lower()
        else:
            nm = sanitize(row.get("Name","card"))
            base = re.sub(r"[^a-zA-Z0-9]+", "_", nm).strip("_")[:80].lower()

        outpath = os.path.join(set_outdir, f"{base}_co.png")
        # print(f"[DEBUG] Creating card for row {idx}: '{row.get('Name','')}' -> {outpath}")
        # Create a 1024x2048 transparent canvas and anchor the card to the bottom left
        pow2_w, pow2_h = 1024, 2048
        padded = Image.new("RGBA", (pow2_w, pow2_h), (0,0,0,0))
        padded.paste(img, (0, pow2_h - PX_H))
        padded.save(outpath, dpi=(DPI, DPI))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate collectible card PNGs from CSV.")
    parser.add_argument("--csv", type=str, default="srp_bitterroot_collection.csv", help="CSV file to use")
    parser.add_argument("--outdir", type=str, default="release", help="Output directory")
    parser.add_argument("--row", type=str, default=None, help="Comma-separated list of row numbers (0-based) to generate only those cards")
    args = parser.parse_args()
    if args.row is not None:
        try:
            rownums = [int(x.strip()) for x in args.row.split(",") if x.strip()]
        except ValueError:
            print("Invalid value for --row. Please provide a comma-separated list of integers.")
            exit(1)
    else:
        rownums = None
    main(csv_path=args.csv, outdir=args.outdir, rownum=rownums)
