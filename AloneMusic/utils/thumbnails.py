#
# Meera Music Thumbnail Generator
# Fixed YouTube thumbnail / white player card
#

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
    ImageOps,
)

from py_yt import VideosSearch

from config import YOUTUBE_IMG_URL


# ============================================================
# SETTINGS
# ============================================================

WIDTH = 1536
HEIGHT = 864

CACHE_DIR = "cache"

os.makedirs(CACHE_DIR, exist_ok=True)


# ============================================================
# FONT HELPER
# ============================================================

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()


# ============================================================
# TEXT WIDTH
# ============================================================

def get_text_width(draw, text, font):
    try:
        box = draw.textbbox(
            (0, 0),
            text,
            font=font
        )
        return box[2] - box[0]
    except Exception:
        return draw.textlength(
            text,
            font=font
        )


# ============================================================
# TEXT WRAPPER
# ============================================================

def wrap_text(
    draw,
    text,
    font,
    max_width,
    max_lines=2
):

    words = text.split()

    lines = []
    current = ""

    for word in words:

        test = (
            word
            if not current
            else current + " " + word
        )

        if (
            get_text_width(
                draw,
                test,
                font
            ) <= max_width
        ):
            current = test

        else:

            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    # Keep only requested number of lines
    if len(lines) > max_lines:

        lines = lines[:max_lines]

        last = lines[-1]

        while (
            get_text_width(
                draw,
                last + "...",
                font
            ) > max_width
            and len(last) > 5
        ):
            last = last[:-1].rstrip()

        lines[-1] = last + "..."

    return lines


# ============================================================
# ROUNDED THUMBNAIL
# ============================================================

def make_thumbnail(
    image,
    box_width,
    box_height,
    radius=24
):

    # --------------------------------------------------------
    # IMPORTANT:
    # ImageOps.contain = picture crop nahi hogi
    # --------------------------------------------------------

    source = image.convert("RGB")

    contained = ImageOps.contain(
        source,
        (
            box_width,
            box_height
        ),
        method=Image.Resampling.LANCZOS
    )

    # White background inside thumbnail area
    canvas = Image.new(
        "RGB",
        (
            box_width,
            box_height
        ),
        (245, 245, 245)
    )

    x = (
        box_width
        - contained.width
    ) // 2

    y = (
        box_height
        - contained.height
    ) // 2

    canvas.paste(
        contained,
        (x, y)
    )

    canvas = canvas.convert("RGBA")

    # Rounded mask
    mask = Image.new(
        "L",
        (
            box_width,
            box_height
        ),
        0
    )

    mask_draw = ImageDraw.Draw(mask)

    mask_draw.rounded_rectangle(
        [
            (0, 0),
            (
                box_width - 1,
                box_height - 1
            )
        ],
        radius=radius,
        fill=255
    )

    canvas.putalpha(mask)

    return canvas


# ============================================================
# GET THUMBNAIL
# ============================================================

async def get_thumb(
    videoid,
    user_name=None,
    next_title=None
):

    output_file = (
        f"{CACHE_DIR}/{videoid}.png"
    )

    raw_file = (
        f"{CACHE_DIR}/thumb_{videoid}.jpg"
    )

    # --------------------------------------------------------
    # CACHE
    # --------------------------------------------------------

    if os.path.isfile(output_file):

        return output_file

    try:

        # ====================================================
        # SEARCH VIDEO
        # ====================================================

        url = (
            f"https://www.youtube.com/watch?v={videoid}"
        )

        results = VideosSearch(
            url,
            limit=1
        )

        response = await results.next()

        if (
            not response
            or "result" not in response
            or not response["result"]
        ):
            raise Exception(
                "No video result found"
            )

        result = response["result"][0]

        # ====================================================
        # TITLE
        # ====================================================

        try:
            title = result["title"]
        except Exception:
            title = "Unknown Song"

        title = re.sub(
            r"\s+",
            " ",
            title
        ).strip()

        # ====================================================
        # DURATION
        # ====================================================

        try:
            duration = result["duration"]
        except Exception:
            duration = "0:00"

        # ====================================================
        # THUMBNAIL URL
        # ====================================================

        try:

            thumbnail_url = (
                result["thumbnails"][0]["url"]
                .split("?")[0]
            )

        except Exception:

            thumbnail_url = YOUTUBE_IMG_URL

        # ====================================================
        # DOWNLOAD THUMBNAIL
        # ====================================================

        async with aiohttp.ClientSession() as session:

            async with session.get(
                thumbnail_url
            ) as response:

                if response.status != 200:
                    raise Exception(
                        "Thumbnail download failed"
                    )

                image_data = await response.read()

        async with aiofiles.open(
            raw_file,
            "wb"
        ) as file:

            await file.write(
                image_data
            )

        # ====================================================
        # OPEN IMAGE
        # ====================================================

        youtube = Image.open(
            raw_file
        ).convert("RGB")

        # ====================================================
        # BACKGROUND
        # ====================================================

        background = ImageOps.fit(
            youtube,
            (
                WIDTH,
                HEIGHT
            ),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5)
        )

        background = background.filter(
            ImageFilter.GaussianBlur(65)
        )

        background = ImageEnhance.Brightness(
            background
        ).enhance(0.22)

        background = background.convert(
            "RGBA"
        )

        # Dark overlay
        dark_layer = Image.new(
            "RGBA",
            (
                WIDTH,
                HEIGHT
            ),
            (0, 0, 0, 100)
        )

        background = Image.alpha_composite(
            background,
            dark_layer
        )

        draw = ImageDraw.Draw(
            background
        )

        # ====================================================
        # WHITE CARD
        # ====================================================

        card_x = 88
        card_y = 85

        card_w = 1360
        card_h = 790

        # Shadow
        shadow = Image.new(
            "RGBA",
            (
                WIDTH,
                HEIGHT
            ),
            (0, 0, 0, 0)
        )

        shadow_draw = ImageDraw.Draw(
            shadow
        )

        shadow_draw.rounded_rectangle(
            [
                (
                    card_x + 8,
                    card_y + 12
                ),
                (
                    card_x
                    + card_w
                    + 8,
                    card_y
                    + card_h
                    + 12
                )
            ],
            radius=38,
            fill=(0, 0, 0, 150)
        )

        shadow = shadow.filter(
            ImageFilter.GaussianBlur(22)
        )

        background = Image.alpha_composite(
            background,
            shadow
        )

        draw = ImageDraw.Draw(
            background
        )

        # White card
        draw.rounded_rectangle(
            [
                (
                    card_x,
                    card_y
                ),
                (
                    card_x + card_w,
                    card_y + card_h
                )
            ],
            radius=38,
            fill=(248, 248, 250)
        )

        # ====================================================
        # SONG PICTURE
        # ====================================================

        # Picture ko card ke andar proper size diya gaya hai
        picture_x = card_x + 45
        picture_y = card_y + 30

        picture_w = card_w - 90
        picture_h = 505

        song_picture = make_thumbnail(
            youtube,
            picture_w,
            picture_h,
            radius=25
        )

        background.paste(
            song_picture,
            (
                picture_x,
                picture_y
            ),
            song_picture
        )

        draw = ImageDraw.Draw(
            background
        )

        # ====================================================
        # FONTS
        # ====================================================

        title_font = get_font(
            "AloneMusic/assets/font.ttf",
            38
        )

        time_font = get_font(
            "AloneMusic/assets/font3.ttf",
            25
        )

        watermark_font = get_font(
            "AloneMusic/assets/font2.ttf",
            27
        )

        # ====================================================
        # SONG TITLE
        # ====================================================

        title_width = (
            card_w - 150
        )

        title_lines = wrap_text(
            draw,
            title,
            title_font,
            title_width,
            max_lines=2
        )

        title_y = (
            picture_y
            + picture_h
            + 28
        )

        line_gap = 48

        for index, line in enumerate(
            title_lines
        ):

            line_width = get_text_width(
                draw,
                line,
                title_font
            )

            line_x = (
                card_x
                + (
                    card_w
                    - line_width
                ) / 2
            )

            draw.text(
                (
                    line_x,
                    title_y
                    + index * line_gap
                ),
                line,
                fill=(10, 10, 10),
                font=title_font
            )

        # ====================================================
        # PROGRESS BAR
        # ====================================================

        bar_x = card_x + 90

        bar_y = (
            card_y
            + card_h
            - 78
        )

        bar_w = card_w - 180

        bar_h = 7

        # Background
        draw.rounded_rectangle(
            [
                (
                    bar_x,
                    bar_y
                ),
                (
                    bar_x + bar_w,
                    bar_y + bar_h
                )
            ],
            radius=5,
            fill=(150, 150, 150)
        )

        # Progress
        progress = 0.30

        progress_w = (
            bar_w
            * progress
        )

        draw.rounded_rectangle(
            [
                (
                    bar_x,
                    bar_y
                ),
                (
                    bar_x + progress_w,
                    bar_y + bar_h
                )
            ],
            radius=5,
            fill=(20, 170, 55)
        )

        # Slider dot
        dot_x = (
            bar_x
            + progress_w
        )

        dot_y = (
            bar_y
            + bar_h / 2
        )

        draw.ellipse(
            [
                (
                    dot_x - 12,
                    dot_y - 12
                ),
                (
                    dot_x + 12,
                    dot_y + 12
                )
            ],
            fill=(20, 170, 55)
        )

        # ====================================================
        # TIME
        # ====================================================

        time_y = (
            bar_y + 24
        )

        draw.text(
            (
                bar_x,
                time_y
            ),
            "00:00",
            fill=(20, 20, 20),
            font=time_font
        )

        duration_width = get_text_width(
            draw,
            duration,
            time_font
        )

        draw.text(
            (
                bar_x
                + bar_w
                - duration_width,
                time_y
            ),
            duration,
            fill=(20, 20, 20),
            font=time_font
        )

        # ====================================================
        # MEERA MUSIC
        # ====================================================

        watermark = "Meera Music"

        watermark_width = get_text_width(
            draw,
            watermark,
            watermark_font
        )

        draw.text(
            (
                WIDTH
                - watermark_width
                - 42,
                25
            ),
            watermark,
            fill=(255, 255, 255),
            font=watermark_font
        )

        # ====================================================
        # SAVE
        # ====================================================

        background = background.convert(
            "RGB"
        )

        background.save(
            output_file,
            "PNG",
            optimize=True
        )

        # ====================================================
        # DELETE TEMP FILE
        # ====================================================

        try:
            if os.path.exists(raw_file):
                os.remove(raw_file)
        except Exception:
            pass

        return output_file

    # ========================================================
    # ERROR
    # ========================================================

    except Exception as e:

        print(
            f"Thumbnail Error: {e}"
        )

        try:
            if os.path.exists(raw_file):
                os.remove(raw_file)
        except Exception:
            pass

        return YOUTUBE_IMG_URL


# ============================================================
# GET ORIGINAL YOUTUBE THUMBNAIL
# ============================================================

async def get_qthumb(vidid):

    try:

        url = (
            f"https://www.youtube.com/watch?v={vidid}"
        )

        results = VideosSearch(
            url,
            limit=1
        )

        response = await results.next()

        if (
            response
            and "result" in response
            and response["result"]
        ):

            return (
                response["result"][0]
                ["thumbnails"][0]["url"]
                .split("?")[0]
            )

    except Exception as e:

        print(
            f"get_qthumb Error: {e}"
        )

    return YOUTUBE_IMG_URL
