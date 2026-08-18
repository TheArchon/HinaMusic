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


# =========================
# SETTINGS
# =========================

WIDTH = 1536
HEIGHT = 864

os.makedirs("cache", exist_ok=True)


# =========================
# FONT
# =========================

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()


# =========================
# TEXT WIDTH
# =========================

def text_width(draw, text, font):
    try:
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0]
    except Exception:
        return draw.textlength(text, font=font)


# =========================
# TITLE WRAPPER
# =========================

def wrap_title(draw, text, font, max_width):

    words = text.split()
    lines = []
    current = ""

    for word in words:

        test = (
            word
            if not current
            else current + " " + word
        )

        if text_width(
            draw,
            test,
            font
        ) <= max_width:

            current = test

        else:

            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    # Only 2 lines
    if len(lines) > 2:

        lines = lines[:2]

        last = lines[1]

        while (
            text_width(
                draw,
                last + "...",
                font
            ) > max_width
            and len(last) > 4
        ):
            last = last[:-1].rstrip()

        lines[1] = last + "..."

    return lines


# =========================
# ROUNDED IMAGE
# =========================

def make_rounded_image(
    image,
    width,
    height,
    radius=22
):

    image = ImageOps.fit(
        image.convert("RGB"),
        (width, height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5)
    )

    image = image.convert("RGBA")

    mask = Image.new(
        "L",
        (width, height),
        0
    )

    mask_draw = ImageDraw.Draw(mask)

    mask_draw.rounded_rectangle(
        [
            (0, 0),
            (width, height)
        ],
        radius=radius,
        fill=255
    )

    image.putalpha(mask)

    return image


# =========================
# GET THUMB
# =========================

async def get_thumb(
    videoid,
    user_name=None,
    next_title=None
):

    output_file = (
        f"cache/music_{videoid}.png"
    )

    # Return cached image
    if os.path.isfile(output_file):
        return output_file

    raw_file = (
        f"cache/raw_{videoid}.jpg"
    )

    try:

        # =========================
        # YOUTUBE SEARCH
        # =========================

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
                "Video not found"
            )

        result = response["result"][0]

        # =========================
        # TITLE
        # =========================

        try:
            title = result["title"]
        except Exception:
            title = "Unknown Song"

        title = re.sub(
            r"\s+",
            " ",
            title
        ).strip()

        # =========================
        # DURATION
        # =========================

        try:
            duration = result["duration"]
        except Exception:
            duration = "0:00"

        # =========================
        # THUMBNAIL
        # =========================

        try:
            thumbnail = (
                result["thumbnails"][0]["url"]
                .split("?")[0]
            )
        except Exception:
            thumbnail = YOUTUBE_IMG_URL

        # =========================
        # DOWNLOAD IMAGE
        # =========================

        async with aiohttp.ClientSession() as session:

            async with session.get(
                thumbnail
            ) as resp:

                if resp.status != 200:
                    raise Exception(
                        "Thumbnail download failed"
                    )

                data = await resp.read()

                async with aiofiles.open(
                    raw_file,
                    "wb"
                ) as f:

                    await f.write(data)

        youtube = Image.open(
            raw_file
        ).convert("RGB")

        # =========================
        # BACKGROUND
        # =========================

        background = ImageOps.fit(
            youtube,
            (WIDTH, HEIGHT),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5)
        )

        background = background.filter(
            ImageFilter.GaussianBlur(65)
        )

        background = ImageEnhance.Brightness(
            background
        ).enhance(0.25)

        background = background.convert(
            "RGBA"
        )

        # Dark overlay
        overlay = Image.new(
            "RGBA",
            (WIDTH, HEIGHT),
            (0, 0, 0, 90)
        )

        background = Image.alpha_composite(
            background,
            overlay
        )

        draw = ImageDraw.Draw(
            background
        )

        # =========================
        # WHITE CARD
        # =========================

        card_x = 135
        card_y = 68

        card_w = 1270
        card_h = 755

        # Shadow
        shadow = Image.new(
            "RGBA",
            (WIDTH, HEIGHT),
            (0, 0, 0, 0)
        )

        shadow_draw = ImageDraw.Draw(
            shadow
        )

        shadow_draw.rounded_rectangle(
            [
                (card_x + 10, card_y + 15),
                (
                    card_x + card_w + 10,
                    card_y + card_h + 15
                )
            ],
            radius=38,
            fill=(0, 0, 0, 150)
        )

        shadow = shadow.filter(
            ImageFilter.GaussianBlur(25)
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
                (card_x, card_y),
                (
                    card_x + card_w,
                    card_y + card_h
                )
            ],
            radius=38,
            fill=(248, 248, 250)
        )

        # =========================
        # SONG PICTURE
        # =========================

        # Smaller picture
        picture_x = card_x + 38
        picture_y = card_y + 30

        picture_w = card_w - 76
        picture_h = 500

        song_image = make_rounded_image(
            youtube,
            picture_w,
            picture_h,
            radius=24
        )

        background.paste(
            song_image,
            (
                picture_x,
                picture_y
            ),
            song_image
        )

        draw = ImageDraw.Draw(
            background
        )

        # =========================
        # FONTS
        # =========================

        title_font = get_font(
            "AloneMusic/assets/font.ttf",
            38
        )

        time_font = get_font(
            "AloneMusic/assets/font3.ttf",
            24
        )

        watermark_font = get_font(
            "AloneMusic/assets/font2.ttf",
            26
        )

        # =========================
        # TITLE
        # =========================

        title_area_width = (
            card_w - 100
        )

        lines = wrap_title(
            draw,
            title,
            title_font,
            title_area_width
        )

        title_y = (
            picture_y
            + picture_h
            + 25
        )

        # First line
        if len(lines) >= 1:

            w = text_width(
                draw,
                lines[0],
                title_font
            )

            draw.text(
                (
                    card_x
                    + (card_w - w) / 2,
                    title_y
                ),
                lines[0],
                fill=(10, 10, 10),
                font=title_font
            )

        # Second line
        if len(lines) >= 2:

            w = text_width(
                draw,
                lines[1],
                title_font
            )

            draw.text(
                (
                    card_x
                    + (card_w - w) / 2,
                    title_y + 48
                ),
                lines[1],
                fill=(10, 10, 10),
                font=title_font
            )

        # =========================
        # PROGRESS BAR
        # =========================

        bar_x = card_x + 85
        bar_y = (
            card_y
            + card_h
            - 80
        )

        bar_w = card_w - 170
        bar_h = 7

        # Gray background
        draw.rounded_rectangle(
            [
                (bar_x, bar_y),
                (
                    bar_x + bar_w,
                    bar_y + bar_h
                )
            ],
            radius=4,
            fill=(145, 145, 145)
        )

        # Progress
        progress = 0.30

        progress_width = (
            bar_w * progress
        )

        draw.rounded_rectangle(
            [
                (bar_x, bar_y),
                (
                    bar_x + progress_width,
                    bar_y + bar_h
                )
            ],
            radius=4,
            fill=(20, 165, 50)
        )

        # Progress dot
        dot_x = (
            bar_x
            + progress_width
        )

        dot_y = (
            bar_y
            + bar_h / 2
        )

        draw.ellipse(
            [
                (
                    dot_x - 11,
                    dot_y - 11
                ),
                (
                    dot_x + 11,
                    dot_y + 11
                )
            ],
            fill=(20, 165, 50)
        )

        # =========================
        # TIME
        # =========================

        time_y = (
            bar_y + 22
        )

        draw.text(
            (
                bar_x,
                time_y
            ),
            "00:00",
            fill=(15, 15, 15),
            font=time_font
        )

        duration_w = text_width(
            draw,
            duration,
            time_font
        )

        draw.text(
            (
                bar_x
                + bar_w
                - duration_w,
                time_y
            ),
            duration,
            fill=(15, 15, 15),
            font=time_font
        )

        # =========================
        # WATERMARK
        # =========================

        watermark = "Meera Music"

        wm_w = text_width(
            draw,
            watermark,
            watermark_font
        )

        draw.text(
            (
                WIDTH
                - wm_w
                - 40,
                25
            ),
            watermark,
            fill=(255, 255, 255),
            font=watermark_font
        )

        # =========================
        # SAVE
        # =========================

        background = background.convert(
            "RGB"
        )

        background.save(
            output_file,
            "PNG",
            optimize=True
        )

        # Delete temporary file
        try:
            os.remove(raw_file)
        except Exception:
            pass

        return output_file

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


# =========================
# GET YOUTUBE THUMBNAIL URL
# =========================

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
