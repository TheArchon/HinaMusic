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

try:
    from config import YOUTUBE_IMG_URL
except Exception:
    YOUTUBE_IMG_URL = "https://i.imgur.com/placeholder.jpg"


# ==========================================================
# SETTINGS
# ==========================================================

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

CANVAS_W = 1280
CANVAS_H = 720

THUMB_W = 680
THUMB_H = 430

THUMB_X = 45
THUMB_Y = 145

RIGHT_X = 760


# ==========================================================
# FONT
# ==========================================================

def get_font(size, bold=False):
    if bold:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    else:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]

    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

    return ImageFont.load_default()


# ==========================================================
# SAFE FILENAME
# ==========================================================

def safe_filename(text):
    text = str(text or "thumbnail")
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    text = re.sub(r"\s+", "_", text)
    return text[:100]


# ==========================================================
# DOWNLOAD IMAGE
# ==========================================================

async def download_image(url, path):
    try:
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(
                url,
                allow_redirects=True
            ) as response:

                if response.status != 200:
                    return False

                data = await response.read()

                async with aiofiles.open(
                    path,
                    "wb"
                ) as file:

                    await file.write(data)

        return True

    except Exception as e:
        print(f"Thumbnail Download Error: {e}")
        return False


# ==========================================================
# YOUTUBE SEARCH
# ==========================================================

async def get_youtube_data(query):
    try:
        search = VideosSearch(
            str(query),
            limit=1
        )

        result = await search.next()

        if not result:
            return None

        videos = result.get("result", [])

        if not videos:
            return None

        video = videos[0]

        title = video.get(
            "title",
            str(query)
        )

        thumbnails = video.get(
            "thumbnails",
            []
        )

        thumbnail = None

        if thumbnails:
            thumbnail = thumbnails[-1].get("url")

        duration = video.get(
            "duration",
            "0:00"
        ) or "0:00"

        channel = video.get(
            "channel",
            {}
        )

        if isinstance(channel, dict):
            channel_name = channel.get(
                "name",
                "YouTube"
            )
        else:
            channel_name = "YouTube"

        return {
            "title": title,
            "thumbnail": thumbnail,
            "duration": duration,
            "channel": channel_name,
        }

    except Exception as e:
        print(f"YouTube Search Error: {e}")
        return None


# ==========================================================
# CROP IMAGE
# ==========================================================

def crop_to_ratio(image, width, height):
    image = image.convert("RGB")

    target_ratio = width / height
    current_ratio = image.width / image.height

    if current_ratio > target_ratio:

        new_width = int(
            image.height * target_ratio
        )

        left = (
            image.width - new_width
        ) // 2

        image = image.crop(
            (
                left,
                0,
                left + new_width,
                image.height,
            )
        )

    else:

        new_height = int(
            image.width / target_ratio
        )

        top = (
            image.height - new_height
        ) // 2

        image = image.crop(
            (
                0,
                top,
                image.width,
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
    image = image.convert("RGBA")

    mask = Image.new(
        "L",
        image.size,
        0
    )

    mask_draw = ImageDraw.Draw(mask)

    mask_draw.rounded_rectangle(
        (
            0,
            0,
            image.width,
            image.height,
        ),
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
# TRUNCATE TEXT
# ==========================================================

def truncate_text(
    draw,
    text,
    font,
    max_width
):
    text = str(text or "")

    try:
        width = draw.textbbox(
            (0, 0),
            text,
            font=font
        )[2]

        if width <= max_width:
            return text

        while len(text) > 3:

            test = text[:-1] + "..."

            width = draw.textbbox(
                (0, 0),
                test,
                font=font
            )[2]

            if width <= max_width:
                return test

            text = text[:-1]

    except Exception:
        return text[:40]

    return text[:40]


# ==========================================================
# CREATE PLAYER
# ==========================================================

async def create_thumbnail(
    query,
    thumbnail_url=None,
    title=None,
    duration=None,
    channel=None,
):
    try:

        # --------------------------------------------------
        # If information is not supplied, search YouTube
        # --------------------------------------------------

        if not thumbnail_url or not title:

            data = await get_youtube_data(
                query
            )

            if data:

                title = (
                    title
                    or data["title"]
                )

                thumbnail_url = (
                    thumbnail_url
                    or data["thumbnail"]
                )

                duration = (
                    duration
                    or data["duration"]
                )

                channel = (
                    channel
                    or data["channel"]
                )

        title = title or str(query)

        duration = (
            duration
            or "0:00"
        )

        channel = (
            channel
            or "YouTube"
        )

        thumbnail_url = (
            thumbnail_url
            or YOUTUBE_IMG_URL
        )

        # --------------------------------------------------
        # File names
        # --------------------------------------------------

        filename = safe_filename(
            title
        )

        source_path = os.path.join(
            CACHE_DIR,
            f"{filename}_source.jpg"
        )

        output_path = os.path.join(
            CACHE_DIR,
            f"{filename}_player.jpg"
        )

        # --------------------------------------------------
        # Download
        # --------------------------------------------------

        if not os.path.exists(
            source_path
        ):

            success = await download_image(
                thumbnail_url,
                source_path
            )

            if not success:
                return None

        # --------------------------------------------------
        # Open
        # --------------------------------------------------

        try:
            source = Image.open(
                source_path
            ).convert("RGB")

        except Exception as e:
            print(
                f"Thumbnail Open Error: {e}"
            )
            return None

        # --------------------------------------------------
        # Canvas
        # --------------------------------------------------

        canvas = Image.new(
            "RGB",
            (
                CANVAS_W,
                CANVAS_H
            ),
            (7, 7, 7)
        )

        # --------------------------------------------------
        # Blurred Background
        # --------------------------------------------------

        background = crop_to_ratio(
            source,
            CANVAS_W,
            CANVAS_H
        )

        background = background.filter(
            ImageFilter.GaussianBlur(18)
        )

        background = ImageEnhance.Brightness(
            background
        ).enhance(0.18)

        canvas.paste(
            background,
            (0, 0)
        )

        # --------------------------------------------------
        # Dark Overlay
        # --------------------------------------------------

        overlay = Image.new(
            "RGBA",
            (
                CANVAS_W,
                CANVAS_H
            ),
            (0, 0, 0, 200)
        )

        canvas = Image.alpha_composite(
            canvas.convert("RGBA"),
            overlay
        )

        draw = ImageDraw.Draw(
            canvas
        )

        # --------------------------------------------------
        # Main Panel
        # --------------------------------------------------

        draw.rounded_rectangle(
            (
                18,
                18,
                CANVAS_W - 18,
                CANVAS_H - 18,
            ),
            radius=40,
            fill=(8, 8, 8, 245),
            outline=(38, 38, 38, 255),
            width=2,
        )

        # --------------------------------------------------
        # Thumbnail
        # --------------------------------------------------

        thumb = crop_to_ratio(
            source,
            THUMB_W,
            THUMB_H
        )

        thumb = rounded_image(
            thumb,
            radius=30
        )

        canvas.alpha_composite(
            thumb,
            (
                THUMB_X,
                THUMB_Y
            )
        )

        draw = ImageDraw.Draw(
            canvas
        )

        # --------------------------------------------------
        # TITLE
        # --------------------------------------------------

        title_font = get_font(
            35,
            bold=True
        )

        small_font = get_font(
            23
        )

        title_text = truncate_text(
            draw,
            title,
            title_font,
            470
        )

        draw.text(
            (
                RIGHT_X,
                90
            ),
            title_text,
            font=title_font,
            fill=(245, 245, 245)
        )

        # --------------------------------------------------
        # CHANNEL
        # --------------------------------------------------

        channel_text = truncate_text(
            draw,
            channel,
            small_font,
            400
        )

        draw.text(
            (
                RIGHT_X,
                140
            ),
            channel_text,
            font=small_font,
            fill=(170, 170, 170)
        )

        # --------------------------------------------------
        # CAST BUTTON
        # --------------------------------------------------

        cx = 1175
        cy = 95
        radius = 30

        draw.ellipse(
            (
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius
            ),
            fill=(65, 65, 65)
        )

        cast_font = get_font(
            25,
            bold=True
        )

        draw.text(
            (
                cx - 9,
                cy - 16
            ),
            "×",
            font=cast_font,
            fill=(240, 240, 240)
        )

        # --------------------------------------------------
        # PROGRESS BAR
        # --------------------------------------------------

        bar_x1 = RIGHT_X
        bar_x2 = 1235
        bar_y = 270

        draw.rounded_rectangle(
            (
                bar_x1,
                bar_y,
                bar_x2,
                bar_y + 12
            ),
            radius=8,
            fill=(65, 65, 68)
        )

        progress_x = 1040

        draw.rounded_rectangle(
            (
                bar_x1,
                bar_y,
                progress_x,
                bar_y + 12
            ),
            radius=8,
            fill=(245, 245, 245)
        )

        draw.ellipse(
            (
                progress_x - 15,
                bar_y - 8,
                progress_x + 15,
                bar_y + 22
            ),
            fill=(255, 255, 255)
        )

        # --------------------------------------------------
        # TIME
        # --------------------------------------------------

        time_font = get_font(
            19
        )

        draw.text(
            (
                RIGHT_X,
                305
            ),
            "0:00",
            font=time_font,
            fill=(220, 220, 220)
        )

        duration_box = draw.textbbox(
            (
                0,
                0
            ),
            str(duration),
            font=time_font
        )

        duration_width = (
            duration_box[2]
            - duration_box[0]
        )

        draw.text(
            (
                bar_x2 - duration_width,
                305
            ),
            str(duration),
            font=time_font,
            fill=(220, 220, 220)
        )

        # --------------------------------------------------
        # PLAYBACK BUTTONS
        # --------------------------------------------------

        center_y = 500

        # Previous
        draw.polygon(
            [
                (820, center_y),
                (865, center_y - 42),
                (865, center_y + 42)
            ],
            fill=(255, 255, 255)
        )

        draw.polygon(
            [
                (850, center_y),
                (895, center_y - 42),
                (895, center_y + 42)
            ],
            fill=(255, 255, 255)
        )

        # Pause
        draw.rounded_rectangle(
            (
                960,
                center_y - 48,
                982,
                center_y + 48
            ),
            radius=5,
            fill=(255, 255, 255)
        )

        draw.rounded_rectangle(
            (
                1000,
                center_y - 48,
                1022,
                center_y + 48
            ),
            radius=5,
            fill=(255, 255, 255)
        )

        # Next
        draw.polygon(
            [
                (1120, center_y - 42),
                (1165, center_y),
                (1120, center_y + 42)
            ],
            fill=(255, 255, 255)
        )

        draw.polygon(
            [
                (1150, center_y - 42),
                (1195, center_y),
                (1150, center_y + 42)
            ],
            fill=(255, 255, 255)
        )

        # --------------------------------------------------
        # VOLUME BAR
        # --------------------------------------------------

        volume_y = 615

        draw.rounded_rectangle(
            (
                820,
                volume_y,
                1240,
                volume_y + 12
            ),
            radius=8,
            fill=(70, 70, 72)
        )

        draw.rounded_rectangle(
            (
                820,
                volume_y,
                1040,
                volume_y + 12
            ),
            radius=8,
            fill=(235, 235, 235)
        )

        # Speaker
        draw.polygon(
            [
                (775, volume_y + 6),
                (795, volume_y - 12),
                (805, volume_y - 12),
                (805, volume_y + 24),
                (795, volume_y + 24)
            ],
            fill=(235, 235, 235)
        )

        draw.rectangle(
            (
                805,
                volume_y - 8,
                812,
                volume_y + 20
            ),
            fill=(235, 235, 235)
        )

        # --------------------------------------------------
        # IPHONE BUTTON
        # --------------------------------------------------

        button_x1 = 970
        button_y1 = 665
        button_x2 = 1115
        button_y2 = 710

        draw.rounded_rectangle(
            (
                button_x1,
                button_y1,
                button_x2,
                button_y2
            ),
            radius=25,
            fill=(60, 60, 60)
        )

        iphone_font = get_font(
            20,
            bold=True
        )

        iphone = "iPhone"

        box = draw.textbbox(
            (0, 0),
            iphone,
            font=iphone_font
        )

        text_width = (
            box[2] - box[0]
        )

        text_height = (
            box[3] - box[1]
        )

        draw.text(
            (
                button_x1
                + (
                    button_x2
                    - button_x1
                    - text_width
                ) / 2,

                button_y1
                + (
                    button_y2
                    - button_y1
                    - text_height
                ) / 2
                - 3,
            ),
            iphone,
            font=iphone_font,
            fill=(245, 245, 245)
        )

        # --------------------------------------------------
        # SAVE
        # --------------------------------------------------

        canvas = canvas.convert(
            "RGB"
        )

        canvas.save(
            output_path,
            "JPEG",
            quality=95,
            optimize=True
        )

        return output_path

    except Exception as e:
        print(
            f"Thumbnail Creation Error: {e}"
        )
        return None


# ==========================================================
# get_thumbnail
# ==========================================================

async def get_thumbnail(query):
    try:
        return await create_thumbnail(
            query
        )
    except Exception as e:
        print(
            f"get_thumbnail Error: {e}"
        )
        return None


# ==========================================================
# get_thumb
# ==========================================================
# IMPORTANT:
# Existing AloneMusic files use get_thumb().
# This function keeps compatibility.
# ==========================================================

async def get_thumb(
    query,
    thumbnail_url=None,
    title=None,
    duration=None,
    channel=None,
    *args,
    **kwargs
):
    try:

        # Some old code may pass URL as second argument.
        if thumbnail_url:

            return await create_thumbnail(
                query=query,
                thumbnail_url=thumbnail_url,
                title=title,
                duration=duration,
                channel=channel,
            )

        return await create_thumbnail(
            query=query,
            title=title,
            duration=duration,
            channel=channel,
        )

    except Exception as e:
        print(
            f"get_thumb Error: {e}"
        )
        return None
