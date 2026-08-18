#
# Copyright (C) 2021-2022 by TheAloneteam@Github.
# Fixed YouTube 16:9 thumbnail / white music-player card version.
#

import os
import re
from io import BytesIO

import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from py_yt import VideosSearch

from config import YOUTUBE_IMG_URL


def changeImageSize(maxWidth, maxHeight, image):
    ratio = min(maxWidth / image.width, maxHeight / image.height)
    return image.resize(
        (max(1, int(image.width * ratio)), max(1, int(image.height * ratio))),
        Image.Resampling.LANCZOS,
    )


async def get_thumb(videoid, user_name=None, next_title=None):
    cache_file = f"cache/{videoid}.png"

    if os.path.isfile(cache_file):
        return cache_file

    try:
        os.makedirs("cache", exist_ok=True)

        # -----------------------------
        # Get YouTube video information
        # -----------------------------
        url = f"https://www.youtube.com/watch?v={videoid}"
        results = VideosSearch(url, limit=1)
        res = await results.next()

        if not res or not res.get("result"):
            raise Exception("No results found")

        result = res["result"][0]

        try:
            title = re.sub(r"\W+", " ", result["title"]).strip()
        except Exception:
            title = "Unsupported Title"

        try:
            duration = result["duration"]
        except Exception:
            duration = "0:00"

        try:
            channel = result["channel"]["name"]
        except Exception:
            channel = "Unknown Artist"

        # ---------------------------------------------
        # Best YouTube thumbnail: 16:9, no forced crop
        # ---------------------------------------------
        thumb_urls = [
            f"https://i.ytimg.com/vi/{videoid}/maxresdefault.jpg",
            f"https://i.ytimg.com/vi/{videoid}/sddefault.jpg",
            f"https://i.ytimg.com/vi/{videoid}/hqdefault.jpg",
        ]

        thumb_data = None

        timeout = aiohttp.ClientTimeout(total=15)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for thumb_url in thumb_urls:
                try:
                    async with session.get(thumb_url) as resp:
                        if resp.status != 200:
                            continue

                        data = await resp.read()

                        # Validate the image before using it.
                        test = Image.open(BytesIO(data)).convert("RGB")

                        if test.width >= 300 and test.height >= 150:
                            thumb_data = data
                            break

                except Exception:
                    continue

        if thumb_data is None:
            return YOUTUBE_IMG_URL

        temp_thumb = f"cache/thumb_{videoid}.jpg"

        async with aiofiles.open(temp_thumb, "wb") as f:
            await f.write(thumb_data)

        youtube = Image.open(temp_thumb).convert("RGB")

        # -----------------------------
        # 1280x720 dark blurred background
        # -----------------------------
        bg = ImageOps.fit(
            youtube,
            (1280, 720),
            method=Image.Resampling.LANCZOS,
        )
        bg = bg.filter(ImageFilter.GaussianBlur(45))
        bg = ImageEnhance.Brightness(bg).enhance(0.16)

        # -----------------------------
        # Main white player card
        # -----------------------------
        card_w = 1130
        card_h = 660
        card_x = (1280 - card_w) // 2
        card_y = (720 - card_h) // 2

        card = Image.new("RGBA", (card_w, card_h), (248, 248, 250, 255))
        card_draw = ImageDraw.Draw(card)

        card_draw.rounded_rectangle(
            (0, 0, card_w - 1, card_h - 1),
            radius=35,
            fill=(248, 248, 250, 255),
        )

        # ----------------------------------------
        # IMPORTANT:
        # YouTube image stays 16:9 and is NEVER
        # cropped. ImageOps.contain() is used.
        # ----------------------------------------
        margin = 45
        image_x = margin
        image_y = 30
        image_w = card_w - (margin * 2)
        image_h = int(image_w * 9 / 16)

        thumb_canvas = Image.new(
            "RGB",
            (image_w, image_h),
            "white",
        )

        contained = ImageOps.contain(
            youtube,
            (image_w, image_h),
            method=Image.Resampling.LANCZOS,
        )

        paste_x = (image_w - contained.width) // 2
        paste_y = (image_h - contained.height) // 2

        thumb_canvas.paste(contained, (paste_x, paste_y))

        # Rounded corners for thumbnail.
        mask = Image.new("L", (image_w, image_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            (0, 0, image_w - 1, image_h - 1),
            radius=25,
            fill=255,
        )

        card.paste(
            thumb_canvas,
            (image_x, image_y),
            mask,
        )

        # -----------------------------
        # Fonts
        # -----------------------------
        def get_font(path, size):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                try:
                    return ImageFont.truetype("arial.ttf", size)
                except Exception:
                    return ImageFont.load_default()

        font_title = get_font("AloneMusic/assets/font.ttf", 31)
        font_artist = get_font("AloneMusic/assets/font2.ttf", 22)
        font_time = get_font("AloneMusic/assets/font3.ttf", 21)
        font_watermark = get_font("AloneMusic/assets/font2.ttf", 25)

        def text_width(text, font):
            try:
                return card_draw.textlength(text, font=font)
            except Exception:
                box = card_draw.textbbox((0, 0), text, font=font)
                return box[2] - box[0]

        # -----------------------------
        # Title: maximum 2 lines
        # -----------------------------
        title_area_w = card_w - 90
        title_y = image_y + image_h + 20

        words = title.split()
        lines = []
        current = ""

        for word in words:
            test = f"{current} {word}".strip()

            if text_width(test, font_title) <= title_area_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word

                if len(lines) == 2:
                    break

        if current and len(lines) < 2:
            lines.append(current)

        if len(lines) == 2 and len(words) > 0:
            # Add ellipsis when title did not fit completely.
            used = " ".join(lines).split()
            if len(used) < len(words):
                last = lines[1]
                while last and text_width(last + "...", font_title) > title_area_w:
                    last = last.rsplit(" ", 1)[0] if " " in last else ""
                lines[1] = (last + "...").strip()

        line_gap = 5
        line_heights = []

        for line in lines:
            box = card_draw.textbbox((0, 0), line, font=font_title)
            line_heights.append(box[3] - box[1])

        total_title_h = sum(line_heights) + line_gap * max(0, len(lines) - 1)

        current_y = title_y

        for line, h in zip(lines, line_heights):
            w = text_width(line, font_title)
            x = (card_w - w) / 2

            card_draw.text(
                (x, current_y),
                line,
                fill=(15, 15, 18),
                font=font_title,
            )

            current_y += h + line_gap

        # -----------------------------
        # Channel / artist
        # -----------------------------
        artist_text = channel

        artist_w = text_width(artist_text, font_artist)
        artist_x = (card_w - artist_w) / 2
        artist_y = current_y + 4

        card_draw.text(
            (artist_x, artist_y),
            artist_text,
            fill=(105, 105, 110),
            font=font_artist,
        )

        # -----------------------------
        # Progress bar
        # -----------------------------
        bar_x = 70
        bar_w = card_w - 140
        bar_y = card_h - 65
        bar_h = 7

        # Gray track
        card_draw.rounded_rectangle(
            (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h),
            radius=4,
            fill=(165, 165, 165),
        )

        # Green progress
        progress = 0.20
        progress_w = max(1, int(bar_w * progress))

        card_draw.rounded_rectangle(
            (bar_x, bar_y, bar_x + progress_w, bar_y + bar_h),
            radius=4,
            fill=(35, 180, 70),
        )

        # Green slider dot
        dot_x = bar_x + progress_w
        dot_y = bar_y + bar_h // 2

        card_draw.ellipse(
            (
                dot_x - 11,
                dot_y - 11,
                dot_x + 11,
                dot_y + 11,
            ),
            fill=(35, 180, 70),
        )

        # -----------------------------
        # Time labels
        # -----------------------------
        time_y = bar_y + 18

        card_draw.text(
            (bar_x, time_y),
            "00:00",
            fill=(20, 20, 20),
            font=font_time,
        )

        duration_w = text_width(duration, font_time)

        card_draw.text(
            (bar_x + bar_w - duration_w, time_y),
            duration,
            fill=(20, 20, 20),
            font=font_time,
        )

        # -----------------------------
        # Composite card on background
        # -----------------------------
        bg_rgba = bg.convert("RGBA")
        bg_rgba.alpha_composite(card, (card_x, card_y))

        draw = ImageDraw.Draw(bg_rgba)

        # -----------------------------
        # Meera Music watermark
        # -----------------------------
        watermark = "Meera Music"
        watermark_w = text_width(watermark, font_watermark)

        draw.text(
            (1280 - watermark_w - 45, 25),
            watermark,
            fill=(255, 255, 255, 230),
            font=font_watermark,
        )

        # -----------------------------
        # Save
        # -----------------------------
        try:
            os.remove(temp_thumb)
        except Exception:
            pass

        bg_rgba.convert("RGB").save(
            cache_file,
            "PNG",
            optimize=True,
        )

        return cache_file

    except Exception as e:
        print(f"Thumbnail error: {e}")
        return YOUTUBE_IMG_URL


async def get_qthumb(vidid):
    try:
        url = f"https://www.youtube.com/watch?v={vidid}"
        results = VideosSearch(url, limit=1)
        res = await results.next()

        for result in res.get("result", []):
            return result["thumbnails"][0]["url"].split("?")[0]

        return YOUTUBE_IMG_URL

    except Exception as e:
        print(e)
        return YOUTUBE_IMG_URL
            
