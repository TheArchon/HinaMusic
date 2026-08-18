# AloneMusic/utils/thumbnails.py

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
    YOUTUBE_IMG_URL = ""


# ==========================================================
# SETTINGS
# ==========================================================

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

CANVAS_W = 1280
CANVAS_H = 720

# Picture THODA CHOTA
THUMB_W = 620
THUMB_H = 400

# Picture position
THUMB_X = 55
THUMB_Y = 160

# Right side
RIGHT_X = 720


# ==========================================================
# FONT
# ==========================================================

def get_font(size, bold=False):

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
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

    return ImageFont.load_default()


# ==========================================================
# SAFE FILE NAME
# ==========================================================

def safe_filename(text):

    text = str(text or "thumbnail")

    text = re.sub(
        r'[\\/*?:"<>|]',
        "",
        text
    )

    text = re.sub(
        r"\s+",
        "_",
        text
    )

    return text[:100]


# ==========================================================
# DOWNLOAD IMAGE
# ==========================================================

async def download_image(url, path):

    if not url:
        return False

    try:

        timeout = aiohttp.ClientTimeout(
            total=30
        )

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

        print(
            f"Thumbnail Download Error: {e}"
        )

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

        videos = result.get(
            "result",
            []
        )

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

            thumbnail = thumbnails[-1].get(
                "url"
            )

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

        print(
            f"YouTube Search Error: {e}"
        )

        return None


# ==========================================================
# CROP IMAGE
# ==========================================================

def crop_to_ratio(
    image,
    width,
    height
):

    image = image.convert(
        "RGB"
    )

    target_ratio = (
        width / height
    )

    current_ratio = (
        image.width / image.height
    )

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
                image.height
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
                top + new_height
            )
        )

    return image.resize(
        (
            width,
            height
        ),
        Image.Resampling.LANCZOS
    )


# ==========================================================
# ROUNDED IMAGE
# ==========================================================

def rounded_image(
    image,
    radius=28
):

    image = image.convert(
        "RGBA"
    )

    mask = Image.new(
        "L",
        image.size,
        0
    )

    mask_draw = ImageDraw.Draw(
        mask
    )

    mask_draw.rounded_rectangle(
        (
            0,
            0,
            image.width - 1,
            image.height - 1
        ),
        radius=radius,
        fill=255
    )

    result = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0)
    )

    result.paste(
        image,
        (0, 0),
        mask
    )

    return result


# ==========================================================
# TEXT TRUNCATE
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

        return text[:35]

    return text[:35]


# ==========================================================
# CREATE THUMBNAIL
# ==========================================================

async def create_thumbnail(
    query,
    thumbnail_url=None,
    title=None,
    duration=None,
    channel=None,
    *args,
    **kwargs
):

    try:

        # --------------------------------------------------
        # GET YOUTUBE DATA
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

        title = (
            title
            or str(query)
        )

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
        # FILE
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
        # DOWNLOAD
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
        # OPEN IMAGE
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

        # ==================================================
        # CANVAS
        # ==================================================

        canvas = Image.new(
            "RGB",
            (
                CANVAS_W,
                CANVAS_H
            ),
            (7, 7, 7)
        )

        # ==================================================
        # BLURRED BACKGROUND
        # ==================================================

        background = crop_to_ratio(
            source,
            CANVAS_W,
            CANVAS_H
        )

        background = background.filter(
            ImageFilter.GaussianBlur(
                18
            )
        )

        background = ImageEnhance.Brightness(
            background
        ).enhance(
            0.15
        )

        canvas.paste(
            background,
            (0, 0)
        )

        # ==================================================
        # DARK OVERLAY
        # ==================================================

        overlay = Image.new(
            "RGBA",
            (
                CANVAS_W,
                CANVAS_H
            ),
            (0, 0, 0, 205)
        )

        canvas = Image.alpha_composite(
            canvas.convert("RGBA"),
            overlay
        )

        draw = ImageDraw.Draw(
            canvas
        )

        # ==================================================
        # MAIN PLAYER PANEL
        # ==================================================

        draw.rounded_rectangle(
            (
                18,
                18,
                CANVAS_W - 18,
                CANVAS_H - 18
            ),
            radius=40,
            fill=(8, 8, 8, 245),
            outline=(40, 40, 40, 255),
            width=2
        )

        # ==================================================
        # SMALLER PICTURE
        # ==================================================

        thumbnail = crop_to_ratio(
            source,
            THUMB_W,
            THUMB_H
        )

        thumbnail = rounded_image(
            thumbnail,
            radius=28
        )

        canvas.alpha_composite(
            thumbnail,
            (
                THUMB_X,
                THUMB_Y
            )
        )

        draw = ImageDraw.Draw(
            canvas
        )

        # ==================================================
        # TITLE
        # ==================================================

        title_font = get_font(
            32,
            bold=True
        )

        small_font = get_font(
            21
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

        # ==================================================
        # CHANNEL
        # ==================================================

        channel_text = truncate_text(
            draw,
            channel,
            small_font,
            400
        )

        draw.text(
            (
                RIGHT_X,
                138
            ),
            channel_text,
            font=small_font,
            fill=(165, 165, 165)
        )

        # ==================================================
        # THREE DOTS
        # ==================================================

        cx = 1180
        cy = 95

        draw.ellipse(
            (
                cx - 35,
                cy - 35,
                cx + 35,
                cy + 35
            ),
            fill=(55, 55, 55)
        )

        for dx in (-12, 0, 12):

            draw.ellipse(
                (
                    cx + dx - 4,
                    cy - 4,
                    cx + dx + 4,
                    cy + 4
                ),
                fill=(245, 245, 245)
            )

        # ==================================================
        # PROGRESS BAR
        # ==================================================

        bar_x1 = RIGHT_X
        bar_x2 = 1235
        bar_y = 270

        draw.rounded_rectangle(
            (
                bar_x1,
                bar_y,
                bar_x2,
                bar_y + 10
            ),
            radius=7,
            fill=(60, 60, 63)
        )

        progress_x = 1040

        draw.rounded_rectangle(
            (
                bar_x1,
                bar_y,
                progress_x,
                bar_y + 10
            ),
            radius=7,
            fill=(245, 245, 245)
        )

        draw.ellipse(
            (
                progress_x - 14,
                bar_y - 7,
                progress_x + 14,
                bar_y + 21
            ),
            fill=(255, 255, 255)
        )

        # ==================================================
        # TIME
        # ==================================================

        time_font = get_font(
            18
        )

        draw.text(
            (
                RIGHT_X,
                300
            ),
            "0:00",
            font=time_font,
            fill=(210, 210, 210)
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
                300
            ),
            str(duration),
            font=time_font,
            fill=(210, 210, 210)
        )

        # ==================================================
        # PREVIOUS
        # ==================================================

        center_y = 490

        draw.polygon(
            [
                (830, center_y),
                (870, center_y - 38),
                (870, center_y + 38)
            ],
            fill=(255, 255, 255)
        )

        draw.polygon(
            [
                (855, center_y),
                (895, center_y - 38),
                (895, center_y + 38)
            ],
            fill=(255, 255, 255)
        )

        # ==================================================
        # PAUSE
        # ==================================================

        draw.rounded_rectangle(
            (
                975,
                center_y - 45,
                997,
                center_y + 45
            ),
            radius=5,
            fill=(255, 255, 255)
        )

        draw.rounded_rectangle(
            (
                1015,
                center_y - 45,
                1037,
                center_y + 45
            ),
            radius=5,
            fill=(255, 255, 255)
        )

        # ==================================================
        # NEXT
        # ==================================================

        draw.polygon(
            [
                (1130, center_y - 38),
                (1170, center_y),
                (1130, center_y + 38)
            ],
            fill=(255, 255, 255)
        )

        draw.polygon(
            [
                (1155, center_y - 38),
                (1195, center_y),
                (1155, center_y + 38)
            ],
            fill=(255, 255, 255)
        )

        # ==================================================
        # VOLUME
        # ==================================================

        volume_y = 610

        draw.rounded_rectangle(
            (
                800,
                volume_y,
                1235,
                volume_y + 10
            ),
            radius=7,
            fill=(65, 65, 68)
        )

        draw.rounded_rectangle(
            (
                800,
                volume_y,
                1015,
                volume_y + 10
            ),
            radius=7,
            fill=(235, 235, 235)
        )

        # ==================================================
        # IPHONE BUTTON
        # ==================================================

        button_x1 = 970
        button_y1 = 655
        button_x2 = 1120
        button_y2 = 700

        draw.rounded_rectangle(
            (
                button_x1,
                button_y1,
                button_x2,
                button_y2
            ),
            radius=24,
            fill=(55, 55, 55)
        )

        iphone_font = get_font(
            19,
            bold=True
        )

        iphone = "iPhone"

        box = draw.textbbox(
            (0, 0),
            iphone,
            font=iphone_font
        )

        tw = box[2] - box[0]
        th = box[3] - box[1]

        draw.text(
            (
                button_x1
                + (
                    button_x2
                    - button_x1
                    - tw
                ) / 2,

                button_y1
                + (
                    button_y2
                    - button_y1
                    - th
                ) / 2
                - 3
            ),
            iphone,
            font=iphone_font,
            fill=(245, 245, 245)
        )

        # ==================================================
        # SAVE
        # ==================================================

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
# get_thumb
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

        return await create_thumbnail(
            query=query,
            thumbnail_url=thumbnail_url,
            title=title,
            duration=duration,
            channel=channel
        )

    except Exception as e:

        print(
            f"get_thumb Error: {e}"
        )

        return None


# ==========================================================
# get_thumbnail
# ==========================================================

async def get_thumbnail(
    query,
    *args,
    **kwargs
):

    return await get_thumb(
        query,
        *args,
        **kwargs
        )
