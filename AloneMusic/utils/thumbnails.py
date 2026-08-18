import os
import re
import time
import aiofiles
import aiohttp

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageOps
from py_yt import VideosSearch
from config import YOUTUBE_IMG_URL


# ==========================================================
# CONFIG
# ==========================================================

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

WIDTH, HEIGHT = 1280, 720

FONT_TITLE = "AloneMusic/assets/f (1).ttf"
FONT_META = "AloneMusic/assets/cfont (1).ttf"
FONT_TIME = "AloneMusic/assets/cfont (1).ttf"

DIRECT_THUMB = "https://i.ytimg.com/vi/{videoid}/hqdefault.jpg"


# ==========================================================
# HELPERS
# ==========================================================

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def fit_cover(img, size):
    return ImageOps.fit(
        img.convert("RGB"),
        size,
        method=Image.Resampling.LANCZOS
    ).convert("RGBA")


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size[0] - 1, size[1] - 1),
        radius=radius,
        fill=255
    )
    return mask


def trim_text(text, font, max_width):
    text = str(text or "Song").strip()
    try:
        if font.getlength(text) <= max_width:
            return text
        for i in range(len(text), 0, -1):
            part = text[:i] + "…"
            if font.getlength(part) <= max_width:
                return part
    except Exception:
        pass
    return text[:45] + "…"


def parse_duration_seconds(duration):
    if not duration:
        return 0

    value = str(duration).strip()
    if value.lower() == "live":
        return 0

    try:
        parts = [int(x) for x in value.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except Exception:
        pass

    return 0


def format_time(seconds):
    seconds = max(0, int(seconds))
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


async def fetch_bytes(url, timeout=12):
    try:
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            ) as response:
                if response.status == 200:
                    return await response.read()
    except Exception:
        pass
    return None


async def get_metadata(videoid):
    try:
        results = VideosSearch(
            f"https://www.youtube.com/watch?v={videoid}",
            limit=1
        )
        data = await results.next()
        item = data.get("result", [{}])[0]

        returned_id = item.get("id") or item.get("videoId")
        if returned_id and returned_id != videoid:
            return None

        title = item.get("title") or "Song"
        thumbnails = item.get("thumbnails") or []

        thumbnail_url = ""
        if thumbnails:
            thumbnail_url = thumbnails[0].get("url", "").split("?")[0]

        duration = item.get("duration") or "0:00"
        views = item.get("viewCount", {}).get("short", "Unknown")
        channel = item.get("channel", {}).get("name", "YouTube")

        return title, thumbnail_url, duration, views, channel

    except Exception:
        return None


# ==========================================================
# MAIN THUMBNAIL
# ==========================================================

async def get_thumb(
    videoid: str,
    progress_percent: int = 0,
    use_cache: bool = False,
    user_name: str = "Badnam"
) -> str:

    progress_percent = max(0, min(100, int(progress_percent)))

    cache_path = os.path.join(
        CACHE_DIR,
        f"music_{videoid}_{progress_percent}.png"
    )

    if use_cache and os.path.exists(cache_path):
        return cache_path

    # ------------------------------------------------------
    # GET SONG INFO
    # ------------------------------------------------------

    meta = await get_metadata(videoid)

    if meta:
        title, thumbnail_url, duration, views, channel = meta
    else:
        title = "Song"
        thumbnail_url = DIRECT_THUMB.format(videoid=videoid)
        duration = "0:00"
        views = "Unknown"
        channel = "YouTube"

    # Exact video thumbnail fallback
    urls = [
        thumbnail_url,
        DIRECT_THUMB.format(videoid=videoid),
    ]

    image_data = None

    for url in urls:
        if url:
            image_data = await fetch_bytes(url)
            if image_data:
                break

    if not image_data:
        return YOUTUBE_IMG_URL

    # ------------------------------------------------------
    # LOAD YOUTUBE IMAGE
    # ------------------------------------------------------

    try:
        from io import BytesIO

        original = Image.open(BytesIO(image_data)).convert("RGB")
    except Exception:
        return YOUTUBE_IMG_URL

    # ======================================================
    # BACKGROUND
    # ======================================================

    # Make the YouTube image a dark cinematic background.
    bg = fit_cover(original, (WIDTH, HEIGHT))
    bg = ImageEnhance.Contrast(bg).enhance(1.08)
    bg = ImageEnhance.Brightness(bg).enhance(0.48)
    bg = bg.filter(ImageFilter.GaussianBlur(18))

    canvas = bg

    # Black transparent overlay
    dark = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 125)
    )
    canvas = Image.alpha_composite(canvas, dark)

    draw = ImageDraw.Draw(canvas)

    # ======================================================
    # WHITE PLAYER CARD — SAME STYLE AS REFERENCE
    # ======================================================

    card_x1, card_y1 = 145, 105
    card_x2, card_y2 = 1135, 555
    radius = 30

    # Glow
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)

    gd.rounded_rectangle(
        (card_x1, card_y1, card_x2, card_y2),
        radius=radius,
        fill=(255, 255, 255, 210)
    )

    glow = glow.filter(ImageFilter.GaussianBlur(25))
    canvas = Image.alpha_composite(canvas, glow)

    # Card
    card_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card_layer)

    cd.rounded_rectangle(
        (card_x1, card_y1, card_x2, card_y2),
        radius=radius,
        fill=(248, 248, 248, 248)
    )

    canvas = Image.alpha_composite(canvas, card_layer)
    draw = ImageDraw.Draw(canvas)

    # ======================================================
    # ALBUM / YOUTUBE THUMBNAIL
    # ======================================================

    album_x, album_y = 170, 130
    album_size = 310

    album = fit_cover(original, (album_size, album_size))
    album_mask = rounded_mask(
        (album_size, album_size),
        18
    )

    # Album shadow
    shadow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)

    sd.rounded_rectangle(
        (
            album_x + 4,
            album_y + 8,
            album_x + album_size + 4,
            album_y + album_size + 8
        ),
        radius=20,
        fill=(0, 0, 0, 75)
    )

    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    canvas = Image.alpha_composite(canvas, shadow)

    canvas.paste(
        album,
        (album_x, album_y),
        album_mask
    )

    draw = ImageDraw.Draw(canvas)

    # ======================================================
    # FONTS
    # ======================================================

    title_font = load_font(FONT_TITLE, 39)
    artist_font = load_font(FONT_META, 22)
    meta_font = load_font(FONT_META, 18)
    time_font = load_font(FONT_TIME, 16)

    text_x = 520

    # ======================================================
    # TITLE
    # ======================================================

    title_text = trim_text(
        title,
        title_font,
        490
    )

    draw.text(
        (text_x, 164),
        title_text,
        font=title_font,
        fill="black"
    )

    # ======================================================
    # VERIFIED ICON + CHANNEL
    # ======================================================

    vx, vy = text_x, 270

    draw.ellipse(
        (vx, vy, vx + 20, vy + 20),
        fill="black"
    )

    draw.line(
        (vx + 5, vy + 10, vx + 9, vy + 14),
        fill="white",
        width=2
    )

    draw.line(
        (vx + 9, vy + 14, vx + 16, vy + 6),
        fill="white",
        width=2
    )

    draw.text(
        (text_x + 30, 266),
        str(channel),
        font=artist_font,
        fill="black"
    )

    # Album/source line
    draw.text(
        (text_x + 30, 305),
        "YouTube Music",
        font=meta_font,
        fill=(55, 55, 55)
    )

    # ======================================================
    # HEART + MENU
    # ======================================================

    draw.text(
        (995, 165),
        "♥",
        font=load_font(FONT_TITLE, 42),
        fill="black"
    )

    draw.text(
        (1060, 167),
        "⋮",
        font=load_font(FONT_TITLE, 34),
        fill="black"
    )

    # ======================================================
    # PROGRESS BAR
    # ======================================================

    bar_x1 = 520
    bar_x2 = 1095
    bar_y = 365

    draw.line(
        (bar_x1, bar_y, bar_x2, bar_y),
        fill=(185, 185, 185),
        width=4
    )

    progress_x = int(
        bar_x1 +
        (bar_x2 - bar_x1) *
        (progress_percent / 100)
    )

    if progress_x > bar_x1:
        draw.line(
            (bar_x1, bar_y, progress_x, bar_y),
            fill=(20, 20, 20),
            width=5
        )

    draw.ellipse(
        (
            progress_x - 6,
            bar_y - 6,
            progress_x + 6,
            bar_y + 6
        ),
        fill="black"
    )

    total_seconds = parse_duration_seconds(duration)
    current_seconds = int(
        total_seconds *
        (progress_percent / 100)
    )

    current_time = format_time(current_seconds)

    draw.text(
        (bar_x1, 390),
        current_time,
        font=time_font,
        fill=(60, 60, 60)
    )

    draw.text(
        (bar_x2 - 40, 390),
        str(duration),
        font=time_font,
        fill=(60, 60, 60)
    )

    # ======================================================
    # CONTROLS
    # ======================================================

    # Shuffle
    sx, sy = 570, 465

    draw.line(
        (sx - 18, sy - 10, sx - 6, sy - 10,
         sx + 8, sy + 10, sx + 18, sy + 10),
        fill="black",
        width=4
    )

    draw.line(
        (sx - 18, sy + 10, sx - 7, sy + 10,
         sx + 7, sy - 10, sx + 18, sy - 10),
        fill="black",
        width=4
    )

    # Previous
    px, py = 680, 465

    draw.polygon(
        [
            (px + 12, py - 17),
            (px - 6, py),
            (px + 12, py + 17)
        ],
        fill="black"
    )

    draw.rectangle(
        (px - 12, py - 19, px - 7, py + 19),
        fill="black"
    )

    # Big pause button
    cx, cy = 805, 465

    draw.ellipse(
        (cx - 39, cy - 39, cx + 39, cy + 39),
        fill="black"
    )

    draw.rounded_rectangle(
        (cx - 12, cy - 22, cx - 3, cy + 22),
        radius=3,
        fill="white"
    )

    draw.rounded_rectangle(
        (cx + 4, cy - 22, cx + 13, cy + 22),
        radius=3,
        fill="white"
    )

    # Next
    nx, ny = 930, 465

    draw.polygon(
        [
            (nx - 12, ny - 17),
            (nx + 6, ny),
            (nx - 12, ny + 17)
        ],
        fill="black"
    )

    draw.rectangle(
        (nx + 7, ny - 19, nx + 12, ny + 19),
        fill="black"
    )

    # Repeat
    rx, ry = 1030, 465

    draw.arc(
        (rx - 18, ry - 15, rx + 18, ry + 15),
        210,
        40,
        fill="black",
        width=4
    )

    draw.polygon(
        [
            (rx - 18, ry - 15),
            (rx - 18, ry - 2),
            (rx - 7, ry - 10)
        ],
        fill="black"
    )

    draw.polygon(
        [
            (rx + 18, ry + 15),
            (rx + 18, ry + 2),
            (rx + 7, ry + 10)
        ],
        fill="black"
    )

    # ======================================================
    # SAVE
    # ======================================================
    canvas = canvas.convert("RGB")
    canvas.save(
        cache_path,
        "PNG",
        optimize=True
    )

    print(
        f"✓ Thumbnail generated: {cache_path} | "
        f"Progress: {progress_percent}%"
    )

    return cache_path
    
