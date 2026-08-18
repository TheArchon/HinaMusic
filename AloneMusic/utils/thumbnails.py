#
# Copyright (C) 2021-2022 by TheAloneTeam@Github
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


CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


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


def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()


async def get_thumb(videoid, user_name=None, next_title=None):

    output_file = f"{CACHE_DIR}/{videoid}.png"

    if os.path.isfile(output_file):
        return output_file

    url = f"https://www.youtube.com/watch?v={videoid}"

    try:
        # -----------------------------------------
        # GET YOUTUBE DATA
        # -----------------------------------------
        results = VideosSearch(url, limit=1)
        res = await results.next()

        if not res or "result" not in res or not res["result"]:
            raise Exception("No results found")

        result = res["result"][0]

        # Title
        try:
            title = result["title"]
        except Exception:
            title = "Unknown Song"

        title = re.sub(r"\s+", " ", title).strip()

        # Duration
        try:
            duration = result["duration"]
        except Exception:
            duration = "0:00"

        # Thumbnail
        try:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        except Exception:
            return YOUTUBE_IMG_URL

        # Channel / Artist
        try:
            channel = result["channel"]["name"]
        except Exception:
            channel = "Unknown Artist"

        # -----------------------------------------
        # DOWNLOAD THUMBNAIL
        # -----------------------------------------
        thumb_file = f"{CACHE_DIR}/thumb_{videoid}.jpg"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                thumbnail,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:

                if resp.status != 200:
                    return YOUTUBE_IMG_URL

                data = await resp.read()

        async with aiofiles.open(
            thumb_file,
            mode="wb"
        ) as f:
            await f.write(data)

        # -----------------------------------------
        # OPEN ORIGINAL THUMBNAIL
        # -----------------------------------------
        youtube = Image.open(thumb_file).convert("RGB")

        # -----------------------------------------
        # CANVAS
        # -----------------------------------------
        WIDTH = 1536
        HEIGHT = 1024

        # Background
        bg = ImageOps.fit(
            youtube,
            (WIDTH, HEIGHT),
            method=Image.Resampling.LANCZOS
        )

        bg = bg.filter(
            ImageFilter.GaussianBlur(35)
        )

        bg = ImageEnhance.Brightness(
            bg
        ).enhance(0.22)

        bg = bg.convert("RGBA")

        # -----------------------------------------
        # WHITE MUSIC PLAYER
        # -----------------------------------------
        player_x = 85
        player_y = 85
        player_w = 1365
        player_h = 850

        overlay = Image.new(
            "RGBA",
            (WIDTH, HEIGHT),
            (0, 0, 0, 0)
        )

        odraw = ImageDraw.Draw(overlay)

        # Shadow
        odraw.rounded_rectangle(
            [
                (player_x + 10, player_y + 12),
                (
                    player_x + player_w + 10,
                    player_y + player_h + 12
                )
            ],
            radius=45,
            fill=(0, 0, 0, 100)
        )

        # Main white player
        odraw.rounded_rectangle(
            [
                (player_x, player_y),
                (
                    player_x + player_w,
                    player_y + player_h
                )
            ],
            radius=45,
            fill=(250, 250, 252, 255)
        )

        bg = Image.alpha_composite(
            bg,
            overlay
        )

        draw = ImageDraw.Draw(bg)

        # -----------------------------------------
        # THUMBNAIL AREA
        # -----------------------------------------
        image_x = player_x + 45
        image_y = player_y + 30

        image_w = player_w - 90
        image_h = 505

        # White area behind image
        draw.rounded_rectangle(
            [
                (image_x, image_y),
                (
                    image_x + image_w,
                    image_y + image_h
                )
            ],
            radius=28,
            fill=(245, 245, 247, 255)
        )

        # -----------------------------------------
        # IMPORTANT:
        # FULL IMAGE FIT — NO CROPPING
        # -----------------------------------------
        fitted = ImageOps.contain(
            youtube,
            (image_w, image_h),
            method=Image.Resampling.LANCZOS
        )

        # Center image
        paste_x = (
            image_x +
            (image_w - fitted.width) // 2
        )

        paste_y = (
            image_y +
            (image_h - fitted.height) // 2
        )

        # Rounded mask
        mask = Image.new(
            "L",
            fitted.size,
            0
        )

        mask_draw = ImageDraw.Draw(mask)

        mask_draw.rounded_rectangle(
            [
                (0, 0),
                (
                    fitted.width - 1,
                    fitted.height - 1
                )
            ],
            radius=25,
            fill=255
        )

        bg.paste(
            fitted,
            (paste_x, paste_y),
            mask
        )

        # -----------------------------------------
        # FONTS
        # -----------------------------------------
        font_title = get_font(
            "AloneMusic/assets/font.ttf",
            38
        )

        font_artist = get_font(
            "AloneMusic/assets/font2.ttf",
            28
        )

        font_time = get_font(
            "AloneMusic/assets/font3.ttf",
            23
        )

        font_watermark = get_font(
            "AloneMusic/assets/font2.ttf",
            28
        )

        # -----------------------------------------
        # TITLE
        # -----------------------------------------
        max_title_chars = 72

        display_title = title

        if len(display_title) > max_title_chars:
            display_title = (
                display_title[:max_title_chars - 3]
                + "..."
            )

        # Center title
        bbox = draw.textbbox(
            (0, 0),
            display_title,
            font=font_title
        )

        title_width = bbox[2] - bbox[0]

        title_x = (
            WIDTH - title_width
        ) // 2

        title_y = player_y + 540

        draw.text(
            (title_x, title_y),
            display_title,
            fill=(20, 20, 20),
            font=font_title
        )

        # -----------------------------------------
        # ARTIST
        # -----------------------------------------
        artist_text = channel

        bbox = draw.textbbox(
            (0, 0),
            artist_text,
            font=font_artist
        )

        artist_width = bbox[2] - bbox[0]

        artist_x = (
            WIDTH - artist_width
        ) // 2

        artist_y = title_y + 55

        draw.text(
            (artist_x, artist_y),
            artist_text,
            fill=(90, 90, 90),
            font=font_artist
        )

        # -----------------------------------------
        # PROGRESS BAR
        # -----------------------------------------
        bar_x = player_x + 90
        bar_y = player_y + player_h - 80
        bar_w = player_w - 180

        # Background
        draw.rounded_rectangle(
            [
                (bar_x, bar_y),
                (
                    bar_x + bar_w,
                    bar_y + 7
                )
            ],
            radius=4,
            fill=(150, 150, 150)
        )

        # Progress
        progress = 0.30

        progress_w = int(
            bar_w * progress
        )

        draw.rounded_rectangle(
            [
                (bar_x, bar_y),
                (
                    bar_x + progress_w,
                    bar_y + 7
                )
            ],
            radius=4,
            fill=(30, 180, 70)
        )

        # Slider
        dot_x = bar_x + progress_w

        draw.ellipse(
            [
                (dot_x - 11, bar_y - 7),
                (dot_x + 11, bar_y + 15)
            ],
            fill=(30, 180, 70)
        )

        # -----------------------------------------
        # TIME
        # -----------------------------------------
        draw.text(
            (bar_x, bar_y + 20),
            "00:00",
            fill=(35, 35, 35),
            font=font_time
        )

        duration_bbox = draw.textbbox(
            (0, 0),
            duration,
            font=font_time
        )

        duration_width = (
            duration_bbox[2]
            - duration_bbox[0]
        )

        draw.text(
            (
                bar_x +
                bar_w -
                duration_width,
                bar_y + 20
            ),
            duration,
            fill=(35, 35, 35),
            font=font_time
        )

        # -----------------------------------------
        # WATERMARK
        # -----------------------------------------
        watermark = "Meera Music"

        bbox = draw.textbbox(
            (0, 0),
            watermark,
            font=font_watermark
        )

        watermark_w = bbox[2] - bbox[0]

        draw.text(
            (
                WIDTH -
                watermark_w -
                40,
                30
            ),
            watermark,
            fill=(255, 255, 255, 230),
            font=font_watermark
        )

        # -----------------------------------------
        # SAVE
        # -----------------------------------------
        bg = bg.convert("RGB")

        bg.save(
            output_file,
            "PNG",
            optimize=True
        )

        # Remove temporary thumbnail
        try:
            os.remove(thumb_file)
        except Exception:
            pass

        return output_file

    except Exception as e:
        print(f"Thumbnail Error: {e}")
        return YOUTUBE_IMG_URL


# -----------------------------------------
# SIMPLE YOUTUBE THUMBNAIL URL
# -----------------------------------------
async def get_qthumb(vidid):

    try:
        url = f"https://www.youtube.com/watch?v={vidid}"

        results = VideosSearch(
            url,
            limit=1
        )

        data = await results.next()

        if not data or not data.get("result"):
            return YOUTUBE_IMG_URL

        result = data["result"][0]

        thumbnail = (
            result["thumbnails"][0]["url"]
            .split("?")[0]
        )

        return thumbnail

    except Exception as e:
        print(f"QThumb Error: {e}")
        return YOUTUBE_IMG_URL
