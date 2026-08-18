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
                channel = "Unknown Artist"

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        youtube = Image.open(f"cache/thumb{videoid}.png")

        # Background: Blurred and darkened version of the thumbnail
        image1 = changeImageSize(1280, 720, youtube)
        image1 = image1.filter(ImageFilter.GaussianBlur(50))
        image1 = ImageEnhance.Brightness(image1).enhance(0.15)
        
        # Player Widget Dimensions (Mobile Notification Style)
        widget_width = 1100
        widget_height = 400
        widget_x = (1280 - widget_width) // 2
        widget_y = (720 - widget_height) // 2
        
        # Create Widget Overlay (semi-transparent dark background)
        overlay = Image.new('RGBA', (1280, 720), (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)
        
        # Main Widget
        draw_overlay.rounded_rectangle(
            [(widget_x, widget_y), (widget_x + widget_width, widget_y + widget_height)],
            radius=60,
            fill=(15, 15, 15, 250)
        )
        
        # Media output pill
        pill_w, pill_h = 240, 60
        pill_x = widget_x + widget_width - pill_w - 40
        pill_y = widget_y + 50
        draw_overlay.rounded_rectangle([(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)], radius=30, fill=(255, 255, 255, 40))
        
        # Progress Bar Background Line
        bar_x = widget_x + 50
        bar_y = widget_y + widget_height - 80
        bar_width = widget_width - 100
        bar_bg_height = 4
        draw_overlay.rectangle([(bar_x, bar_y + 2), (bar_x + bar_width, bar_y + 2 + bar_bg_height)], fill=(255, 255, 255, 40))

        image1 = image1.convert('RGBA')
        image1 = Image.alpha_composite(image1, overlay)
        draw = ImageDraw.Draw(image1)
        
        # Album Art (Square with rounded corners) - Mobile Notification Style
        album_size = 140
        album_x = widget_x + 40
        album_y = widget_y + 40
        
        # Use ImageOps.fit to crop to square without squashing
        youtube_thumb = ImageOps.fit(youtube, (album_size, album_size), centering=(0.5, 0.5))
        mask = Image.new("L", (album_size, album_size), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle([(0, 0), (album_size, album_size)], radius=20, fill=255)
        youtube_thumb.putalpha(mask)
        image1.paste(youtube_thumb, (album_x, album_y), youtube_thumb)
        
        # Load Fonts
        def get_font(path, size):
            try:
                return ImageFont.truetype(path, size)
            except:
                try:
                    return ImageFont.truetype("arial.ttf", size)
                except:
                    return ImageFont.load_default()

        font_title = get_font("AloneMusic/assets/font.ttf", 60)
        font_artist = get_font("AloneMusic/assets/font2.ttf", 35)
        font_label = get_font("AloneMusic/assets/font2.ttf", 30)
        font_time = get_font("AloneMusic/assets/font3.ttf", 25)
        font_watermark = get_font("AloneMusic/assets/font2.ttf", 30)

        def get_text_width(text, font):
            if hasattr(draw, "textlength"):
                return draw.textlength(text, font=font)
            else:
                return draw.textsize(text, font=font)[0]

        # Draw Spotify-style icon and "This phone" label
        label_x = album_x + album_size + 40
        label_y = album_y + 10
        
        # Draw Spotify Circle
        draw.ellipse([(label_x, label_y), (label_x + 35, label_y + 35)], fill="white")
        # Draw Three Curved Lines inside (Spotify style)
        for i in range(3):
            draw.arc([(label_x+6, label_y+6+i*7), (label_x+29, label_y+14+i*7)], start=190, end=350, fill="black", width=3)
            
        draw.text((label_x + 50, label_y + 2), text="This phone", fill="white", font=font_label)

        # Draw Title and Artist
        text_x = label_x
        text_y_base = label_y + 80
        
        # Truncate title if too long
        display_title = title
        if len(display_title) > 35:
            display_title = display_title[:32] + "..."
            
        draw.text((text_x, text_y_base - 10), text=display_title, fill="white", font=font_title)
        draw.text((text_x, text_y_base + 75), text=channel, fill="#b3b3b3", font=font_artist)
        
        # Draw Media Controls (Centered and Enlarged)
        controls_y = widget_y + 265
        icon_color = "white"
        
        # Heart Icon (Standard Heart Shape - refined)
        hx, hy = widget_x + 340, controls_y
        draw.ellipse([(hx-18, hy-18), (hx+2, hy+2)], fill=icon_color)
        draw.ellipse([(hx-2, hy-18), (hx+18, hy+2)], fill=icon_color)
        draw.polygon([(hx-18, hy-3), (hx+18, hy-3), (hx, hy+20)], fill=icon_color)
        
        # Prev Icon
        px, py = widget_x + 480, controls_y
        draw.polygon([(px+18, py-20), (px-6, py), (px+18, py+20)], fill=icon_color)
        draw.rectangle([(px-16, py-20), (px-10, py+20)], fill=icon_color)
        
        # Pause Icon
        pax, pay = widget_x + 620, controls_y
        draw.rectangle([(pax-14, pay-22), (pax-4, pay+22)], fill=icon_color)
        draw.rectangle([(pax+4, pay-22), (pax+14, pay+22)], fill=icon_color)
        
        # Next Icon
        nx, ny = widget_x + 760, controls_y
        draw.polygon([(nx-18, ny-20), (nx+6, ny), (nx-18, ny+20)], fill=icon_color)
        draw.rectangle([(nx+10, ny-20), (nx+16, ny+20)], fill=icon_color)
        
        # Media output pill text
        label_mo = "Media output"
        w_mo = get_text_width(label_mo, font_label)
        draw.text((pill_x + (pill_w - w_mo)//2, pill_y + (pill_h - 45)//2), text=label_mo, fill="white", font=font_label)
        
        # Progress Bar
        bar_x = widget_x + 50
        bar_y = widget_y + widget_height - 80
        bar_width = widget_width - 100
        bar_fg_height = 8
        
        # Progress (Fixed at 20% to match reference exactly for verification)
        progress = 0.20
        draw.rectangle([(bar_x, bar_y), (bar_x + bar_width * progress, bar_y + bar_fg_height)], fill="white")
        # Slider Dot
        dot_x = bar_x + bar_width * progress
        draw.ellipse([(dot_x - 14, bar_y + bar_fg_height//2 - 14), (dot_x + 14, bar_y + bar_fg_height//2 + 14)], fill="white")
        
        # Timestamps
        draw.text((bar_x, bar_y + 20), text="00:00", fill="#b3b3b3", font=font_time)
        w_dur = get_text_width(duration, font_time)
        draw.text((bar_x + bar_width - w_dur, bar_y + 20), text=duration, fill="#b3b3b3", font=font_time)
        
        # Watermark
        draw.text((1280 - 180, 40), text="Meera Music", fill=(255, 255, 255, 150), font=font_watermark)

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
        
