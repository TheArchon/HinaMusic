#
# Copyright (C) 2021-2022 by TheAloneTeam@Github.
# GNU v3.0 License Agreement.
#

import os
import re
import textwrap

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

CACHE_DIR = "cache"
CACHE_VERSION = "v3"

os.makedirs(CACHE_DIR, exist_ok=True)


# =========================
# IMAGE RESIZE
# =========================

def changeImageSize(maxWidth, maxHeight, image):
    return ImageOps.fit(
        image.convert("RGB"),
        (maxWidth, maxHeight),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


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
        return draw.textbbox((0, 0), text, font=font)[2]
    except Exception:
        try:
            return draw.textlength(text, font=font)
        except Exception:
            return draw.textsize(text, font=font)[0]


# =========================
# FIT TITLE
# =========================

def fit_title(draw, title, font, max_width, max_lines=2):

    title = re.sub(r"\s+", " ", title).strip()

    if not title:
        return "Unknown Title"

    words = title.split()
    lines = []
    current = ""

    for word in words:
        test = word if not current else current + " " + word

        if text_width(draw, test, font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)

            current = word

            if len(lines) >= max_lines:
                break

    if current and len(lines) < max_lines:
        lines.append(current)

    if not lines:
        return title[:30]

    # If title still has remaining words, add ...
    used_words = " ".join(lines).split()
    if len(used_words) < len(words):
        last = lines[-1]

        while last and text_width(
            draw,
            last + "...",
            font
        ) > max_width:
            last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]

        lines[-1] = last + "..."

    return "\n".join(lines[:max_lines])


# =========================
# SPOTIFY ICON
# =========================

def draw_spotify_icon(draw, x, y, size=48):

    draw.ellipse(
        [(x, y), (x + size, y + size)],
        fill="white"
    )

    # Spotify style curves
    for i in range(3):

        offset = 8 + (i * 7)

        draw.arc(
            [
                (
                    x + 7,
                    y + offset,
                ),
                (
                    x + size - 7,
                    y + offset + 14,
                ),
            ],
            start=190,
            end=350,
            fill="black",
            width=4,
        )


# =========================
# MAIN THUMBNAIL
# =========================

async def get_thumb(videoid, user_name=None, next_title=None):

    # Versioned cache.
    # This prevents old thumbnail from being returned.
    file_name = f"{CACHE_DIR}/{CACHE_VERSION}_{videoid}.png"

    if os.path.isfile(file_name):
        return file_name

    url = f"https://www.youtube.com/watch?v={videoid}"

    try:

        # =========================
        # YOUTUBE DATA
        # =========================

        results = VideosSearch(url, limit=1)
        res = await results.next()

        if (
            not res
            or "result" not in res
            or not res["result"]
        ):
            raise Exception("No results found")

        result = res["result"][0]

        # Title
        try:
            title = result["title"]
            title = re.sub(r"\s+", " ", title).strip()
        except Exception:
            title = "Unsupported Title"

        # Duration
        try:
            duration = result["duration"]
        except Exception:
            duration = "Unknown"

        # Thumbnail
        try:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        except Exception:
            thumbnail = YOUTUBE_IMG_URL

        # Channel
        try:
            channel = result["channel"]["name"]
        except Exception:
            channel = "Unknown Artist"

        # =========================
        # DOWNLOAD THUMBNAIL
        # =========================

        raw_thumb = f"{CACHE_DIR}/raw_{videoid}.jpg"

        async with aiohttp.ClientSession() as session:

            async with session.get(thumbnail) as resp:

                if resp.status != 200:
                    raise Exception(
                        f"Thumbnail download failed: {resp.status}"
                    )

                async with aiofiles.open(
                    raw_thumb,
                    mode="wb"
                ) as f:

                    await f.write(await resp.read())

        youtube = Image.open(raw_thumb).convert("RGB")

        # =========================
        # CANVAS
        # =========================

        canvas_width = 1280
        canvas_height = 720

        # Beautiful blurred background
        background = changeImageSize(
            canvas_width,
            canvas_height,
            youtube
        )

        background = background.filter(
            ImageFilter.GaussianBlur(45)
        )

        background = ImageEnhance.Brightness(
            background
        ).enhance(0.13)

        background = background.convert("RGBA")

        # =========================
        # PLAYER SIZE
        # =========================

        widget_width = 1200
        widget_height = 500

        widget_x = (
            canvas_width - widget_width
        ) // 2

        widget_y = (
            canvas_height - widget_height
        ) // 2

        # =========================
        # OVERLAY
        # =========================

        overlay = Image.new(
            "RGBA",
            (canvas_width, canvas_height),
            (0, 0, 0, 0)
        )

        overlay_draw = ImageDraw.Draw(overlay)

        # Main card
        overlay_draw.rounded_rectangle(
            [
                (widget_x, widget_y),
                (
                    widget_x + widget_width,
                    widget_y + widget_height
                ),
            ],
            radius=55,
            fill=(12, 12, 12, 250),
            outline=(55, 55, 55, 180),
            width=2,
        )

        background = Image.alpha_composite(
            background,
            overlay
        )

        draw = ImageDraw.Draw(background)

        # =========================
        # ALBUM ART
        # =========================

        album_size = 190

        album_x = widget_x + 40
        album_y = widget_y + 45

        album = ImageOps.fit(
            youtube,
            (album_size, album_size),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )

        album = album.convert("RGBA")

        mask = Image.new(
            "L",
            (album_size, album_size),
            0
        )

        mask_draw = ImageDraw.Draw(mask)

        mask_draw.rounded_rectangle(
            [
                (0, 0),
                (
                    album_size,
                    album_size
                ),
            ],
            radius=25,
            fill=255,
        )

        album.putalpha(mask)

        background.paste(
            album,
            (album_x, album_y),
            album
        )

        # =========================
        # FONTS
        # =========================

        font_title = get_font(
            "AloneMusic/assets/font.ttf",
            54
        )

        font_artist = get_font(
            "AloneMusic/assets/font2.ttf",
            34
        )

        font_label = get_font(
            "AloneMusic/assets/font2.ttf",
            32
        )

        font_time = get_font(
            "AloneMusic/assets/font3.ttf",
            27
        )

        font_watermark = get_font(
            "AloneMusic/assets/font2.ttf",
            30
        )

        # =========================
        # HEADER
        # =========================

        label_x = (
            album_x
            + album_size
            + 40
        )

        label_y = album_y + 5

        draw_spotify_icon(
            draw,
            label_x,
            label_y,
            size=48
        )

        draw.text(
            (
                label_x + 65,
                label_y + 3
            ),
            "This phone",
            fill="white",
            font=font_label,
        )

        # =========================
        # MEDIA OUTPUT
        # =========================

        pill_w = 270
        pill_h = 70

        pill_x = (
            widget_x
            + widget_width
            - pill_w
            - 40
        )

        pill_y = widget_y + 45

        draw.rounded_rectangle(
            [
                (pill_x, pill_y),
                (
                    pill_x + pill_w,
                    pill_y + pill_h
                ),
            ],
            radius=35,
            fill=(80, 90, 100, 120),
        )

        media_text = "Media output"

        media_w = text_width(
            draw,
            media_text,
            font_label
        )

        draw.text(
            (
                pill_x
                + (pill_w - media_w) // 2,
                pill_y + 15
            ),
            media_text,
            fill="white",
            font=font_label,
        )

        # =========================
        # TITLE
        # =========================

        text_x = label_x

        title_max_width = (
            widget_x
            + widget_width
            - 45
            - text_x
        )

        display_title = fit_title(
            draw,
            title,
            font_title,
            title_max_width,
            max_lines=2,
        )

        title_y = widget_y + 155

        draw.multiline_text(
            (
                text_x,
                title_y
            ),
            display_title,
            fill="white",
            font=font_title,
            spacing=4,
        )

        # =========================
        # ARTIST
        # =========================

        artist_y = widget_y + 310

        draw.text(
            (
                text_x,
                artist_y
            ),
            channel,
            fill="#b3b3b3",
            font=font_artist,
        )

        # =========================
        # CONTROLS
        # =========================

        controls_y = widget_y + 350

        icon_color = "white"

        # Heart
        hx = widget_x + 430
        hy = controls_y

        draw.ellipse(
            [
                (hx - 18, hy - 15),
                (hx + 8, hy + 12)
            ],
            fill=icon_color
        )

        draw.ellipse(
            [
                (hx + 5, hy - 15),
                (hx + 31, hy + 12)
            ],
            fill=icon_color
        )

        draw.polygon(
            [
                (hx - 18, hy),
                (hx + 31, hy),
                (hx + 6, hy + 35),
            ],
            fill=icon_color,
        )

        # Previous
        px = widget_x + 600
        py = controls_y + 5

        draw.polygon(
            [
                (px + 25, py - 25),
                (px - 8, py),
                (px + 25, py + 25),
            ],
            fill=icon_color,
        )

        draw.rectangle(
            [
                (px - 15, py - 25),
                (px - 7, py + 25),
            ],
            fill=icon_color,
        )

        # Pause
        pax = widget_x + 780
        pay = controls_y + 5

        draw.rectangle(
            [
                (pax - 18, pay - 27),
                (pax - 5, pay + 27),
            ],
            fill=icon_color,
        )

        draw.rectangle(
            [
                (pax + 5, pay - 27),
                (pax + 18, pay + 27),
            ],
            fill=icon_color,
        )

        # Next
        nx = widget_x + 960
        ny = controls_y + 5

        draw.polygon(
            [
                (nx - 25, ny - 25),
                (nx + 8, ny),
                (nx - 25, ny + 25),
            ],
            fill=icon_color,
        )

        draw.rectangle(
            [
                (nx + 8, ny - 25),
                (nx + 16, ny + 25),
            ],
            fill=icon_color,
        )

        # =========================
        # PROGRESS BAR
        # =========================

        bar_x = widget_x + 55

        bar_y = (
            widget_y
            + widget_height
            - 105
        )

        bar_width = (
            widget_width - 110
        )

        # Background
        draw.rounded_rectangle(
            [
                (bar_x, bar_y),
                (
                    bar_x + bar_width,
                    bar_y + 7
                ),
            ],
            radius=4,
            fill=(255, 255, 255, 55),
        )

        # Progress
        progress = 0.20

        progress_width = (
            bar_width * progress
        )

        draw.rounded_rectangle(
            [
                (bar_x, bar_y),
                (
                    bar_x + progress_width,
                    bar_y + 7
                ),
            ],
            radius=4,
            fill="white",
        )

        # Slider
        dot_x = (
            bar_x
            + progress_width
        )

        dot_y = bar_y + 3

        draw.ellipse(
            [
                (dot_x - 15, dot_y - 15),
                (dot_x + 15, dot_y + 15),
            ],
            fill="white",
        )

        # =========================
        # TIME
        # =========================

        time_y = bar_y + 25

        draw.text(
            (
                bar_x,
                time_y
            ),
            "00:00",
            fill="#b3b3b3",
            font=font_time,
        )

        duration_width = text_width(
            draw,
            duration,
            font_time
        )

        draw.text(
            (
                bar_x
                + bar_width
                - duration_width,
                time_y
            ),
            duration,
            fill="#b3b3b3",
            font=font_time,
        )

        # =========================
        # WATERMARK
        # =========================

        watermark = "Meera Music"

        watermark_w = text_width(
            draw,
            watermark,
            font_watermark
        )

        draw.text(
            (
                canvas_width
                - watermark_w
                - 40,
                25
            ),
            watermark,
            fill=(255, 255, 255, 180),
            font=font_watermark,
        )

        # =========================
        # SAVE
        # =========================

        background = background.convert("RGB")

        background.save(
            file_name,
            "PNG",
            optimize=True,
        )

        # Remove temporary thumbnail
        try:
            os.remove(raw_thumb)
        except Exception:
            pass

        return file_name

    except Exception as e:

        print(
            f"get_thumb error: {e}"
        )

        return YOUTUBE_IMG_URL


# =========================
# GET YOUTUBE THUMBNAIL
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

            thumbnail = (
                result["thumbnails"][0]["url"]
                .split("?")[0]
            )

            return thumbnail

    except Exception as e:

        print(
            f"get_qthumb error: {e}"
        )

        return YOUTUBE_IMG_URL
