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


def _lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _parse_duration(duration):
    try:
        parts = [int(p) for p in duration.split(":")]
    except Exception:
        return 0
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def _format_time(seconds):
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


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
                duration = "0:00"
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            try:
                channel = result["channel"]["name"]
            except:
                channel = "Unknown Artist"

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        youtube = Image.open(f"cache/thumb{videoid}.png").convert("RGB")

        CANVAS_W, CANVAS_H = 1280, 720

        # Background: Blurred and darkened version of the thumbnail
        background = changeImageSize(CANVAS_W, CANVAS_H, youtube)
        background = background.filter(ImageFilter.GaussianBlur(60))
        background = ImageEnhance.Brightness(background).enhance(0.18)
        background = background.convert("RGBA")

        # ---- Card / Widget geometry ----
        widget_width = 640
        widget_height = 680
        widget_x = (CANVAS_W - widget_width) // 2
        widget_y = (CANVAS_H - widget_height) // 2
        margin = 40
        radius = 40

        # ---- Soft neon glow behind the card (like the reference image) ----
        glow_layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        glow_pad = 18
        glow_draw.rounded_rectangle(
            [(widget_x - glow_pad, widget_y - glow_pad),
             (widget_x + widget_width + glow_pad, widget_y + widget_height + glow_pad)],
            radius=radius + glow_pad,
            outline=(90, 140, 255, 255),
            width=10,
        )
        glow_draw.rounded_rectangle(
            [(widget_x - glow_pad, widget_y - glow_pad),
             (widget_x + widget_width + glow_pad, widget_y + widget_height + glow_pad)],
            radius=radius + glow_pad,
            outline=(200, 120, 255, 200),
            width=4,
        )
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(14))

        image1 = Image.alpha_composite(background, glow_layer)

        # ---- Main card background ----
        overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)
        draw_overlay.rounded_rectangle(
            [(widget_x, widget_y), (widget_x + widget_width, widget_y + widget_height)],
            radius=radius,
            fill=(18, 16, 24, 235),
        )
        image1 = Image.alpha_composite(image1, overlay)
        draw = ImageDraw.Draw(image1)

        # ---- Fonts ----
        def get_font(path, size):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                try:
                    return ImageFont.truetype("arial.ttf", size)
                except Exception:
                    return ImageFont.load_default()

        font_title = get_font("AloneMusic/assets/font.ttf", 42)
        font_artist = get_font("AloneMusic/assets/font2.ttf", 26)
        font_time = get_font("AloneMusic/assets/font3.ttf", 22)

        def get_text_width(text, font):
            if hasattr(draw, "textlength"):
                return draw.textlength(text, font=font)
            return draw.textsize(text, font=font)[0]

        # ---- Title & Artist (top-left). No heart / playlist icons on the top-right. ----
        text_x = widget_x + margin
        title_y = widget_y + 28

        display_title = title
        if len(display_title) > 26:
            display_title = display_title[:23] + "..."
        draw.text((text_x, title_y), text=display_title, fill="white", font=font_title)

        artist_y = title_y + 58
        draw.text((text_x, artist_y), text=channel, fill="#b3b3b3", font=font_artist)

        # Verified badge next to artist name
        artist_w = get_text_width(channel, font_artist)
        badge_x = text_x + artist_w + 12
        badge_y = artist_y + 3
        badge_size = 20
        draw.ellipse([(badge_x, badge_y), (badge_x + badge_size, badge_y + badge_size)], fill="#3897f0")
        draw.line(
            [(badge_x + 5, badge_y + 10), (badge_x + 9, badge_y + 14), (badge_x + 15, badge_y + 6)],
            fill="white", width=2, joint="curve",
        )

        # ---- Video thumbnail box ----
        img_x0 = widget_x + margin
        img_y0 = artist_y + 55
        img_w = widget_width - 2 * margin
        img_h = 320
        img_x1 = img_x0 + img_w
        img_y1 = img_y0 + img_h

        thumb_fit = ImageOps.fit(youtube, (img_w, img_h), centering=(0.5, 0.4))
        mask = Image.new("L", (img_w, img_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (img_w, img_h)], radius=28, fill=255)
        thumb_fit = thumb_fit.convert("RGBA")
        thumb_fit.putalpha(mask)
        image1.paste(thumb_fit, (img_x0, img_y0), thumb_fit)
        draw = ImageDraw.Draw(image1)

        # ---- Waveform bars overlapping the bottom of the thumbnail ----
        bar_count = 46
        bar_gap = 3
        bar_w = (img_w - (bar_count - 1) * bar_gap) / bar_count
        color_a = (255, 107, 157)   # pink
        color_b = (91, 143, 249)    # blue
        for i in range(bar_count):
            t = i / (bar_count - 1)
            h = 10 + int(36 * abs(((i * 37) % 23) / 23 - 0.5) * 2)
            bx0 = img_x0 + i * (bar_w + bar_gap)
            by1 = img_y1 - 6
            by0 = by1 - h
            color = _lerp_color(color_a, color_b, t)
            draw.rounded_rectangle(
                [(bx0, by0), (bx0 + bar_w, by1)],
                radius=bar_w / 2,
                fill=color + (210,),
            )

        # ---- Progress bar ----
        bar_x = widget_x + margin
        bar_y = img_y1 + 34
        bar_width = widget_width - 2 * margin
        progress = 0.3

        draw.rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + 4)], fill=(255, 255, 255, 60))
        draw.rectangle([(bar_x, bar_y), (bar_x + bar_width * progress, bar_y + 4)], fill="white")
        dot_x = bar_x + bar_width * progress
        draw.ellipse([(dot_x - 8, bar_y - 6), (dot_x + 8, bar_y + 10)], fill="white")

        # Time labels (elapsed / remaining, like "-2:07")
        total_seconds = _parse_duration(duration)
        elapsed_seconds = int(total_seconds * progress)
        remaining_seconds = total_seconds - elapsed_seconds
        time_y = bar_y + 18
        draw.text((bar_x, time_y), text=_format_time(elapsed_seconds), fill="#b3b3b3", font=font_time)
        remaining_text = f"-{_format_time(remaining_seconds)}"
        w_rem = get_text_width(remaining_text, font_time)
        draw.text((bar_x + bar_width - w_rem, time_y), text=remaining_text, fill="#b3b3b3", font=font_time)

        # ---- Playback controls: shuffle / prev / play / next / repeat ----
        controls_y = time_y + 55
        center_x = widget_x + widget_width // 2
        icon_color = "white"
        dim_color = "#8a8a8a"

        # Shuffle icon (far left)
        sh_x = bar_x + 20
        for dy in (-6, 6):
            draw.line([(sh_x, controls_y + dy), (sh_x + 26, controls_y - dy)], fill=dim_color, width=3)
        draw.polygon([(sh_x + 22, controls_y - 10), (sh_x + 30, controls_y - 6), (sh_x + 22, controls_y - 2)], fill=dim_color)
        draw.polygon([(sh_x + 22, controls_y + 10), (sh_x + 30, controls_y + 6), (sh_x + 22, controls_y + 2)], fill=dim_color)

        # Previous icon
        px = center_x - 110
        draw.polygon([(px + 16, controls_y - 18), (px - 6, controls_y), (px + 16, controls_y + 18)], fill=icon_color)
        draw.rectangle([(px - 14, controls_y - 18), (px - 8, controls_y + 18)], fill=icon_color)

        # Play icon (large centered circle)
        play_r = 38
        draw.ellipse(
            [(center_x - play_r, controls_y - play_r), (center_x + play_r, controls_y + play_r)],
            fill="white",
        )
        tri_off = 14
        draw.polygon(
            [(center_x - tri_off + 6, controls_y - 18),
             (center_x - tri_off + 6, controls_y + 18),
             (center_x + tri_off + 4, controls_y)],
            fill=(20, 18, 26),
        )

        # Next icon
        nx = center_x + 110
        draw.polygon([(nx - 16, controls_y - 18), (nx + 6, controls_y), (nx - 16, controls_y + 18)], fill=icon_color)
        draw.rectangle([(nx + 8, controls_y - 18), (nx + 14, controls_y + 18)], fill=icon_color)

        # Repeat icon (far right)
        rp_x = bar_x + bar_width - 46
        draw.arc([(rp_x - 16, controls_y - 16), (rp_x + 16, controls_y + 16)], start=30, end=300, fill=dim_color, width=3)
        draw.polygon([(rp_x + 14, controls_y - 18), (rp_x + 22, controls_y - 12), (rp_x + 12, controls_y - 8)], fill=dim_color)

        # ---- Volume row ----
        vol_y = controls_y + 70
        sp_x = bar_x
        draw.rectangle([(sp_x, vol_y - 6), (sp_x + 8, vol_y + 6)], fill=dim_color)
        draw.polygon([(sp_x + 8, vol_y - 6), (sp_x + 18, vol_y - 14), (sp_x + 18, vol_y + 14), (sp_x + 8, vol_y + 6)], fill=dim_color)
        draw.arc([(sp_x + 18, vol_y - 12), (sp_x + 30, vol_y + 12)], start=300, end=60, fill=dim_color, width=2)

        vol_bar_x = sp_x + 42
        vol_bar_width = bar_width - 42
        vol_progress = 0.55
        draw.rectangle([(vol_bar_x, vol_y - 2), (vol_bar_x + vol_bar_width, vol_y + 2)], fill=(255, 255, 255, 60))
        draw.rectangle([(vol_bar_x, vol_y - 2), (vol_bar_x + vol_bar_width * vol_progress, vol_y + 2)], fill="white")
        vdot_x = vol_bar_x + vol_bar_width * vol_progress
        draw.ellipse([(vdot_x - 7, vol_y - 7), (vdot_x + 7, vol_y + 7)], fill="white")

        try:
            os.remove(f"cache/thumb{videoid}.png")
        except Exception:
            pass

        file_name = f"cache/{videoid}.png"
        image1.convert("RGB").save(file_name)
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
    
