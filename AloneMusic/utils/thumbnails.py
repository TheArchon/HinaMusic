# Copyright (C) 2021-2022 by TheAloneteam@Github
# AloneMusic thumbnail generator - combined/fixed version

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


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def changeImageSize(maxWidth, maxHeight, image):
    """Resize an image to fit the requested dimensions."""
    return ImageOps.contain(
        image,
        (maxWidth, maxHeight),
        method=Image.Resampling.LANCZOS,
    )


def get_font(path, size):
    """Load custom font, then Arial, then PIL default."""
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()


def get_text_width(draw, text, font):
    if hasattr(draw, "textlength"):
        return draw.textlength(text, font=font)
    return draw.textbbox((0, 0), text, font=font)[2]


def safe_remove(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
    except Exception:
        pass


# ---------------------------------------------------------
# Main thumbnail
# ---------------------------------------------------------

async def get_thumb(videoid, user_name=None, next_title=None):
    os.makedirs("cache", exist_ok=True)

    output_file = f"cache/{videoid}.png"
    thumb_file = f"cache/thumb_{videoid}.png"

    if os.path.isfile(output_file):
        return output_file

    try:
        # -------------------------------------------------
        # Get YouTube information
        # -------------------------------------------------
        url = f"https://www.youtube.com/watch?v={videoid}"

        results = VideosSearch(url, limit=1)
        res = await results.next()

        if not res or not res.get("result"):
            raise Exception("No YouTube result found")

        result = res["result"][0]

        title = result.get("title", "Unknown Title")
        duration = result.get("duration", "00:00")

        channel_data = result.get("channel") or {}
        channel = channel_data.get("name", "Unknown Artist")

        thumbnails = result.get("thumbnails") or []
        if not thumbnails:
            raise Exception("No thumbnail found")

        thumbnail = thumbnails[0]["url"].split("?")[0]

        # -------------------------------------------------
        # Download YouTube thumbnail
        # -------------------------------------------------
        timeout = aiohttp.ClientTimeout(total=20)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(thumbnail) as response:
                if response.status != 200:
                    raise Exception(
                        f"Thumbnail download failed: HTTP {response.status}"
                    )

                data = await response.read()

                if not data:
                    raise Exception("Downloaded thumbnail is empty")

                async with aiofiles.open(thumb_file, "wb") as f:
                    await f.write(data)

        # -------------------------------------------------
        # Open source image
        # -------------------------------------------------
        original = Image.open(thumb_file).convert("RGB")

        # -------------------------------------------------
        # Canvas - 1536 x 1024
        # -------------------------------------------------
        WIDTH = 1536
        HEIGHT = 1024

        # Blurred background
        background = ImageOps.fit(
            original,
            (WIDTH, HEIGHT),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )

        background = background.filter(
            ImageFilter.GaussianBlur(38)
        )

        background = ImageEnhance.Brightness(
            background
        ).enhance(0.24)

        background = background.convert("RGBA")

        # Slight black overlay
        dark = Image.new(
            "RGBA",
            (WIDTH, HEIGHT),
            (0, 0, 0, 70),
        )

        background = Image.alpha_composite(
            background,
            dark,
        )

        draw = ImageDraw.Draw(background)

        # -------------------------------------------------
        # Main glass player card
        # -------------------------------------------------
        card_x = 75
        card_y = 158
        card_w = 1385
        card_h = 704

        draw.rounded_rectangle(
            (
                card_x,
                card_y,
                card_x + card_w,
                card_y + card_h,
            ),
            radius=45,
            fill=(8, 8, 8, 215),
            outline=(150, 150, 150, 145),
            width=2,
        )

        # -------------------------------------------------
        # Album artwork
        # -------------------------------------------------
        album_x = 128
        album_y = 218
        album_size = 570

        album = ImageOps.fit(
            original,
            (album_size, album_size),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        ).convert("RGBA")

        album_mask = Image.new(
            "L",
            (album_size, album_size),
            0,
        )

        album_mask_draw = ImageDraw.Draw(album_mask)

        album_mask_draw.rounded_rectangle(
            (
                0,
                0,
                album_size,
                album_size,
            ),
            radius=30,
            fill=255,
        )

        album.putalpha(album_mask)

        background.paste(
            album,
            (album_x, album_y),
            album,
        )

        draw = ImageDraw.Draw(background)

        # -------------------------------------------------
        # Fonts
        # -------------------------------------------------
        font_small = get_font(
            "AloneMusic/assets/font2.ttf",
            28,
        )

        font_title = get_font(
            "AloneMusic/assets/font.ttf",
            82,
        )

        font_song = get_font(
            "AloneMusic/assets/font2.ttf",
            42,
        )

        font_artist = get_font(
            "AloneMusic/assets/font2.ttf",
            28,
        )

        font_time = get_font(
            "AloneMusic/assets/font2.ttf",
            24,
        )

        # -------------------------------------------------
        # Right side layout
        # -------------------------------------------------
        right_x = 755

        # Media output pill
        pill_x = right_x
        pill_y = 218
        pill_w = 245
        pill_h = 74

        draw.rounded_rectangle(
            (
                pill_x,
                pill_y,
                pill_x + pill_w,
                pill_y + pill_h,
            ),
            radius=35,
            fill=(60, 60, 60, 175),
        )

        # Small device icon
        draw.rectangle(
            (
                pill_x + 25,
                pill_y + 24,
                pill_x + 48,
                pill_y + 42,
            ),
            outline="white",
            width=3,
        )

        draw.line(
            (
                pill_x + 31,
                pill_y + 48,
                pill_x + 42,
                pill_y + 48,
            ),
            fill="white",
            width=3,
        )

        draw.text(
            (
                pill_x + 70,
                pill_y + 18,
            ),
            "Meera Music",
            fill="white",
            font=font_small,
        )

        # -------------------------------------------------
        # Three-dot menu
        # -------------------------------------------------
        dot_x = 1398

        for dot_y in (238, 255, 272):
            draw.ellipse(
                (
                    dot_x,
                    dot_y,
                    dot_x + 9,
                    dot_y + 9,
                ),
                fill="white",
            )

        # -------------------------------------------------
        # Song title
        # -------------------------------------------------
        draw.text(
            (
                right_x,
                350,
            ),
            "Dil",
            fill="white",
            font=font_title,
        )

        # -------------------------------------------------
        # Song subtitle
        # -------------------------------------------------
        song_name = "Shreya's Version (Lyrical)"

        # Automatically reduce very long text
        if len(song_name) > 32:
            song_name = song_name[:29] + "..."

        draw.text(
            (
                right_x,
                465,
            ),
            song_name,
            fill="white",
            font=font_song,
        )

        # -------------------------------------------------
        # Movie / artist
        # -------------------------------------------------
        info = f"Ek Villain Returns | {channel}"

        # Keep information inside the card
        if len(info) > 42:
            info = info[:39] + "..."

        draw.text(
            (
                right_x,
                535,
            ),
            info,
            fill=(190, 190, 190),
            font=font_artist,
        )

        draw.text(
            (
                right_x,
                580,
            ),
            "T-Series",
            fill=(190, 190, 190),
            font=font_artist,
        )

        # -------------------------------------------------
        # Progress bar
        # -------------------------------------------------
        bar_x = right_x
        bar_y = 670
        bar_w = 560
        bar_h = 6

        draw.rounded_rectangle(
            (
                bar_x,
                bar_y,
                bar_x + bar_w,
                bar_y + bar_h,
            ),
            radius=4,
            fill=(100, 100, 100),
        )

        # Progress percentage
        progress = 0.20
        progress_w = int(bar_w * progress)

        draw.rounded_rectangle(
            (
                bar_x,
                bar_y,
                bar_x + progress_w,
                bar_y + bar_h,
            ),
            radius=4,
            fill=(255, 195, 20),
        )

        # Progress slider
        slider_x = bar_x + progress_w

        draw.ellipse(
            (
                slider_x - 10,
                bar_y - 7,
                slider_x + 10,
                bar_y + 13,
            ),
            fill="white",
        )

        # Time labels
        draw.text(
            (
                bar_x,
                690,
            ),
            "00:00",
            fill="white",
            font=font_time,
        )

        duration_width = get_text_width(
            draw,
            duration,
            font_time,
        )

        draw.text(
            (
                bar_x + bar_w - duration_width,
                690,
            ),
            duration,
            fill="white",
            font=font_time,
        )

        # -------------------------------------------------
        # Controls
        # -------------------------------------------------
        controls_y = 765
        icon_color = (225, 225, 225)

        # Shuffle icon - simple custom drawing
        sx = right_x + 25
        sy = controls_y

        draw.line(
            (
                sx,
                sy - 15,
                sx + 12,
                sy - 15,
                sx + 25,
                sy + 15,
            ),
            fill=icon_color,
            width=5,
        )

        draw.line(
            (
                sx,
                sy + 15,
                sx + 12,
                sy + 15,
                sx + 25,
                sy - 15,
            ),
            fill=icon_color,
            width=5,
        )

        # Previous button
        px = right_x + 175

        draw.polygon(
            [
                (px + 25, controls_y),
                (px + 55, controls_y - 27),
                (px + 55, controls_y + 27),
            ],
            fill="white",
        )

        draw.rectangle(
            (
                px + 14,
                controls_y - 27,
                px + 23,
                controls_y + 27,
            ),
            fill="white",
        )

        # -------------------------------------------------
        # Play / Pause button
        # -------------------------------------------------
        center_x = right_x + 330

        draw.ellipse(
            (
                center_x - 53,
                controls_y - 53,
                center_x + 53,
                controls_y + 53,
            ),
            fill=(255, 195, 20),
        )

        # Pause bars
        draw.rounded_rectangle(
            (
                center_x - 17,
                controls_y - 25,
                center_x - 7,
                controls_y + 25,
            ),
            radius=3,
            fill="black",
        )

        draw.rounded_rectangle(
            (
                center_x + 7,
                controls_y - 25,
                center_x + 17,
                controls_y + 25,
            ),
            radius=3,
            fill="black",
        )

        # -------------------------------------------------
        # Next button
        # -------------------------------------------------
        nx = right_x + 465

        draw.polygon(
            [
                (nx + 5, controls_y),
                (nx + 35, controls_y - 27),
                (nx + 35, controls_y + 27),
            ],
            fill="white",
        )

        draw.rectangle(
            (
                nx + 38,
                controls_y - 27,
                nx + 47,
                controls_y + 27,
            ),
            fill="white",
        )

        # -------------------------------------------------
        # Repeat icon
        # -------------------------------------------------
        rx = right_x + 585
        ry = controls_y

        draw.arc(
            (
                rx - 20,
                ry - 20,
                rx + 20,
                ry + 20,
            ),
            start=40,
            end=320,
            fill=icon_color,
            width=5,
        )

        draw.polygon(
            [
                (rx + 14, ry - 18),
                (rx + 27, ry - 18),
                (rx + 22, ry - 7),
            ],
            fill=icon_color,
        )

        # -------------------------------------------------
        # Save output
        # -------------------------------------------------
        background.convert("RGB").save(
            output_file,
            format="PNG",
            optimize=True,
        )

        safe_remove(thumb_file)

        return output_file

    except Exception as e:
        print(f"get_thumb error: {e}")
        safe_remove(thumb_file)
        return YOUTUBE_IMG_URL


# ---------------------------------------------------------
# Quick thumbnail URL
# ---------------------------------------------------------

async def get_qthumb(vidid):
    try:
        url = f"https://www.youtube.com/watch?v={vidid}"

        results = VideosSearch(url, limit=1)
        res = await results.next()

        if not res or not res.get("result"):
            return YOUTUBE_IMG_URL

        result = res["result"][0]

        thumbnails = result.get("thumbnails") or []

        if not thumbnails:
            return YOUTUBE_IMG_URL

        return thumbnails[0]["url"].split("?")[0]

    except Exception as e:
        print(f"get_qthumb error: {e}")
        return YOUTUBE_IMG_URL
