#
# Copyright (C) 2021-2022 by TheAloneteam@Github, < https://github.com/TheAloneTeam >.
#
# This file is part of < https://github.com/TheAloneTeam/AloneMusic > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TheAloneTeam/AloneMusic/blob/master/LICENSE >
#
# All rights reserved.

import os
import re
from io import BytesIO

import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from py_yt import VideosSearch

from config import YOUTUBE_IMG_URL


def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage


async def get_thumb(videoid, user_name=None, next_title=None):
    if os.path.isfile(f"cache/{videoid}.png"):
        return f"cache/{videoid}.png"

    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        results = VideosSearch(url, limit=1)
        res = await results.next()
        if not res or "result" not in res or not res["result"]:
            raise Exception("No results found for videoid")
        
        for result in res["result"]:
            try:
                title = result["title"]
                title = re.sub(r"\W+", " ", title)
                title = title.title()
            except:
                title = "Unsupported Title"
            try:
                duration = result["duration"]
            except:
                duration = "Unknown"
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            try:
                channel = result["channel"]["name"]
            except:
                chann        # ------------------------------------------------------------
        # Get the best YouTube thumbnail available.
        # maxresdefault is preferred because it is normally 16:9.
        # ------------------------------------------------------------
        thumb_urls = [
            f"https://i.ytimg.com/vi/{videoid}/maxresdefault.jpg",
            f"https://i.ytimg.com/vi/{videoid}/sddefault.jpg",
            f"https://i.ytimg.com/vi/{videoid}/hqdefault.jpg",
        ]

        thumb_data = None

        async with aiohttp.ClientSession() as session:
            for thumb_url in thumb_urls:
                try:
                    async with session.get(
                        thumb_url,
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            try:
                                test = Image.open(BytesIO(data)).convert("RGB")
                                if test.width >= 300 and test.height >= 150:
                                    thumb_data = data
                                    break
                            except Exception:
                                pass
                except Exception:
                    continue

        if thumb_data is None:
            return YOUTUBE_IMG_URL

        async with aiofiles.open(
            f"cache/thumb{videoid}.png",
            mode="wb"
        ) as f:
            await f.write(thumb_data)

        youtube = Image.open(
            f"cache/thumb{videoid}.png"
        ).convert("RGB")

        # ------------------------------------------------------------
        # Background
        # ------------------------------------------------------------
        bg = Image.new("RGB", (1280, 720), (20, 20, 20))

        # Soft blurred thumbnail background
        bg_thumb = ImageOps.fit(
            youtube,
            (1280, 720),
            method=Image.Resampling.LANCZOS
        )
        bg_thumb = bg_thumb.filter(
            ImageFilter.GaussianBlur(45)
        )
        bg_thumb = ImageEnhance.Brightness(
            bg_thumb
        ).enhance(0.18)
        bg.paste(bg_thumb, (0, 0))

        # ------------------------------------------------------------
        # White player card
        # ------------------------------------------------------------
        widget_width = 1130
        widget_height = 660

        widget_x = (1280 - widget_width) // 2
        widget_y = (720 - widget_height) // 2

        card = Image.new(
            "RGBA",
            (widget_width, widget_height),
            (248, 248, 250, 255)
        )

        card_draw = ImageDraw.Draw(card)

        card_draw.rounded_rectangle(
            [
                (0, 0),
                (widget_width - 1, widget_height - 1)
            ],
            radius=35,
            fill=(248, 248, 250, 255)
        )

        # ------------------------------------------------------------
        # 16:9 thumbnail area
        # IMPORTANT: contain() = NO CROPPING
        # ------------------------------------------------------------
        image_x = 45
        image_y = 30

        image_w = widget_width - 90
        image_h = int(image_w * 9 / 16)

        # White 16:9 canvas so a non-16:9 source still remains complete.
        thumb_canvas = Image.new(
            "RGB",
            (image_w, image_h),
            "white"
        )

        youtube_thumb = ImageOps.contain(
            youtube,
            (image_w, image_h),
            method=Image.Resampling.LANCZOS
        )

        paste_x = (image_w - youtube_thumb.width) // 2
        paste_y = (image_h - youtube_thumb.height) // 2

        thumb_canvas.paste(
            youtube_thumb,
            (paste_x, paste_y)
        )

        # Rounded thumbnail corners
        thumb_mask = Image.new(
            "L",
            (image_w, image_h),
            0
        )

        mask_draw = ImageDraw.Draw(thumb_mask)

        mask_draw.rounded_rectangle(
            [
                (0, 0),
                (image_w - 1, image_h - 1)
            ],
            radius=25,
            fill=255
        )

        card.paste(
            thumb_canvas,
            (image_x, image_y),
            thumb_mask
        )

        # ------------------------------------------------------------
        # Fonts
        # ------------------------------------------------------------
        def get_font(path, size):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                try:
                    return ImageFont.truetype(
                        "arial.ttf",
                        size
                    )
                except Exception:
                    return ImageFont.load_default()

        font_title = get_font(
            "AloneMusic/assets/font.ttf",
            34
        )
        font_artist = get_font(
            "AloneMusic/assets/font2.ttf",
            25
        )
        font_time = get_font(
            "AloneMusic/assets/font3.ttf",
            23
        )
        font_watermark = get_font(
            "AloneMusic/assets/font2.ttf",
            28
        )

        # ------------------------------------------------------------
        # Title - centered, maximum 2 lines
        # ------------------------------------------------------------
        title_area_width = widget_width - 90
        title_y = image_y + image_h + 22

        def text_width(txt, font):
            try:
                return card_draw.textlength(
                    txt,
                    font=font
                )
            except Exception:
                return card_draw.textbbox(
                    (0, 0),
                    txt,
                    font=font
                )[2]

        words = title.split()
        lines = []
        current = ""

        for word in words:
            candidate = (
                f"{current} {word}"
                if current else word
            )

            if text_width(
                candidate,
                font_title
            ) <= title_area_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        # Keep the same clean 2-line style as the reference.
        lines = lines[:2]

        line_gap = 40

        for i, line in enumerate(lines):
            line_w = text_width(
                line,
                font_title
            )

            card_draw.text(
                (
                    (widget_width - line_w) // 2,
                    title_y + i * line_gap
                ),
                line,
                fill=(15, 15, 15),
                font=font_title
            )

        # ------------------------------------------------------------
        # Channel / artist
        # ------------------------------------------------------------
        channel_y = (
            title_y +
            len(lines) * line_gap +
            4
        )

        channel_w = text_width(
            channel,
            font_artist
        )

        card_draw.text(
            (
                (widget_width - channel_w) // 2,
                channel_y
            ),
            channel,
            fill=(110, 110, 110),
            font=font_artist
        )

        # ------------------------------------------------------------
        # Progress bar
        # ------------------------------------------------------------
        bar_x = 90
        bar_y = widget_height - 78
        bar_width = widget_width - 180

        card_draw.rounded_rectangle(
            [
                (bar_x, bar_y),
                (bar_x + bar_width, bar_y + 7)
            ],
            radius=5,
            fill=(160, 160, 160)
        )

        progress = 0.30

        fg_width = int(
            bar_width * progress
        )

        card_draw.rounded_rectangle(
            [
                (bar_x, bar_y),
                (bar_x + fg_width, bar_y + 7)
            ],
            radius=5,
            fill=(35, 180, 70)
        )

        dot_x = bar_x + fg_width

        card_draw.ellipse(
            [
                (dot_x - 12, bar_y - 8),
                (dot_x + 12, bar_y + 16)
            ],
            fill=(35, 180, 70)
        )

        # ------------------------------------------------------------
        # Timestamps
        # ------------------------------------------------------------
        time_y = bar_y + 20

        card_draw.text(
            (bar_x, time_y),
            "00:00",
            fill=(20, 20, 20),
            font=font_time
        )

        duration_width = text_width(
            duration,
            font_time
        )

        card_draw.text(
            (
                bar_x + bar_width - duration_width,
                time_y
            ),
            duration,
            fill=(20, 20, 20),
            font=font_time
        )

        # ------------------------------------------------------------
        # Paste white card onto background
        # ------------------------------------------------------------
        card_mask_full = Image.new(
            "L",
            (widget_width, widget_height),
            0
        )

        ImageDraw.Draw(
            card_mask_full
        ).rounded_rectangle(
            [
                (0, 0),
                (widget_width - 1, widget_height - 1)
            ],
            radius=35,
            fill=255
        )

        bg.paste(
            card,
            (widget_x, widget_y),
            card_mask_full
        )

        # ------------------------------------------------------------
        # Watermark
        # ------------------------------------------------------------
        draw = ImageDraw.Draw(bg)

        watermark = "Meera Music"
        watermark_w = text_width(
            watermark,
            font_watermark
        )

        draw.text(
            (
                1280 - watermark_w - 45,
                25
            ),
            watermark,
            fill=(255, 255, 255),
            font=font_watermark
        )

        image1 = bg


        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass

        file_name = f"cache/{videoid}.png"
        image1.save(file_name)
        return file_name

    except Exception as e:
        print(e)
        return YOUTUBE_IMG_URL


async def get_qthumb(vidid):
    try:
        url = f"https://www.youtube.com/watch?v={vidid}"
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        return thumbnail
    except Exception as e:
        print(e)
        return YOUTUBE_IMG_URL

        
