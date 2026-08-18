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

os.makedirs("cache", exist_ok=True)

WIDTH = 1536
HEIGHT = 864


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
# TEXT SIZE
# =========================

def get_text_width(draw, text, font):
    try:
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0]
    except Exception:
        return draw.textlength(text, font=font)


# =========================
# TEXT WRAP
# =========================

def fit_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = word if not current else current + " " + word

        if get_text_width(draw, test, font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    # Maximum 2 lines
    if len(lines) > 2:
        lines = lines[:2]

        last = lines[-1]

        while (
            get_text_width(
                draw,
                last + "...",
                font
            ) > max_width
            and len(last) > 3
        ):
            last = last[:-1].rstrip()

        lines[-1] = last + "..."

    return "\n".join(lines)


# =========================
# ROUNDED IMAGE
# =========================

def rounded_image(image, size, radius):
    image = ImageOps.fit(
        image.convert("RGB"),
        size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )

    image = image.convert("RGBA")

    mask = Image.new(
        "L",
        size,
        0
    )

    mask_draw = ImageDraw.Draw(mask)

    mask_draw.rounded_rectangle(
        [
            (0, 0),
            (size[0], size[1])
        ],
        radius=radius,
        fill=255
    )

    image.putalpha(mask)

    return image


# =========================
# MAIN THUMBNAIL
# =========================

async def get_thumb(
    videoid,
    user_name=None,
    next_title=None
):

    # New cache name so old images don't load
    file_name = f"cache/fix_{videoid}.png"

    if os.path.isfile(file_name):
        return file_name

    try:

        # =========================
        # YOUTUBE DATA
        # =========================

        url = (
            f"https://www.youtube.com/watch?v={videoid}"
        )

        results = VideosSearch(
            url,
            limit=1
        )

        res = await results.next()

        if (
            not res
            or "result" not in res
            or not res["result"]
        ):
            raise Exception(
                "No YouTube result found"
            )

        result = res["result"][0]

        # Title
        try:
            title = result["title"]
        except Exception:
            title = "Unknown Title"

        title = re.sub(
            r"\s+",
            " ",
            title
        ).strip()

        # Duration
        try:
            duration = result["duration"]
        except Exception:
            duration = "Unknown"

        # Channel
        try:
            channel = result["channel"]["name"]
        except Exception:
            channel = "Unknown Artist"

        # Thumbnail URL
        try:
            thumbnail = (
                result["thumbnails"][0]["url"]
                .split("?")[0]
            )
        except Exception:
            thumbnail = YOUTUBE_IMG_URL

        # =========================
        # DOWNLOAD THUMBNAIL
        # =========================

        raw_file = (
            f"cache/raw_{videoid}.jpg"
        )

        async with aiohttp.ClientSession() as session:

            async with session.get(
                thumbnail
            ) as response:

                if response.status != 200:
                    raise Exception(
                        "Thumbnail download failed"
                    )

                data = await response.read()

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
            ImageFilter.GaussianBlur(55)
        )

        background = ImageEnhance.Brightness(
            background
        ).enhance(0.42)

        background = ImageEnhance.Color(
            background
        ).enhance(1.15)

        background = background.convert(
            "RGBA"
        )

        # Dark transparent layer
        dark = Image.new(
            "RGBA",
            (WIDTH, HEIGHT),
            (0, 0, 0, 80)
        )

        background = Image.alpha_composite(
            background,
            dark
        )

        draw = ImageDraw.Draw(
            background
        )

        # =========================
        # MAIN WHITE CARD
        # =========================

        card_x = 165
        card_y = 85

        card_w = 1205
        card_h = 695

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
            radius=35,
            fill=(0, 0, 0, 120)
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

        # Main card
        draw.rounded_rectangle(
            [
                (card_x, card_y),
                (
                    card_x + card_w,
                    card_y + card_h
                )
            ],
            radius=35,
            fill=(245, 245, 248, 245)
        )

        # =========================
        # LARGE ALBUM ART
        # =========================

        image_x = card_x + 25
        image_y = card_y + 25

        image_w = card_w - 50
        image_h = 480

        album = rounded_image(
            youtube,
            (
                image_w,
                image_h
            ),
            25
        )

        background.paste(
            album,
            (
                image_x,
                image_y
            ),
            album
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

        artist_font = get_font(
            "AloneMusic/assets/font2.ttf",
            27
        )

        time_font = get_font(
            "AloneMusic/assets/font3.ttf",
            24
        )

        watermark_font = get_font(
            "AloneMusic/assets/font2.ttf",
            25
        )

        # =========================
        # TITLE
        # =========================

        title_y = (
            image_y
            + image_h
            + 10
        )

        max_title_width = (
            card_w - 80
        )

        display_title = fit_text(
            draw,
            title,
            title_font,
            max_title_width
        )

        draw.multiline_text(
            (
                card_x + card_w // 2,
                title_y
            ),
            display_title,
            fill=(10, 10, 10),
            font=title_font,
            anchor="ma",
            align="center",
            spacing=2
        )

        # =========================
        # ARTIST / INFO
        # =========================

        info_y = (
            title_y
            + 70
        )

        info_text = (
            f"YouTube | {channel}"
        )

        info_width = get_text_width(
            draw,
            info_text,
            artist_font
        )

        draw.text(
            (
                card_x
                + (card_w - info_width) // 2,
                info_y
            ),
            info_text,
            fill=(20, 20, 20),
            font=artist_font
        )

        # =========================
        # PROGRESS BAR
        # =========================

        bar_x = card_x + 120
        bar_y = card_y + card_h - 75

        bar_w = card_w - 240
        bar_h = 7

        # Background bar
        draw.rounded_rectangle(
            [
                (bar_x, bar_y),
                (
                    bar_x + bar_w,
                    bar_y + bar_h
                )
            ],
            radius=4,
            fill=(100, 100, 100)
        )

        # Progress
        progress = 0.30

        progress_w = (
            bar_w * progress
        )

        draw.rounded_rectangle(
            [
                (bar_x, bar_y),
                (
                    bar_x + progress_w,
                    bar_y + bar_h
                )
            ],
            radius=4,
            fill=(20, 160, 35)
        )

        # Slider dot
        dot_x = (
            bar_x
            + progress_w
        )

        dot_y = (
            bar_y
            + bar_h // 2
        )

        draw.ellipse(
            [
                (dot_x - 10, dot_y - 10),
                (dot_x + 10, dot_y + 10)
            ],
            fill=(20, 160, 35)
        )

        # =========================
        # TIMESTAMPS
        # =========================

        time_y = bar_y + 18

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

        # =========================
        # WATERMARK
        # =========================

        watermark = "Meera Music"

        wm_width = get_text_width(
            draw,
            watermark,
            watermark_font
        )

        draw.text(
            (
                WIDTH
                - wm_width
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
            file_name,
            "PNG",
            optimize=True
        )

        # Remove raw image
        try:
            os.remove(raw_file)
        except Exception:
            pass

        return file_name

    except Exception as e:

        print(
            f"Thumbnail Error: {e}"
        )

        return YOUTUBE_IMG_URL


# =========================
# YOUTUBE THUMB URL
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

        for result in response["result"]:

            return (
                result["thumbnails"][0]["url"]
                .split("?")[0]
            )

    except Exception as e:

        print(
            f"get_qthumb Error: {e}"
        )

        return YOUTUBE_IMG_URL
