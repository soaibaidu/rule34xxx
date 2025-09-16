# Survivalists Card Templates — Concise Generator (2025)
# Requires: Pillow, pandas
#
# This script generates collectible card PNGs from a CSV file, using Pillow for image processing
# and pandas for CSV parsing. The card layout, art, and text are all programmatically rendered.

import os
import re
import shutil
import argparse
import random
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# CSV column name constants
COL_ROW_NUMBER = "Row Number"
COL_CARD_ID = "Card ID"
COL_NAME = "Name"
COL_FACTION = "Faction"
COL_RARITY = "Rarity"
COL_TYPE = "Type"
COL_SUBTYPE = "Subtype"
COL_COST = "Cost"
COL_POWER = "Power"
COL_TOUGHNESS = "Toughness"
COL_ABILITIES = "Abilities"
COL_FLAVOR = "Flavor Text"
COL_SET_EDITION = "Set/Edition"

# Map single-letter cost codes to faction keys
FACTION_COST_CODE_MAP = {
    'E': 'espenlock',
    'M': 'stag',
    'F': 'cow',
    'S': 'survivor',
    # Add more as needed
}
# Faction data abstraction: all color, orb, and badge info in one place
FACTION_DATA = {
    "espenlock": {
        "gradient": [(100,150,220), (60,110,180), (30,60,120)],
        "badge": ((70,120,200),(35,70,140),(255,255,255),(0,0,0)),
        "orb": "orb_energy.png",
        "orb_img": None,
        "alias": ["espen", "espenlock"],
    },
    "stag": {
        "gradient": [(200,60,40), (140,30,25), (90,20,20)],
        "badge": ((200,60,40),(90,20,20),(0,0,0),(255,255,255)),
        "orb": "orb_munitions.png",
        "orb_img": None,
        "alias": ["stag"],
    },
    "cow": {
        "gradient": [(120,50,170), (80,30,120), (45,20,80)],
        "badge": ((150,60,200),(80,30,120),(255,255,255),(0,0,0)),
        "orb": "orb_faith.png",
        "orb_img": None,
        "alias": ["cow", "warlock"],
    },
    "survivor": {
        "gradient": [(200,90,20), (150,60,10), (100,40,5)],
        "badge": ((220,120,40),(160,70,10),(0,0,0),(255,255,255)),
        "orb": "orb_supplies.png",
        "orb_img": None,
        "alias": ["survivor"],
    },
    "special": {
        "gradient": [(235,230,220), (210,205,195)],
        "badge": ((240,235,225),(200,195,185),(0,0,0),(255,255,255)),
        "orb": None,
        "orb_img": None,
        "alias": ["special"],
    },
    "players": {
        "gradient": [(235,230,220), (210,205,195)],
        "badge": ((240,235,225),(200,195,185),(0,0,0),(255,255,255)),
        "orb": None,
        "orb_img": None,
        "alias": ["players"],
    },
}
# Preload orb images for each faction at startup
def preload_orb_images():
    for fkey, data in FACTION_DATA.items():
        orb_file = data.get("orb")
        if orb_file:
            orb_path = os.path.join("source", "icons", "resources", orb_file)
            if os.path.isfile(orb_path):
                try:
                    data["orb_img"] = Image.open(orb_path).convert("RGBA")
                except Exception as e:
                    print(f"[DEBUG] Failed to load orb image: {orb_path} ({e})")
            else:
                data["orb_img"] = None
        else:
            data["orb_img"] = None

preload_orb_images()

PX_W, PX_H = 750, 1024  # Card width and height in pixels
DPI = 300               # Output DPI for PNGs
ART_W, ART_H = 645, 339 # Artwork region size

# Map a faction string to a canonical faction key using FACTION_DATA aliases
def faction_key_from_text(text):
    s = str(text).lower()
    for key, data in FACTION_DATA.items():
        for alias in data.get("alias", []):
            if alias in s:
                return key
    return "XXX"

# Convert value to string, treating NaN/None as empty string
def sanitize(val):
    s = str(val) if val is not None else ""
    return "" if s.lower() in ("nan","none") else s

# Load a font of the given size, optionally italic
def load_font(size=24, italic=False):
    try:
        if italic:
            return ImageFont.truetype("source/fonts/DejaVuSerif-Italic.ttf", size)
        return ImageFont.truetype("source/fonts/DejaVuSerif-Bold.ttf", size)
    except:
        # Fallback to regular if bold/italic not found
        return ImageFont.truetype("source/fonts/DejaVuSerif.ttf", size)

# Create a vertical gradient image from top color to bottom color
def vertical_gradient(size, *colors):
    w, h = size
    if len(colors) < 2:
        raise ValueError("At least two colors required for gradient")
    base = Image.new("RGB", size, color=colors[0])
    col = Image.new("RGB", (1, h))
    n = len(colors) - 1
    for y in range(h):
        t = y / max(1, h-1)
        # Find which segment this y falls into
        seg = min(int(t * n), n-1)
        t0 = seg / n
        t1 = (seg+1) / n
        local_t = (t - t0) / (t1 - t0) if t1 > t0 else 0
        c0 = colors[seg]
        c1 = colors[seg+1]
        r = int(c0[0] + (c1[0]-c0[0]) * local_t)
        g = int(c0[1] + (c1[1]-c0[1]) * local_t)
        b = int(c0[2] + (c1[2]-c0[2]) * local_t)
        col.putpixel((0, y), (r, g, b))
    base.paste(col.resize((w, h)))
    return base

# Generate a grayscale noise texture with given alpha
def noise_texture(size, alpha=35):
    noise = Image.effect_noise(size, 30).convert("L")
    return Image.merge("RGBA", (noise, noise, noise, Image.new("L", size, alpha)))

# Create a mask for rounded rectangles
def rounded_rect_mask(size, radius):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0,0,size[0],size[1]), radius=radius, fill=255)
    return m

# Generate a parchment-like background for plaques
def plaque_parchment(size):
    img = vertical_gradient(size, (242,233,208), (224,212,184)).convert("RGBA")
    img.alpha_composite(noise_texture(size, alpha=22))
    return img

# Draw a raised plaque with shadow and border
def draw_plaque_raised(base, rect, radius=12, elevation=10):
    x0,y0,x1,y1 = rect
    w,h = x1-x0, y1-y0
    shadow = Image.new("RGBA", (PX_W, PX_H), (0,0,0,0))
    m = rounded_rect_mask((w,h), radius)
    shcut = Image.new("RGBA", (w,h), (0,0,0,160))
    shadow.paste(shcut, (x0 + elevation//2, y0 + elevation), m)
    shadow = shadow.filter(ImageFilter.GaussianBlur(elevation//2 + 4))
    body = Image.new("RGBA", (PX_W, PX_H), (0,0,0,0))
    fill = plaque_parchment((w,h))
    body.paste(fill, (x0,y0), m)
    d = ImageDraw.Draw(body, "RGBA")
    d.rounded_rectangle(rect, radius=radius, outline=(0,0,0,220), width=2)
    for inset, color, wdt in [(3, (255,255,255,140), 2), (5, (0,0,0,90), 2)]:
        d.rounded_rectangle((x0+inset,y0+inset,x1-inset,y1-inset), radius=max(1,radius-inset), outline=color, width=wdt)
    base.alpha_composite(shadow)
    base.alpha_composite(body)

# Draw a beveled border around the art region
def draw_art_bevel(base, rect):
    x0,y0,x1,y1 = rect
    layer = Image.new("RGBA", (PX_W, PX_H), (0,0,0,0))
    d = ImageDraw.Draw(layer, "RGBA")
    d.rectangle(rect, outline=(0,0,0,230), width=6)
    for pad, color, wdt in [(6, (255,255,255,100), 2), (10, (0,0,0,90), 2)]:
        d.rectangle((x0+pad,y0+pad,x1-pad,y1-pad), outline=color, width=wdt)
    base.alpha_composite(layer)

# Draw text centered and wrapped within a box
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

# Draw the rules text and flavor text, centered and wrapped, in the rules area
def draw_rules_flavor_centered(base, rules_rect, ability, flavor):
    d = ImageDraw.Draw(base, "RGBA")
    ability_size, flavor_size = 25, 24
    min_ability, min_flavor = 18, 18
    ability_line_gap, para_gap, divider_gap = 4, 8, 12
    def get_fonts(a_size, f_size):
        return load_font(a_size), load_font(f_size, italic=True)
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
        pad_top, pad_bottom = 18, 20
        max_w = rules_rect[2]-rules_rect[0]-40
        y = pad_top
        for para in (ability or "").split("\n"):
            para = para.strip()
            if not para: continue
            for _ in wrap_left(para, fa, max_w):
                bbox = d.textbbox((0,0), "Hg", font=fa)
                y += (bbox[3] - bbox[1]) + ability_line_gap
            y += para_gap
        y += divider_gap
        if (flavor or "").strip():
            for _ in wrap_left(flavor, ff, max_w):
                bbox = d.textbbox((0,0), "Hg", font=ff)
                y += (bbox[3] - bbox[1]) + 4
        y += pad_bottom
        return y
    available = rules_rect[3]-rules_rect[1]
    while True:
        total_h = measure(ability_size, flavor_size)
        if total_h <= available or (ability_size <= min_ability and flavor_size <= min_flavor): break
        if ability_size > min_ability: ability_size -= 1
        elif flavor_size > min_flavor: flavor_size -= 1
        else: break
    fa, ff = get_fonts(ability_size, flavor_size)
    pad_top = 18
    y = rules_rect[1] + pad_top
    max_w = rules_rect[2]-rules_rect[0]-40
    for para in (ability or "").split("\n"):
        para = para.strip()
        if not para: continue
        for line in wrap_left(para, fa, max_w):
            d.text((rules_rect[0]+20, y), line, font=fa, fill=(0,0,0), stroke_width=2, stroke_fill=(220,220,220))
            bbox = d.textbbox((0,0), "Hg", font=fa)
            y += (bbox[3] - bbox[1]) + ability_line_gap
        y += para_gap
    y += divider_gap
    d.line((rules_rect[0]+30, y, rules_rect[2]-30, y), fill=(0,0,0,200), width=2)
    y += divider_gap
    if (flavor or "").strip():
        for line in wrap_left(flavor, ff, max_w):
            tw = d.textlength(line, font=ff)
            tx = rules_rect[0] + 20 + (max_w - tw)//2
            d.text((tx, y), line, font=ff, fill=(60,60,60))
            bbox = d.textbbox((0,0), "Hg", font=ff)
            y += (bbox[3] - bbox[1]) + 4

# Parse cost string into a list of (faction_key, count) tuples
def parse_cost_types(cost):
    s = sanitize(cost)
    # Example cost: "2E 1F" or "3S" or "1E 1F 1S"
    result = []
    for part in re.findall(r"(\d+)([A-Za-z])", s):
        num, letter = part
        fkey = FACTION_COST_CODE_MAP.get(letter.upper())
        if fkey:
            result.append((fkey, int(num)))
    return result

# Place the cost orbs (multi-type) at the right of the name plaque
def place_orb_number_left_centered(base, name_rect, row):
    cost = sanitize(row.get(COL_COST, ""))
    # Parse cost string for all cost codes and build orb image list
    # Example: "2E 1F 1M" -> [espenlock, espenlock, cow, stag]
    tokens = []
    for part in re.findall(r"(\d+)([A-Za-z])", cost):
        num, code = part
        fkey = FACTION_COST_CODE_MAP.get(code.upper())
        if fkey:
            tokens.extend([fkey] * int(num))
    total_tokens = len(tokens)
    if total_tokens == 0:
        return
    plaque_h = name_rect[3] - name_rect[1]
    token_size = int(plaque_h * 0.35)
    gap = 4
    layer = Image.new("RGBA", (PX_W, PX_H), (0,0,0,0))

    # Determine row split
    if total_tokens == 1:
        # Single orb, center it
        x = name_rect[2] - 10 - token_size
        y = name_rect[1] + (plaque_h - token_size) // 2
        orb_img = FACTION_DATA.get(tokens[0], {}).get("orb_img")
        if orb_img:
            token_img = orb_img.copy().convert("RGBA").resize((token_size, token_size), Image.Resampling.LANCZOS)
            layer.paste(token_img, (int(x), int(y)), token_img)
    elif total_tokens == 2:
        # Two orbs, center both in one row
        total_row_w = 2 * token_size + gap
        y = name_rect[1] + (plaque_h - token_size) // 2
        xs = [name_rect[2] - 10 - total_row_w + i * (token_size + gap) for i in range(2)]
        for i in range(2):
            orb_img = FACTION_DATA.get(tokens[i], {}).get("orb_img")
            if orb_img:
                token_img = orb_img.copy().convert("RGBA").resize((token_size, token_size), Image.Resampling.LANCZOS)
                layer.paste(token_img, (int(xs[i]), int(y)), token_img)
    else:
        # 3 or more orbs: split into two rows, bottom row gets extra if odd
        n_bottom = (total_tokens + 1) // 2
        n_top = total_tokens // 2
        n_rows = 2
        total_height = n_rows * token_size + gap
        start_y = name_rect[1] + (plaque_h - total_height) // 2
        y_top = start_y
        y_bottom = start_y + token_size + gap
        # Bottom row (first n_bottom tokens)
        total_row_w_b = n_bottom * token_size + (n_bottom - 1) * gap
        xs_bottom = [name_rect[2] - 10 - total_row_w_b + i * (token_size + gap) for i in range(n_bottom)]
        # Top row (next n_top tokens)
        total_row_w_t = n_top * token_size + (n_top - 1) * gap if n_top > 0 else 0
        xs_top = [name_rect[2] - 10 - total_row_w_t + i * (token_size + gap) for i in range(n_top)]
        # Place bottom row
        for i in range(n_bottom):
            orb_img = FACTION_DATA.get(tokens[i], {}).get("orb_img")
            if orb_img:
                token_img = orb_img.copy().convert("RGBA").resize((token_size, token_size), Image.Resampling.LANCZOS)
                layer.paste(token_img, (int(xs_bottom[i]), int(y_bottom)), token_img)
        # Place top row
        for i in range(n_top):
            orb_img = FACTION_DATA.get(tokens[n_bottom + i], {}).get("orb_img")
            if orb_img:
                token_img = orb_img.copy().convert("RGBA").resize((token_size, token_size), Image.Resampling.LANCZOS)
                layer.paste(token_img, (int(xs_top[i]), int(y_top)), token_img)
    base.alpha_composite(layer)

# Draw the colored faction badge at the right of the type plaque
def draw_faction_badge(base, type_rect, faction_key, label_text, width_factor=0.35, overshoot_px=3):
    x0,y0,x1,y1 = type_rect
    h = y1 - y0
    w_total = x1 - x0
    badge_w = int(w_total * width_factor)
    rx1 = x1 + overshoot_px
    rx0 = rx1 - badge_w
    w = rx1 - rx0
    c1,c2,txt,stroke = FACTION_DATA.get(faction_key, {}).get("badge", ((140,140,140),(60,60,60),(0,0,0),(255,255,255)))
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
    d.rounded_rectangle((rx0+2,y0+2,rx1-2,y1-2), radius=max(1, radius-2), outline=(255,255,255,90), width=2)
    font = load_font(size=26)
    tw = d.textlength(label_text, font=font)
    bbox = d.textbbox((0,0), "Hg", font=font)
    th = bbox[3] - bbox[1]
    d.text((rx0 + (w - tw)//2, y0 + (h - th-6)//2), label_text, font=font, fill=txt, stroke_width=2, stroke_fill=stroke)

# Compute the bounding rectangles for each card region
def compute_regions():
    ART_INSET = 32
    name_rect = (ART_INSET, 20, PX_W-ART_INSET, 100)
    art_rect  = (ART_INSET+10, name_rect[3]+5, PX_W-ART_INSET-10, name_rect[3]+365)
    type_rect = (ART_INSET, art_rect[3]+6, PX_W-ART_INSET, art_rect[3]+54)
    stats_rect= (PX_W//2-180, PX_H-115, PX_W//2+180, PX_H-75)
    foot_rect = (ART_INSET, PX_H-70, PX_W-ART_INSET, PX_H-10)
    rules_rect= (ART_INSET, type_rect[3]+5, PX_W-ART_INSET, stats_rect[1]-5)
    return name_rect, art_rect, type_rect, rules_rect, stats_rect, foot_rect

# Draw the footer plaque with set/edition, card ID, and card number
def draw_footer(base, foot_rect, row, index, total_cards):
    d = ImageDraw.Draw(base, "RGBA")
    # Draw the raised plaque background for the footer
    draw_plaque_raised(base, foot_rect, radius=10, elevation=10)
    font = load_font(size=22)
    # Draw the set/edition text on the left
    left = sanitize(row.get(COL_SET_EDITION, ""))
    bbox = d.textbbox((0,0), left, font=font)
    lh = bbox[3] - bbox[1]
    # // is integer division in Python, so this centers the text vertically
    d.text((foot_rect[0]+20, (foot_rect[1]+foot_rect[3]-lh)//2), left, font=font, fill=(0,0,0), stroke_width=2, stroke_fill=(220,220,220))
    # Prepare the card ID and ordinal (e.g., 3/30) for the right side
    card_id = sanitize(row.get(COL_CARD_ID, ""))
    ordinal = f"{int(index) + 1}/{int(total_cards) if total_cards is not None else 1}"
    # Measure text bounding boxes for alignment
    bbox_id = d.textbbox((0,0), card_id, font=font)
    tw_id = bbox_id[2] - bbox_id[0]
    th_id = bbox_id[3] - bbox_id[1]
    bbox_ord = d.textbbox((0,0), ordinal, font=font)
    tw_ord = bbox_ord[2] - bbox_ord[0]
    th_ord = bbox_ord[3] - bbox_ord[1]
    # Add padding between lines and from the right edge
    vertical_pad = 8  # space between ordinal and card ID
    right_pad = 10    # space from right edge
    between_pad = 2
    # Stack the ordinal above the card ID, centered vertically with padding
    total_h = th_id + th_ord + vertical_pad
    top_y = (foot_rect[1]+foot_rect[3]-total_h)//2
    x_right = foot_rect[2] - right_pad
    # Draw ordinal (e.g., 3/30) above card ID, both right-aligned with padding
    d.text((x_right - tw_ord, top_y), ordinal, font=font, fill=(0,0,0), stroke_width=2, stroke_fill=(220,220,220))
    d.text((x_right - tw_id, top_y + th_ord + between_pad), card_id, font=font, fill=(0,0,0), stroke_width=2, stroke_fill=(220,220,220))

# Crop and resize an image to cover a target region
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

def collection_abbr(set_folder):
    mapping = {
        'srp_bitterroot': 'srp_br',
        'srp_player': 'srp_pl',
        # Add more mappings as needed
    }
    key = set_folder.lower()
    return mapping.get(key, key)

# Locate and load the artwork image for a card row
def locate_art(row):
    # Use abbreviated collection name and card id for artwork path
    set_name = sanitize(row.get(COL_SET_EDITION, ""))
    set_folder = re.sub(r"[^a-zA-Z0-9]+", "_", set_name).strip("_").lower()
    abbr = collection_abbr(set_folder)
    row_index = str(row.get(COL_ROW_NUMBER, ""))
    artwork_path = f"source/art/{abbr}/{abbr}_{row_index}.png"
    if os.path.isfile(artwork_path):
        try:
            return Image.open(artwork_path).convert("RGBA")
        except Exception as e:
            print(f"[DEBUG] Failed to open artwork: {artwork_path} ({e})")
    return None

# Paste the fitted artwork image into the art region
def paste_art(base, art_rect, art_img):
    if art_img is None: return
    x0,y0,x1,y1 = art_rect
    fitted = cover_fit(art_img, ART_W, ART_H)
    base.alpha_composite(fitted, (x0+11, y0+11))

# Draw the card frame and background
def draw_card_frame(outer, faction_key):
    frame_rect = (4,4,PX_W-4,PX_H-4)
    colors = FACTION_DATA.get(faction_key, {}).get("gradient", [(140,140,140),(60,60,60)])
    fw, fh = frame_rect[2]-frame_rect[0], frame_rect[3]-frame_rect[1]
    fill = vertical_gradient((fw,fh), *colors).convert("RGBA")
    fill.alpha_composite(noise_texture((fw,fh), alpha=34 if faction_key!="special" else 48))
    mask = rounded_rect_mask((fw,fh), radius=30)
    frame_layer = Image.new("RGBA", (PX_W, PX_H), (0,0,0,0))
    frame_layer.paste(fill, (frame_rect[0], frame_rect[1]), mask)
    dfl = ImageDraw.Draw(frame_layer, "RGBA")
    dfl.rounded_rectangle(frame_rect, radius=30, outline=(0,0,0,220), width=2)
    dfl.rounded_rectangle((frame_rect[0]+2,frame_rect[1]+2,frame_rect[2]-2,frame_rect[3]-2), radius=28, outline=(255,255,255,80), width=2)
    outer.alpha_composite(frame_layer)

# Draw all plaques (name, type, rules, stats, footer)
def draw_card_plaques(outer, regions):
    for rect, rad in zip(regions, [12,10,16,14,10]):
        draw_plaque_raised(outer, rect, radius=rad, elevation=10)

# Draw the card artwork
def draw_card_art(outer, art_rect, row):
    art_img = locate_art(row)
    if art_img is not None:
        paste_art(outer, art_rect, art_img)
    draw_art_bevel(outer, art_rect)

# Draw the card name and cost
def draw_card_name_and_cost(outer, name_rect, row):
    d = ImageDraw.Draw(outer, "RGBA")
    font_header = load_font(size=34)
    name_text = sanitize(row.get(COL_NAME, ""))[:40]
    name_y = name_rect[1] + 20
    d.text((name_rect[0]+20, name_y), name_text, font=font_header, fill=(0,0,0), stroke_width=2, stroke_fill=(220,220,220))
    place_orb_number_left_centered(outer, name_rect, row)

# Draw the card type and faction badge
def draw_card_type_and_badge(outer, type_rect, row, faction_key, faction_label, badge_width_factor):
    d = ImageDraw.Draw(outer, "RGBA")
    font_type = load_font(size=28)
    type_str = f"{sanitize(row.get(COL_TYPE,''))} - {sanitize(row.get(COL_SUBTYPE,''))}"
    # Place text so the top (ascent) is always at a fixed offset from type_rect[1]
    ty = type_rect[1] + 8  # 22px padding from top, adjust as needed
    d.text((type_rect[0]+20, ty), type_str[:60], font=font_type, fill=(0,0,0), stroke_width=2, stroke_fill=(220,220,220))
    draw_faction_badge(outer, type_rect, faction_key, faction_label or "", width_factor=badge_width_factor, overshoot_px=3)

# Draw the card stats (power/toughness)
def draw_card_stats(outer, stats_rect, row):
    d = ImageDraw.Draw(outer, "RGBA")
    font_stats = load_font(size=24)
    try:
        power = int(sanitize(row.get(COL_POWER, "2")))
    except:
        power = 0
    try:
        toughness = int(sanitize(row.get(COL_TOUGHNESS, "1")))
    except:
        toughness = 0
    stats_texts = [f"POW: {power}", f"DEF: {toughness}"]
    widths = [d.textlength(t, font=font_stats) for t in stats_texts]
    spacing = 20
    total_w = sum(widths) + spacing*(len(stats_texts)-1)
    start_x = (stats_rect[0]+stats_rect[2]-total_w)//2
    row_y = (stats_rect[1]+stats_rect[3])//2 - 12
    for i,t in enumerate(stats_texts):
        d.text((start_x, row_y), t, font=font_stats, fill=(0,0,0), stroke_width=2, stroke_fill=(220,220,220))
        start_x += widths[i] + spacing

# Draw the card footer
def draw_card_footer(outer, foot_rect, row, row_index, total_cards):
    if total_cards is None:
        try: total_cards = int(os.environ.get("SURV_TOTAL", "1"))
        except Exception: total_cards = 1
    draw_footer(outer, foot_rect, row, int(row_index) if row_index is not None else (int(row.name) if hasattr(row, "name") and row.name is not None else 0), total_cards)

# Draw the card rules and flavor text
def draw_card_rules_and_flavor(outer, rules_rect, row):
    ability = sanitize(row.get(COL_ABILITIES, ""))
    flavor  = sanitize(row.get(COL_FLAVOR, ""))
    draw_rules_flavor_centered(outer, rules_rect, ability, flavor)

# Build and render a single card image from a CSV row
def build_card(row, faction_key, faction_label=None, badge_width_factor=0.35, row_index=None, total_cards=None):
    outer = vertical_gradient((PX_W, PX_H), (40,45,55), (15,15,20)).convert("RGBA")
    outer.alpha_composite(noise_texture((PX_W,PX_H), alpha=28))
    name_rect, art_rect, type_rect, rules_rect, stats_rect, foot_rect = compute_regions()
    draw_card_frame(outer, faction_key)
    draw_card_plaques(outer, [name_rect, type_rect, rules_rect, stats_rect, foot_rect])
    draw_card_art(outer, art_rect, row)
    draw_card_name_and_cost(outer, name_rect, row)
    draw_card_type_and_badge(outer, type_rect, row, faction_key, faction_label, badge_width_factor)
    draw_card_stats(outer, stats_rect, row)
    draw_card_footer(outer, foot_rect, row, row_index, total_cards)
    draw_card_rules_and_flavor(outer, rules_rect, row)
    return outer

# Main entry point: read CSV, generate cards, and save PNGs
def main(csv_path="srp_bitterroot_collection.csv", outdir="release", rows=None, verbose=False):
    df = pd.read_csv(csv_path).reset_index(drop=True)
    os.environ["SURV_TOTAL"] = str(len(df))
    # Select rows to process (all or subset)
    selected_rows = [(r, df.iloc[r]) for r in rows] if rows else list(df.iterrows())

    # Remove the output set directory before generating new cards
    # Find all set folders that will be generated in this run
    set_names = set()
    for _, row in selected_rows:
        set_name = sanitize(row.get(COL_SET_EDITION))
        set_folder = re.sub(r"[^a-zA-Z0-9]+", "_", set_name).strip("_")[:60]
        set_names.add(set_folder)
    for set_folder in set_names:
        set_outdir = os.path.join(outdir, set_folder)
        if os.path.exists(set_outdir):
            shutil.rmtree(set_outdir)

    for idx, row in selected_rows:
        fkey = faction_key_from_text(row.get(COL_FACTION, ""))
        img = build_card(row, fkey, faction_label=str(row.get(COL_FACTION, "")), badge_width_factor=0.35, row_index=idx, total_cards=len(df))
        # Prepare output directory and filename
        set_name = sanitize(row.get(COL_SET_EDITION))
        set_folder = re.sub(r"[^a-zA-Z0-9]+", "_", set_name).strip("_")[:60]
        set_outdir = os.path.join(outdir, set_folder)
        os.makedirs(set_outdir, exist_ok=True)
        # Output filename: collection_rowindex_co.png
        abbr = collection_abbr(set_folder)
        out_filename = f"{abbr}_{idx+1}_co.png"
        outpath = os.path.join(set_outdir, out_filename)
        # Pad to 1024x1024 for uniformity
        pow2_w, pow2_h = 1024, 1024
        padded = Image.new("RGBA", (pow2_w, pow2_h), (0,0,0,0))
        padded.paste(img, (0, pow2_h - PX_H))
        padded.save(outpath, dpi=(DPI, DPI))
        # Collect card name and output path
        card_name = sanitize(row.get(COL_NAME, out_filename))
        if verbose:
            print(f"[VERBOSE] Generated card: {card_name} -> {outpath}")

# Command-line interface for running the generator
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate collectible card PNGs from CSV.")
    parser.add_argument("--csv", type=str, default="srp_bitterroot_collection.csv", help="CSV file to use")
    parser.add_argument("--outdir", type=str, default="release", help="Output directory")
    parser.add_argument("--rows", type=str, default=None, help="Comma-separated list of row numbers (0-based) to generate only those cards")
    parser.add_argument("--random", nargs="?", const=5, type=int, default=None, help="Generate N random cards (default 5 if not specified)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug output during card generation")
    args = parser.parse_args()
    df = pd.read_csv(args.csv).reset_index(drop=True)
    if args.random is not None:
        n = args.random if args.random > 0 else 5
        if n > len(df):
            n = len(df)
        rows = random.sample(range(len(df)), n)
    elif args.rows:
        rows = [int(x.strip()) for x in args.rows.split(",") if x.strip()]
    else:
        rows = None
    main(csv_path=args.csv, outdir=args.outdir, rows=rows, verbose=args.verbose)