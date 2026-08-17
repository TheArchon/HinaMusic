import os
import re
import aiofiles
import aiohttp

from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
)

from py_yt import VideosSearch
from config import YOUTUBE_IMG_URL


# ==========================================================
# CONSTANTS
# ==========================================================

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

CANVAS_W, CANVAS_H = 1280, 720


# ==========================================================
# BIG THUMBNAIL
# ==========================================================

THUMB_W = 1180
THUMB_H = 545

THUMB_X = (CANVAS_W - THUMB_W) // 2
THUMB_Y = 18


# ==========================================================
# TEXT
# ==========================================================

TITLE_X = 50
TITLE_Y = 578

META_X = 50
META_Y = 622

MAX_TITLE_WIDTH = 850


# ==========================================================
# PROGRESS BAR
# ==========================================================

BAR_X = 50
BAR_Y = 675

BAR_TOTAL_LEN = 1180
BAR_RED_LEN = 590


# ==========================================================
# TRIM TITLE
# ==========================================================

def trim_to_width(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_w: int
) -> str:

    ellipsis = "…"

    if font.getlength(text) <= max_w:
        return text

    for i in range(len(text) - 1, 0, -1):

        new_text = text[:i] + ellipsis

        if font.getlength(new_text) <= max_w:
            return new_text

    return ellipsis


# ==========================================================
# GET THUMBNAIL
# ==========================================================

async def get_thumb(videoid, user_id=None):

    cache_path = os.path.join(
        CACHE_DIR,
        f"{videoid}_v6.png"
    )

    if os.path.exists(cache_path):
        return cache_path

    # ======================================================
    # YOUTUBE DATA
    # ======================================================

    results = VideosSearch(
        f"https://www.youtube.com/watch?v={videoid}",
        limit=1
    )

    try:

        results_data = await results.next()

        result_items = results_data.get(
            "result",
            []
        )

        if not result_items:
            raise ValueError("No results found.")

        data = result_items[0]

        title = re.sub(
            r"\W+",
            " ",
            data.get(
                "title",
                "Unsupported Title"
            )
        ).strip()

        thumbnail = data.get(
            "thumbnails",
            [{}]
        )[0].get(
            "url",
            YOUTUBE_IMG_URL
        )

        duration = data.get("duration")

        views = data.get(
            "viewCount",
            {}
        ).get(
            "short",
            "Unknown Views"
        )

    except Exception as e:

        print(f"YouTube data error: {e}")

        title = "Unsupported Title"
        thumbnail = YOUTUBE_IMG_URL
        duration = None
        views = "Unknown Views"

    # ======================================================
    # DURATION
    # ======================================================

    is_live = (
        not duration
        or str(duration).strip().lower()
        in {
            "",
            "live",
            "live now"
        }
    )

    duration_text = (
        "Live"
        if is_live
        else duration or "Unknown"
    )

    # ======================================================
    # DOWNLOAD THUMBNAIL
    # ======================================================

    thumb_path = os.path.join(
        CACHE_DIR,
        f"thumb_{videoid}.png"
    )

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(thumbnail) as resp:

                if resp.status != 200:
                    return YOUTUBE_IMG_URL

                image_data = await resp.read()

                async with aiofiles.open(
                    thumb_path,
                    "wb"
                ) as f:

                    await f.write(image_data)

    except Exception as e:

        print(f"Thumbnail download error: {e}")
        return YOUTUBE_IMG_URL

    # ======================================================
    # OPEN IMAGE
    # ======================================================

    try:

        original = (
            Image.open(thumb_path)
            .convert("RGB")
        )

    except Exception as e:

        print(f"Image open error: {e}")
        return YOUTUBE_IMG_URL

    # ======================================================
    # CREATE 1280x720 CANVAS
    # ======================================================

    base = Image.new(
        "RGB",
        (CANVAS_W, CANVAS_H)
    )

    # ======================================================
    # BLURRED BACKGROUND
    # ======================================================

    bg = ImageEnhance.Brightness(
        original.resize(
            (CANVAS_W, CANVAS_H),
            Image.Resampling.LANCZOS
        ).filter(
            ImageFilter.GaussianBlur(18)
        )
    ).enhance(0.65)

    base.paste(
        bg,
        (0, 0)
    )

    # ======================================================
    # BIG THUMBNAIL
    #
    # BLACK PANEL REMOVED
    # ======================================================

    thumb = ImageOpsFit(
        original,
        (THUMB_W, THUMB_H)
    )

    # Rounded corners only
    tmask = Image.new(
        "L",
        (THUMB_W, THUMB_H),
        0
    )

    mask_draw = ImageDraw.Draw(tmask)

    mask_draw.rounded_rectangle(
        (
            0,
            0,
            THUMB_W,
            THUMB_H
        ),
        radius=24,
        fill=255
    )

    base.paste(
        thumb,
        (
            THUMB_X,
            THUMB_Y
        ),
        tmask
    )

    # ======================================================
    # DRAW
    # ======================================================

    draw = ImageDraw.Draw(base)

    # ======================================================
    # FONTS
    # ======================================================

    try:

        title_font = ImageFont.truetype(
            "AloneMusic/assets/font2.ttf",
            31
        )

        regular_font = ImageFont.truetype(
            "AloneMusic/assets/font.ttf",
            19
        )

    except OSError:

        title_font = ImageFont.load_default()
        regular_font = ImageFont.load_default()

    # ======================================================
    # TITLE
    # ======================================================

    title_text = trim_to_width(
        title,
        title_font,
        MAX_TITLE_WIDTH
    )

    draw.text(
        (
            TITLE_X,
            TITLE_Y
        ),
        title_text,
        fill="white",
        font=title_font
    )

    # ======================================================
    # META
    # ======================================================

    draw.text(
        (
            META_X,
            META_Y
        ),
        f"YouTube | {views}",
        fill="white",
        font=regular_font
    )

    # ======================================================
    # PROGRESS BAR
    # ======================================================

    # Gray background
    draw.rounded_rectangle(
        (
            BAR_X,
            BAR_Y,
            BAR_X + BAR_TOTAL_LEN,
            BAR_Y + 6
        ),
        radius=4,
        fill=(180, 180, 180)
    )

    # Red progress
    draw.rounded_rectangle(
        (
            BAR_X,
            BAR_Y,
            BAR_X + BAR_RED_LEN,
            BAR_Y + 6
        ),
        radius=4,
        fill=(255, 0, 0)
    )

    # ======================================================
    # RED PROGRESS CIRCLE
    # ======================================================

    circle_x = BAR_X + BAR_RED_LEN
    circle_y = BAR_Y + 3

    draw.ellipse(
        (
            circle_x - 10,
            circle_y - 10,
            circle_x + 10,
            circle_y + 10
        ),
        fill=(255, 0, 0)
    )

    # ======================================================
    # TIME
    # ======================================================

    time_y = BAR_Y + 12

    draw.text(
        (
            BAR_X,
            time_y
        ),
        "00:00",
        fill="white",
        font=regular_font
    )

    # ======================================================
    # END TIME
    # ======================================================

    end_text = (
        "Live"
        if is_live
        else duration_text
    )

    end_width = draw.textlength(
        end_text,
        font=regular_font
    )

    draw.text(
        (
            BAR_X + BAR_TOTAL_LEN - end_width,
            time_y
        ),
        end_text,
        fill="white",
        font=regular_font
    )

    # ======================================================
    # CLEANUP
    # ======================================================

    try:

        os.remove(thumb_path)

    except OSError:

        pass

    # ======================================================
    # SAVE
    # ======================================================

    base.save(
        cache_path,
        "PNG"
    )

    return cache_path


# ==========================================================
# IMAGE FIT FUNCTION
# ==========================================================

def ImageOpsFit(image, size):

    target_w, target_h = size

    src_w, src_h = image.size

    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:

        # Crop left/right
        new_h = src_h
        new_w = int(src_h * target_ratio)

        left = (src_w - new_w) // 2

        image = image.crop(
            (
                left,
                0,
                left + new_w,
                src_h
            )
        )

    else:

        # Crop top/bottom
        new_w = src_w
        new_h = int(src_w / target_ratio)

        top = (src_h - new_h) // 2

        image = image.crop(
            (
                0,
                top,
                src_w,
                top + new_h
            )
        )

    return image.resize(
        size,
        Image.Resampling.LANCZOS
        )
