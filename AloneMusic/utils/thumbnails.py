#
# Copyright (C) 2021-2022 by TheAloneteam@Github
#
# This file is part of AloneMusic
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


# ==========================================================
# SETTINGS
# ==========================================================

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

WIDTH = 1280
HEIGHT = 720

FONT_DIR = "AloneMusic/assets"


# ==========================================================
# IMAGE RESIZE
# ==========================================================

def changeImageSize(maxWidth, maxHeight, image):
    ratio = min(
        maxWidth / image.width,
        maxHeight / image.height
    )

    new_width = int(image.width * ratio)
    new_height = int(image.height * ratio)

    return image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS
    )


# ==========================================================
# FONT
# ==========================================================

def load_font(filename, size, bold=False):

    paths = [
        os.path.join(FONT_DIR, filename),
        os.path.join("assets", filename),
        filename,
    ]

    for path in paths:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception:
            pass

    fallback = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",

        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]

    for path in fallback:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception:
            pass

    return ImageFont.load_default()


# ==========================================================
# TEXT HELPERS
# ==========================================================

def text_width(draw, text, font):
    try:
        return draw.textlength(text, font=font)
    except Exception:
        return draw.textbbox(
            (0, 0),
            text,
            font=font
        )[2]


def shorten_text(text, max_chars):
    text = str(text).strip()

    if len(text) <= max_chars:
        return text

    return text[:max_chars - 3] + "..."


# ==========================================================
# ROUNDED IMAGE
# ==========================================================

def rounded_image(image, size, radius=38):

    image = ImageOps.fit(
        image.convert("RGB"),
        (size, size),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5)
    )

    mask = Image.new(
        "L",
        (size, size),
        0
    )

    mask_draw = ImageDraw.Draw(mask)

    mask_draw.rounded_rectangle(
        (0, 0, size, size),
        radius=radius,
        fill=255
    )

    result = Image.new(
        "RGBA",
        (size, size),
        (0, 0, 0, 0)
    )

    result.paste(
        image,
        (0, 0),
        mask
    )

    return result


# ==========================================================
# DOWNLOAD THUMBNAIL
# ==========================================================

async def download_thumbnail(url, path):

    try:

        timeout = aiohttp.ClientTimeout(
            total=20
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(url) as resp:

                if resp.status != 200:
                    return False

                data = await resp.read()

                async with aiofiles.open(
                    path,
                    "wb"
                ) as f:
                    await f.write(data)

        return True

    except Exception as e:
        print(f"Thumbnail Download Error: {e}")
        return False


# ==========================================================
# MAIN THUMBNAIL
# ==========================================================

async def get_thumb(
    videoid,
    user_name=None,
    next_title=None
):

    output_file = f"{CACHE_DIR}/{videoid}.png"

    # ------------------------------------------------------
    # CACHE
    # ------------------------------------------------------

    if os.path.isfile(output_file):
        return output_file

    thumb_file = f"{CACHE_DIR}/thumb_{videoid}.jpg"

    try:

        # ==================================================
        # YOUTUBE SEARCH
        # ==================================================

        url = f"https://www.youtube.com/watch?v={videoid}"

        results = VideosSearch(
            url,
            limit=1
        )

        res = await results.next()

        if not res:
            raise Exception("No YouTube result")

        if "result" not in res:
            raise Exception("Invalid YouTube result")

        if not res["result"]:
            raise Exception("Empty YouTube result")

        result = res["result"][0]

        # ==================================================
        # TITLE
        # ==================================================

        try:
            title = result.get(
                "title",
                "Unknown Song"
            )

            title = re.sub(
                r"\s+",
                " ",
                title
            ).strip()

        except Exception:
            title = "Unknown Song"

        # ==================================================
        # DURATION
        # ==================================================

        duration = result.get(
            "duration",
            "0:00"
        )

        if not duration:
            duration = "0:00"

        # ==================================================
        # CHANNEL
        # ==================================================

        try:
            channel = result.get(
                "channel",
                {}
            ).get(
                "name",
                "Unknown Artist"
            )

        except Exception:
            channel = "Unknown Artist"

        # ==================================================
        # THUMBNAIL
        # ==================================================

        thumbnails = result.get(
            "thumbnails",
            []
        )

        if thumbnails:

            thumbnail = thumbnails[-1].get(
                "url"
            )

        else:

            thumbnail = YOUTUBE_IMG_URL

        if not thumbnail:
            thumbnail = YOUTUBE_IMG_URL

        thumbnail = thumbnail.split("?")[0]

        # ==================================================
        # DOWNLOAD
        # ==================================================

        success = await download_thumbnail(
            thumbnail,
            thumb_file
        )

        if not success:
            return YOUTUBE_IMG_URL

        # ==================================================
        # OPEN THUMBNAIL
        # ==================================================

        youtube = Image.open(
            thumb_file
        ).convert("RGB")

        # ==================================================
        # BACKGROUND
        # ==================================================

        background = ImageOps.fit(
            youtube,
            (WIDTH, HEIGHT),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5)
        )

        background = background.filter(
            ImageFilter.GaussianBlur(28)
        )

        background = ImageEnhance.Brightness(
            background
        ).enhance(0.27)

        background = ImageEnhance.Contrast(
            background
        ).enhance(0.85)

        background = background.convert(
            "RGBA"
        )

        # ==================================================
        # DARK OVERLAY
        # ==================================================

        dark_overlay = Image.new(
            "RGBA",
            (WIDTH, HEIGHT),
            (0, 0, 0, 95)
        )

        background = Image.alpha_composite(
            background,
            dark_overlay
        )

        draw = ImageDraw.Draw(
            background
        )

        # ==================================================
        # LEFT ALBUM ART
        # ==================================================

        album_size = 600

        album_x = 80
        album_y = 130

        # Shadow
        shadow = Image.new(
            "RGBA",
            (album_size + 35, album_size + 35),
            (0, 0, 0, 0)
        )

        shadow_draw = ImageDraw.Draw(
            shadow
        )

        shadow_draw.rounded_rectangle(
            (
                15,
                15,
                album_size + 15,
                album_size + 15
            ),
            radius=42,
            fill=(0, 0, 0, 130)
        )

        shadow = shadow.filter(
            ImageFilter.GaussianBlur(12)
        )

        background.alpha_composite(
            shadow,
            (
                album_x - 8,
                album_y - 5
            )
        )

        album = rounded_image(
            youtube,
            album_size,
            radius=40
        )

        background.alpha_composite(
            album,
            (
                album_x,
                album_y
            )
        )

        # ==================================================
        # ALBUM BOTTOM LABEL
        # ==================================================

        label_height = 90

        label_overlay = Image.new(
            "RGBA",
            (
                album_size,
                label_height
            ),
            (255, 255, 255, 105)
        )

        label_mask = Image.new(
            "L",
            (
                album_size,
                label_height
            ),
            0
        )

        label_draw = ImageDraw.Draw(
            label_mask
        )

        label_draw.rectangle(
            (
                0,
                0,
                album_size,
                label_height
            ),
            fill=255
        )

        label_overlay.putalpha(
            label_mask
        )

        background.alpha_composite(
            label_overlay,
            (
                album_x,
                album_y + album_size - label_height
            )
        )

        # ==================================================
        # ALBUM LABEL FONT
        # ==================================================

        font_mashup = load_font(
            "font2.ttf",
            34,
            bold=True
        )

        mashup_text = "Bollywood Mashup"

        bbox = draw.textbbox(
            (0, 0),
            mashup_text,
            font=font_mashup
        )

        mashup_w = bbox[2] - bbox[0]
        mashup_h = bbox[3] - bbox[1]

        draw.text(
            (
                album_x +
                (album_size - mashup_w) // 2,
                album_y +
                album_size -
                label_height +
                (label_height - mashup_h) // 2 -
                4
            ),
            mashup_text,
            font=font_mashup,
            fill="black"
        )

        # ==================================================
        # RIGHT SIDE
        # ==================================================

        right_x = 765

        # ==================================================
        # TITLE FONT
        # ==================================================

        font_title = load_font(
            "font.ttf",
            38,
            bold=True
        )

        font_artist = load_font(
            "font2.ttf",
            27,
            bold=True
        )

        font_small = load_font(
            "font2.ttf",
            18,
            bold=True
        )

        font_time = load_font(
            "font3.ttf",
            17,
            bold=True
        )

        # ==================================================
        # TITLE
        # ==================================================

        display_title = shorten_text(
            title,
            28
        )

        draw.text(
            (
                right_x,
                178
            ),
            display_title,
            font=font_title,
            fill="white"
        )

        # ==================================================
        # ARTIST
        # ==================================================

        display_artist = shorten_text(
            channel,
            25
        )

        draw.text(
            (
                right_x,
                247
            ),
            display_artist,
            font=font_artist,
            fill=(220, 220, 220)
        )

        # ==================================================
        # STAR BUTTON
        # ==================================================

        star_x = 1305
        star_y = 175

        draw.ellipse(
            (
                star_x,
                star_y,
                star_x + 50,
                star_y + 50
            ),
            fill=(150, 150, 150, 150)
        )

        font_star = load_font(
            "font2.ttf",
            31
        )

        draw.text(
            (
                star_x + 10,
                star_y + 5
            ),
            "☆",
            font=font_star,
            fill="white"
        )

        # ==================================================
        # MENU BUTTON
        # ==================================================

        menu_x = 1375
        menu_y = 175

        draw.ellipse(
            (
                menu_x,
                menu_y,
                menu_x + 50,
                menu_y + 50
            ),
            fill=(150, 150, 150, 150)
        )

        draw.text(
            (
                menu_x + 17,
                menu_y + 2
            ),
            "⋮",
            font=font_star,
            fill="white"
        )

        # ==================================================
        # PROGRESS BAR
        # ==================================================

        bar_x = 765
        bar_y = 360
        bar_width = 675

        # Background
        draw.rounded_rectangle(
            (
                bar_x,
                bar_y,
                bar_x + bar_width,
                bar_y + 8
            ),
            radius=5,
            fill=(180, 180, 180, 120)
        )

        # Progress
        progress = 0.25

        progress_x = int(
            bar_x +
            bar_width * progress
        )

        draw.rounded_rectangle(
            (
                bar_x,
                bar_y,
                progress_x,
                bar_y + 8
            ),
            radius=5,
            fill="white"
        )

        # Dot
        draw.ellipse(
            (
                progress_x - 11,
                bar_y - 7,
                progress_x + 11,
                bar_y + 15
            ),
            fill="white"
        )

        # ==================================================
        # TIME
        # ==================================================

        draw.text(
            (
                bar_x,
                395
            ),
            "0:00",
            font=font_time,
            fill="white"
        )

        duration_width = text_width(
            draw,
            str(duration),
            font_time
        )

        draw.text(
            (
                bar_x +
                bar_width -
                duration_width,
                395
            ),
            str(duration),
            font=font_time,
            fill="white"
        )

        # ==================================================
        # MEDIA OUTPUT
        # ==================================================

        output_text = "DHIYABOTS"

        output_font = load_font(
            "font2.ttf",
            17,
            bold=True
        )

        output_w = text_width(
            draw,
            output_text,
            output_font
        )

        pill_w = int(
            output_w + 45
        )

        pill_h = 38

        pill_x = 1035
        pill_y = 385

        draw.rounded_rectangle(
            (
                pill_x,
                pill_y,
                pill_x + pill_w,
                pill_y + pill_h
            ),
            radius=20,
            fill=(190, 190, 190, 220)
        )

        draw.text(
            (
                pill_x +
                (pill_w - output_w) / 2,
                pill_y + 8
            ),
            output_text,
            font=output_font,
            fill=(20, 20, 20)
        )

        # ==================================================
        # PLAYER CONTROLS
        # ==================================================

        control_y = 575

        icon_color = "white"

        # --------------------------------------------------
        # PREVIOUS
        # --------------------------------------------------

        px = 930

        draw.polygon(
            [
                (px, control_y),
                (px + 35, control_y - 30),
                (px + 35, control_y + 30)
            ],
            fill=icon_color
        )

        draw.polygon(
            [
                (px + 35, control_y),
                (px + 75, control_y - 30),
                (px + 75, control_y + 30)
            ],
            fill=icon_color
        )

        draw.rectangle(
            (
                px - 5,
                control_y - 30,
                px + 2,
                control_y + 30
            ),
            fill=icon_color
        )

        # --------------------------------------------------
        # PAUSE
        # --------------------------------------------------

        pax = 1085

        draw.rounded_rectangle(
            (
                pax,
                control_y - 27,
                pax + 14,
                control_y + 27
            ),
            radius=4,
            fill=icon_color
        )

        draw.rounded_rectangle(
            (
                pax + 27,
                control_y - 27,
                pax + 41,
                control_y + 27
            ),
            radius=4,
            fill=icon_color
        )

        # --------------------------------------------------
        # NEXT
        # --------------------------------------------------

        nx = 1235

        draw.polygon(
            [
                (nx, control_y - 30),
                (nx + 40, control_y),
                (nx, control_y + 30)
            ],
            fill=icon_color
        )

        draw.polygon(
            [
                (nx - 35, control_y - 30),
                (nx + 5, control_y),
                (nx - 35, control_y + 30)
            ],
            fill=icon_color
        )

        draw.rectangle(
            (
                nx + 40,
                control_y - 30,
                nx + 47,
                control_y + 30
            ),
            fill=icon_color
        )

        # ==================================================
        # VOLUME ICON
        # ==================================================

        volume_font = load_font(
            "font2.ttf",
            27,
            bold=True
        )

        draw.text(
            (
                860,
                655
            ),
            "◖))",
            font=volume_font,
            fill="white"
        )

        # ==================================================
        # VOLUME BAR
        # ==================================================

        draw.rounded_rectangle(
            (
                920,
                670,
                1345,
                678
            ),
            radius=5,
            fill="white"
        )

        # ==================================================
        # BOTTOM ICONS
        # ==================================================

        bottom_font = load_font(
            "font2.ttf",
            34,
            bold=True
        )

        draw.text(
            (
                1050,
                705
            ),
            "▣",
            font=bottom_font,
            fill="white"
        )

        draw.text(
            (
                1150,
                705
            ),
            "☷",
            font=bottom_font,
            fill="white"
        )

        # ==================================================
        # WATERMARK
        # ==================================================

        watermark_font = load_font(
            "font2.ttf",
            22,
            bold=True
        )

        draw.text(
            (
                1080,
                40
            ),
            "Meera Music",
            font=watermark_font,
            fill=(255, 255, 255, 150)
        )

        # ==================================================
        # SAVE
        # ==================================================

        background = background.convert(
            "RGB"
        )

        background.save(
            output_file,
            "PNG",
            optimize=True
        )

        # ==================================================
        # REMOVE TEMP
        # ==================================================

        try:
            os.remove(thumb_file)
        except Exception:
            pass

        return output_file

    except Exception as e:

        print(
            f"Thumbnail Error: {e}"
        )

        try:
            if os.path.exists(
                thumb_file
            ):
                os.remove(
                    thumb_file
                )
        except Exception:
            pass

        return YOUTUBE_IMG_URL


# ==========================================================
# GET YOUTUBE THUMBNAIL URL
# ==========================================================

async def get_qthumb(vidid):

    try:

        url = (
            f"https://www.youtube.com/"
            f"watch?v={vidid}"
        )

        results = VideosSearch(
            url,
            limit=1
        )

        data = await results.next()

        if not data:
            return YOUTUBE_IMG_URL

        result = data.get(
            "result",
            []
        )

        if not result:
            return YOUTUBE_IMG_URL

        thumbnails = result[0].get(
            "thumbnails",
            []
        )

        if not thumbnails:
            return YOUTUBE_IMG_URL

        thumbnail = thumbnails[-1].get(
            "url"
        )

        if not thumbnail:
            return YOUTUBE_IMG_URL

        return thumbnail.split("?")[0]

    except Exception as e:

        print(
            f"get_qthumb Error: {e}"
        )

        return YOUTUBE_IMG_URL
