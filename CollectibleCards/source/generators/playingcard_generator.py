from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1024, 1024               # full canvas (power of two)
CARD_W, CARD_H = 730, 1024      # 5:7 ratio card anchored bottom-left
PAD_X, PAD_Y = 45, 50           # padding for pip set
NUMBER_SIZE = 80                   # pip font size
SUIT_SIZE = 110                   # pip font size
PIP_SIZE = 100                   # pip font size
OUT_DIR = "release/playingcards"       # folder to save PNGs

# ---------------- SHARED CONSTANTS ----------------
INDEX_MARGIN_X = 64
INDEX_MARGIN_Y = 90
INDEX_MARGIN_Y_TOP = 180
INDEX_MARGIN_Y_BOTTOM = 180
FACE_BORDER_PAD = 5
FACE_BORDER_RADIUS = 32
PIP_EXTRA_PAD = 150


# Try loading serif fonts from the fonts directory
FONTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'fonts')
def load_font(name="DejaVuSerif-Bold.ttf", size=60):
    font_path = os.path.join(FONTS_DIR, name)
    try:
        return ImageFont.truetype(font_path, size)
    except OSError:
        print(f"[WARN] Could not load {font_path}, using default font.")
        return ImageFont.load_default()

FONT_INDEX = load_font("CarterOne-Regular.ttf", size=NUMBER_SIZE)
FONT_SUIT  = load_font(size=SUIT_SIZE)
FONT_PIP   = load_font(size=PIP_SIZE)

# ---------------- DRAW HELPERS ----------------
def draw_rotated_index(base, rank, suit, color, x, y, font_index, font_suit, padding=8, border=2):
    """
    Copies the top-left index and suit, rotates it 180 degrees, and pastes at (x, y) center.
    """
    # Define the region to copy (rectangle: taller than wide)
    region_w = 121  # width of the region
    region_h = 170  # height of the region
    region_x = INDEX_MARGIN_X - region_w // 2
    region_y = min(INDEX_MARGIN_Y, INDEX_MARGIN_Y_TOP) - region_h // 5
    region_x = max(0, region_x)
    region_y = max(0, region_y)
    box = (region_x, region_y, region_x + region_w, region_y + region_h)

    # Crop the region from the base image
    region = base.crop(box)
    # Rotate the region 180 degrees
    rotated = region.rotate(180, expand=False)

    # Paste the rotated region at the desired (x, y) center
    paste_x = int(x - region_w // 2)
    paste_y = int(y - region_h + 35)
    base.paste(rotated, (paste_x, paste_y), rotated)

def draw_card_base(draw):
    """Draw the rounded rectangle card with double border."""
    r = 40  # corner radius
    # Outer rect
    draw.rounded_rectangle([0,0,CARD_W,CARD_H], radius=r,
                           fill="white", outline="black", width=8)
    # Inner rect
    pad2 = 14
    draw.rounded_rectangle([pad2,pad2,CARD_W-pad2,CARD_H-pad2],
                           radius=int(r*0.8), fill=None, outline="#444", width=3)

def draw_face_art_border(draw):
    """Draw an inner border for face card artwork, fitting within number/suit margins."""
    # Width: slightly smaller than the margin created by the number/suit indices
    border_inset_x = INDEX_MARGIN_X + 45
    x0 = border_inset_x
    x1 = CARD_W - border_inset_x

    # Height: 120px from the top and bottom edges
    border_inset_y = 100
    y0 = border_inset_y
    y1 = CARD_H - border_inset_y

    r = FACE_BORDER_RADIUS
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, outline="#888", width=6)

def draw_index(base, draw, rank, suit, color="black"):
    """Draw top-left and bottom-right indices."""
    # Top-Left
    draw.text((INDEX_MARGIN_X, INDEX_MARGIN_Y), rank, font=FONT_INDEX, fill=color, anchor="mm")
    draw.text((INDEX_MARGIN_X, INDEX_MARGIN_Y_TOP), suit, font=FONT_SUIT, fill=color, anchor="mm")

    # Bottom-Right (rotated 180 degrees)
    draw_rotated_index(
        base,
        rank,
        suit,
        color,
        CARD_W - INDEX_MARGIN_X,
        CARD_H - INDEX_MARGIN_Y,
        FONT_INDEX,
        FONT_SUIT,
        padding=8,
        border=2
    )
    # Old code for reference:
    # draw.text((CARD_W - INDEX_MARGIN_X, CARD_H - INDEX_MARGIN_Y), rank, font=FONT_INDEX, fill=color, anchor="mm")
    # draw.text((CARD_W - INDEX_MARGIN_X, CARD_H - INDEX_MARGIN_Y_TOP), suit, font=FONT_SUIT, fill=color, anchor="mm")

# ---------------- PIP POSITIONS ----------------
def pip_grid_positions(rank):
    """Return pip center positions for number cards, per new requirements."""
    SET_L, SET_R = PAD_X, CARD_W - PAD_X
    # Add extra top/bottom padding for pips
    SET_B, SET_T = PAD_Y + PIP_EXTRA_PAD, CARD_H - PAD_Y - PIP_EXTRA_PAD
    def lerp(a, b, t): return a + (b - a) * t

    # For 2 and 3: vertical center column
    if rank == "A":
        return [(lerp(SET_L, SET_R, 0.5), lerp(SET_B, SET_T, 0.5))]
    if rank in ["J", "Q", "K"]:
        # Face cards: single large suit glyph in the center
        return [(lerp(SET_L, SET_R, 0.5), lerp(SET_B, SET_T, 0.5))]
    if rank == "2":
        # Use same logic as even numbers: two rows, single column
        rows = 2
        y_vals = [lerp(SET_B, SET_T, t) for t in [i/(rows-1) for i in range(rows)]]
        return [(lerp(SET_L, SET_R, 0.5), y) for y in y_vals]
    if rank == "3":
        # Use same logic as odd numbers: three rows, single column
        rows = 3
        y_vals = [lerp(SET_B, SET_T, t) for t in [i/(rows-1) for i in range(rows)]]
        return [(lerp(SET_L, SET_R, 0.5), y) for y in y_vals]

    # For 4-10: two columns, evenly spaced rows
    n = int(rank)
    if 4 <= n <= 10:
        # Number of rows for even numbers
        if n % 2 == 0:
            rows = n // 2
            y_vals = [lerp(SET_B, SET_T, t) for t in [i/(rows-1) if rows>1 else 0.5 for i in range(rows)]]
            positions = []
            for y in y_vals:
                positions.append((lerp(SET_L, SET_R, 0.3), y))
                positions.append((lerp(SET_L, SET_R, 0.7), y))
            return positions
        # Odd numbers: center pip(s) between columns, offset
        else:
            # Even base (n-1), plus center pip(s)
            base = pip_grid_positions(str(n-1))
            # Find center y between rows
            rows = (n-1)//2
            y_vals = [lerp(SET_B, SET_T, t) for t in [i/(rows-1) if rows>1 else 0.5 for i in range(rows)]]
            center_y = [ (y_vals[i]+y_vals[i+1])/2 for i in range(len(y_vals)-1) ]
            # For 5, 7, 9: add center pip(s) at center between columns
            extra = []
            if n == 5:
                extra = [(lerp(SET_L, SET_R, 0.5), lerp(SET_B, SET_T, 0.5))]
            elif n == 7:
                extra = [
                    (lerp(SET_L, SET_R, 0.5), center_y[0]),
                ]
            elif n == 9:
                extra = [
                    (lerp(SET_L, SET_R, 0.5), center_y[1]),
                ]
            return base + extra
    return []

def draw_pips(base, rank, suit, color="black"):
    positions = pip_grid_positions(rank)
    if rank == "A":
        # Draw a very large suit glyph for aces
        x, y = positions[0]
        size = PIP_SIZE * 7
        pip = Image.new("RGBA", (size, size), (0,0,0,0))
        d = ImageDraw.Draw(pip)
        d.text((size//2, size//2), suit, font=ImageFont.truetype(os.path.join(FONTS_DIR, "DejaVuSerif-Bold.ttf"), size-80), fill=color, anchor="mm")
        base.paste(pip, (int(x-size//2), int(y-size//2)), pip)
    else:
        for (x, y) in positions:
            pip = Image.new("RGBA", (100, 100), (0,0,0,0))
            d = ImageDraw.Draw(pip)
            d.text((50, 50), suit, font=FONT_PIP, fill=color, anchor="mm")
            base.paste(pip, (int(x-50), int(y-50)), pip)

# ---------------- MAIN ----------------
def make_card(rank="A", suit="♠", outpath="card.png", color="black"):
    base = Image.new("RGBA",(W,H),(0,0,0,0))  # transparent canvas
    draw = ImageDraw.Draw(base)
    draw_card_base(draw)
    draw_index(base, draw, rank, suit, color)
    if rank in ["J", "Q", "K"]:
        draw_face_art_border(draw)
    draw_pips(base, rank, suit, color)
    base.save(outpath)
    print(f"Saved {outpath}")

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
    suits = [
        ("♠", "spades", "black"),
        ("♥", "hearts", "#B22222"),  # dark red
        ("♦", "diamonds", "#B22222"),  # dark red
        ("♣", "clubs", "black"),
    ]
    for suit, suit_name, color in suits:
        for r in ranks:
            fname = f"{suit_name}_{r}.png"
            make_card(r, suit, os.path.join(OUT_DIR, fname), color=color)
