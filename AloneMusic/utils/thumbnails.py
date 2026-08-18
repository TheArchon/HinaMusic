# thumbnails.py

import os
import re
import aiohttp
import aiofiles

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
# SETTINGS
# ==========================================================

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

CANVAS_W = 1280
CANVAS_H = 720

# Thumbnail size
THUMB_W = 680
THUMB_H = 430

THUMB_X = 45
THUMB_Y = 145

# Right side
RIGHT_X = 760


# ==========================================================
# FONT
# ==========================================================

def get_font(size, bold=False):
    paths = []

    if bold:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    else:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]

    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


# ==========================================================
# SAFE FILE NAME
# ==========================================================

def safe_filename(text):
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    text = text.replace(" ", "_")
    return text[:80]


# ==========================================================
# DOWNLOAD THUMBNAIL
# ==========================================================

async def download_image(url, path):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return False

                data = await response.read()

                async with aiofiles.open(path, "wb") as f:
                    await f.write(data)

        return True

    except Exception:
        return False


# ==========================================================
# GET YOUTUBE DATA
# ==========================================================

async def get_youtube_data(query):
    try:
        search = VideosSearch(query, limit=1)

        result = await search.next()

        if not result:
            return None

        result = result.get("result", [])

        if not result:
            return None

        video = result[0]

        title = video.get("title", "Unknown Song")

        thumbnail = video.get("thumbnails", [])

        if thumbnail:
            thumb_url = thumbnail[-1].get("url")
        else:
            thumb_url = None

        duration = video.get("duration") or "0:00"

        channel = video.get("channel", {})

        channel_name = (
            channel.get("name")
            if isinstance(channel, dict)
            else "YouTube"
        )

        return {
            "title": title,
            "thumbnail": thumb_url,
            "duration": duration,
            "channel": channel_name or "YouTube",
        }

    except Exception:
        return None


# ==========================================================
# CROP IMAGE WITHOUT DISTORTION
# ==========================================================

def crop_to_ratio(image, width, height):
    image = image.convert("RGB")

    target_ratio = width / height
    image_ratio = image.width / image.height

    if image_ratio > target_ratio:
        # Too wide
        new_height = image.height
        new_width = int(new_height * target_ratio)

        left = (image.width - new_width) // 2

        image = image.crop(
            (
                left,
                0,
                left + new_width,
                new_height,
            )
        )

    else:
        # Too tall
        new_width = image.width
        new_height = int(new_width / target_ratio)

        top = (image.height - new_height) // 2

        image = image.crop(
            (
                0,
                top,
                new_width,
                top + new_height,
            )
        )

    return image.resize(
        (width, height),
        Image.Resampling.LANCZOS,
    )


# ==========================================================
# ROUNDED IMAGE
# ==========================================================

def rounded_image(image, radius=30):
    mask = Image.new(
        "L",
        image.size,
        0,
    )

    draw = ImageDraw.Draw(mask)

    draw.rounded_rectangle(
        (0, 0, image.width, image.height),
        radius=radius,
        fill=255,
    )

    result = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0),
    )

    result.paste(
        image,
        (0, 0),
        mask,
    )

    return result


# ==========================================================
# TEXT TRUNCATE
# ==========================================================

def truncate_text(draw, text, font, max_width):
    if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
        return text

    while len(text) > 3:
        text = text[:-1]

        test = text + "..."

        if draw.textbbox(
            (0, 0),
            test,
            font=font,
        )[2] <= max_width:
            return test

    return "..."


# ==========================================================
# CREATE MUSIC PLAYER
# ==========================================================

async def create_thumbnail(query):
    """
    Create music player thumbnail.

    Returns:
        str: generated image path
    """

    data = await get_youtube_data(query)

    if not data:
        return None

    title = data["title"]
    channel = data["channel"]
    duration = data["duration"]
    thumb_url = data["thumbnail"]

    if not thumb_url:
        thumb_url = YOUTUBE_IMG_URL

    filename = safe_filename(title)

    thumb_path = os.path.join(
        CACHE_DIR,
        f"{filename}_source.jpg",
    )

    output_path = os.path.join(
        CACHE_DIR,
        f"{filename}_player.jpg",
    )

    # ------------------------------------------------------
    # Download image
    # ------------------------------------------------------

    if not os.path.exists(thumb_path):

        downloaded = await download_image(
            thumb_url,
            thumb_path,
        )

        if not downloaded:
            return None

    # ------------------------------------------------------
    # Open source image
    # ------------------------------------------------------

    try:
        source = Image.open(thumb_path).convert("RGB")
    except Exception:
        return None

    # ------------------------------------------------------
    # Canvas
    # ------------------------------------------------------

    canvas = Image.new(
        "RGB",
        (CANVAS_W, CANVAS_H),
        (8, 8, 8),
    )

    # ------------------------------------------------------
    # Background blur
    # ------------------------------------------------------

    bg = crop_to_ratio(
        source,
        CANVAS_W,
        CANVAS_H,
    )

    bg = bg.filter(
        ImageFilter.GaussianBlur(18)
    )

    bg = ImageEnhance.Brightness(
        bg
    ).enhance(0.20)

    canvas.paste(
        bg,
        (0, 0),
    )

    # ------------------------------------------------------
    # Dark overlay
    # ------------------------------------------------------

    overlay = Image.new(
        "RGBA",
        (CANVAS_W, CANVAS_H),
        (0, 0, 0, 185),
    )

    canvas = Image.alpha_composite(
        canvas.convert("RGBA"),
        overlay,
    )

    # ------------------------------------------------------
    # Main black panel
    # ------------------------------------------------------

    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle(
        (
            18,
            18,
            CANVAS_W - 18,
            CANVAS_H - 18,
        ),
        radius=40,
        fill=(10, 10, 10, 245),
        outline=(45, 45, 45, 255),
        width=2,
    )

    # ------------------------------------------------------
    # Thumbnail
    # ------------------------------------------------------

    thumbnail = crop_to_ratio(
        source,
        THUMB_W,
        THUMB_H,
    )

    thumbnail = rounded_image(
        thumbnail,
        radius=30,
    )

    canvas.alpha_composite(
        thumbnail,
        (
            THUMB_X,
            THUMB_Y,
        ),
    )

    draw = ImageDraw.Draw(canvas)

    # ------------------------------------------------------
    # Title
    # ------------------------------------------------------

    title_font = get_font(
        36,
        bold=True,
    )

    small_font = get_font(
        23,
        bold=False,
    )

    title_text = truncate_text(
        draw,
        title,
        title_font,
        470,
    )

    draw.text(
        (
            RIGHT_X,
            90,
        ),
        title_text,
        font=title_font,
        fill=(245, 245, 245),
    )

    # ------------------------------------------------------
    # Channel
    # ------------------------------------------------------

    draw.text(
        (
            RIGHT_X,
            140,
        ),
        channel,
        font=small_font,
        fill=(170, 170, 170),
    )

    # ------------------------------------------------------
    # Cast / close circle
    # ------------------------------------------------------

    circle_x = 1175
    circle_y = 95
    circle_r = 30

    draw.ellipse(
        (
            circle_x - circle_r,
            circle_y - circle_r,
            circle_x + circle_r,
            circle_y + circle_r,
        ),
        fill=(65, 65, 65),
    )

    cast_font = get_font(
        25,
        bold=True,
    )

    draw.text(
        (
            circle_x - 10,
            circle_y - 15,
        ),
        "×",
        font=cast_font,
        fill=(235, 235, 235),
    )

    # ------------------------------------------------------
    # Progress bar
    # ------------------------------------------------------

    bar_x1 = RIGHT_X
    bar_x2 = 1235
    bar_y = 270

    draw.rounded_rectangle(
        (
            bar_x1,
            bar_y,
            bar_x2,
            bar_y + 12,
        ),
        radius=8,
        fill=(65, 65, 68),
    )

    progress_x = 1040

    draw.rounded_rectangle(
        (
            bar_x1,
            bar_y,
            progress_x,
            bar_y + 12,
        ),
        radius=8,
        fill=(245, 245, 245),
    )

    draw.ellipse(
        (
            progress_x - 15,
            bar_y - 8,
            progress_x + 15,
            bar_y + 22,
        ),
        fill=(255, 255, 255),
    )

    # ------------------------------------------------------
    # Time
    # ------------------------------------------------------

    time_font = get_font(
        19,
        bold=False,
    )

    draw.text(
        (
            RIGHT_X,
            305,
        ),
        "0:00",
        font=time_font,
        fill=(220, 220, 220),
    )

    duration_width = draw.textbbox(
        (0, 0),
        duration,
        font=time_font,
    )[2]

    draw.text(
        (
            bar_x2 - duration_width,
            305,
        ),
        duration,
        font=time_font,
        fill=(220, 220, 220),
    )

    # ------------------------------------------------------
    # Playback controls
    # ------------------------------------------------------

    center_y = 500

    # Previous
    draw.polygon(
        [
            (820, center_y),
            (865, center_y - 42),
            (865, center_y + 42),
        ],
        fill=(255, 255, 255),
    )

    draw.polygon(
        [
            (850, center_y),
            (895, center_y - 42),
            (895, center_y + 42),
        ],
        fill=(255, 255, 255),
    )

    # Pause
    draw.rounded_rectangle(
        (
            960,
            center_y - 48,
            982,
            center_y + 48,
        ),
        radius=5,
        fill=(255, 255, 255),
    )

    draw.rounded_rectangle(
        (
            1000,
            center_y - 48,
            1022,
            center_y + 48,
        ),
        radius=5,
        fill=(255, 255, 255),
    )

    # Next
    draw.polygon(
        [
            (1120, center_y - 42),
            (1165, center_y),
            (1120, center_y + 42),
        ],
        fill=(255, 255, 255),
    )

    draw.polygon(
        [
            (1150, center_y - 42),
            (1195, center_y),
            (1150, center_y + 42),
        ],
        fill=(255, 255, 255),
    )

    # ------------------------------------------------------
    # Volume
    # ------------------------------------------------------

    volume_y = 615

    draw.rounded_rectangle(
        (
            820,
            volume_y,
            1240,
            volume_y + 12,
        ),
        radius=8,
        fill=(70, 70, 72),
    )

    draw.rounded_rectangle(
        (
            820,
            volume_y,
            1040,
            volume_y + 12,
        ),
        radius=8,
        fill=(235, 235, 235),
    )

    # Volume speaker
    draw.polygon(
        [
            (775, volume_y + 6),
            (795, volume_y - 12),
            (805, volume_y - 12),
            (805, volume_y + 24),
            (795, volume_y + 24),
        ],
        fill=(235, 235, 235),
    )

    draw.rectangle(
        (
            805,
            volume_y - 8,
            812,
            volume_y + 20,
        ),
        fill=(235, 235, 235),
    )

    # ------------------------------------------------------
    # iPhone button
    # ------------------------------------------------------

    button_x1 = 970
    button_y1 = 665
    button_x2 = 1115
    button_y2 = 710

    draw.rounded_rectangle(
        (
            button_x1,
            button_y1,
            button_x2,
            button_y2,
        ),
        radius=25,
        fill=(60, 60, 60),
    )

    iphone_font = get_font(
        20,
        bold=True,
    )

    iphone_text = "iPhone"

    bbox = draw.textbbox(
        (0, 0),
        iphone_text,
        font=iphone_font,
    )

    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    draw.text(
        (
            button_x1 + (button_x2 - button_x1 - text_w) / 2,
            button_y1 + (button_y2 - button_y1 - text_h) / 2 - 3,
        ),
        iphone_text,
        font=iphone_font,
        fill=(245, 245, 245),
    )

    # ------------------------------------------------------
    # Save
    # ------------------------------------------------------

    canvas = canvas.convert("RGB")

    canvas.save(
        output_path,
        "JPEG",
        quality=95,
        optimize=True,
    )

    return output_path


# ==========================================================
# SIMPLE FUNCTION FOR BOT
# ==========================================================

async def get_thumbnail(query):
    try:
        return await create_thumbnail(query)
    except Exception as e:
        print(f"Thumbnail Error: {e}")
        return None
