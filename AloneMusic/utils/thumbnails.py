# -----------------------------------------
# YOUTUBE MUSIC THUMBNAIL — FIXED 16:9
# NO CROP / NO STRETCH / WHITE PLAYER
# -----------------------------------------

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


# -----------------------------------------
# IMAGE RESIZE
# -----------------------------------------

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


# -----------------------------------------
# FONT
# -----------------------------------------

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            return ImageFont.load_default()


# -----------------------------------------
# TEXT WIDTH
# -----------------------------------------

def get_text_width(draw, text, font):
    try:
        return draw.textlength(text, font=font)
    except Exception:
        return draw.textbbox((0, 0), text, font=font)[2]


# -----------------------------------------
# TEXT WRAP
# -----------------------------------------

def fit_title(draw, title, font, max_width, max_lines=2):

    words = title.split()
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

            if len(lines) >= max_lines:
                break

    if current and len(lines) < max_lines:
        lines.append(current)

    if not lines:
        lines = ["Unknown Title"]

    if len(lines) == max_lines:

        used_words = " ".join(lines).split()

        if len(used_words) < len(words):
            last = lines[-1]

            if len(last) > 3:
                lines[-1] = last.rstrip() + "..."

    return lines[:max_lines]


# -----------------------------------------
# MAIN THUMBNAIL
# -----------------------------------------

async def get_thumb(videoid, user_name=None, next_title=None):

    os.makedirs("cache", exist_ok=True)

    file_name = f"cache/{videoid}.png"

    if os.path.isfile(file_name):
        return file_name

    thumb_file = f"cache/thumb_{videoid}.jpg"

    try:

        # -----------------------------------------
        # GET YOUTUBE VIDEO INFORMATION
        # -----------------------------------------

        url = f"https://www.youtube.com/watch?v={videoid}"

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
            return YOUTUBE_IMG_URL

        result = res["result"][0]

        # -----------------------------------------
        # TITLE
        # -----------------------------------------

        title = result.get(
            "title",
            "Unknown Song"
        )

        title = re.sub(
            r"\s+",
            " ",
            title
        ).strip()

        # -----------------------------------------
        # DURATION
        # -----------------------------------------

        duration = result.get(
            "duration",
            "0:00"
        )

        if not duration:
            duration = "0:00"

        # -----------------------------------------
        # THUMBNAIL
        # -----------------------------------------

        thumbnail = (
            f"https://i.ytimg.com/vi/"
            f"{videoid}/hqdefault.jpg"
        )

        # -----------------------------------------
        # DOWNLOAD THUMBNAIL
        # -----------------------------------------

        async with aiohttp.ClientSession() as session:

            async with session.get(
                thumbnail
            ) as resp:

                if resp.status != 200:
                    return YOUTUBE_IMG_URL

                data = await resp.read()

        async with aiofiles.open(
            thumb_file,
            "wb"
        ) as f:
            await f.write(data)

        # -----------------------------------------
        # OPEN ORIGINAL IMAGE
        # -----------------------------------------

        youtube = Image.open(
            thumb_file
        ).convert("RGB")

        # -----------------------------------------
        # CANVAS
        # -----------------------------------------

        canvas_w = 1280
        canvas_h = 720

        # -----------------------------------------
        # BACKGROUND
        # -----------------------------------------

        bg = Image.new(
            "RGB",
            (canvas_w, canvas_h),
            "#111111"
        )

        # Blurred background
        background = ImageOps.fit(
            youtube,
            (canvas_w, canvas_h),
            method=Image.Resampling.LANCZOS
        )

        background = background.filter(
            ImageFilter.GaussianBlur(35)
        )

        background = ImageEnhance.Brightness(
            background
        ).enhance(0.18)

        bg.paste(
            background,
            (0, 0)
        )

        # -----------------------------------------
        # PLAYER CARD
        # -----------------------------------------

        player_w = 1120
        player_h = 650

        player_x = (
            canvas_w - player_w
        ) // 2

        player_y = (
            canvas_h - player_h
        ) // 2

        overlay = Image.new(
            "RGBA",
            (canvas_w, canvas_h),
            (0, 0, 0, 0)
        )

        overlay_draw = ImageDraw.Draw(
            overlay
        )

        # White player
        overlay_draw.rounded_rectangle(
            [
                (
                    player_x,
                    player_y
                ),
                (
                    player_x + player_w,
                    player_y + player_h
                )
            ],
            radius=35,
            fill=(248, 248, 250, 255)
        )

        bg = Image.alpha_composite(
            bg.convert("RGBA"),
            overlay
        )

        draw = ImageDraw.Draw(bg)

        # -----------------------------------------
        # 16:9 THUMBNAIL AREA
        # -----------------------------------------

        image_w = player_w - 90

        # EXACT 16:9
        image_h = int(
            image_w * 9 / 16
        )

        image_x = player_x + 45
        image_y = player_y + 30

        # -----------------------------------------
        # NO CROP / NO STRETCH
        # -----------------------------------------

        # Thumbnail ko exact 16:9 box ke andar
        # contain kiya jayega.
        #
        # Agar image 16:9 hai -> full image visible.
        # Agar ratio different hai -> crop nahi hogi.

        youtube_thumb = ImageOps.contain(
            youtube,
            (
                image_w,
                image_h
            ),
            method=Image.Resampling.LANCZOS
        )

        # White 16:9 background
        thumb_bg = Image.new(
            "RGB",
            (
                image_w,
                image_h
            ),
            "white"
        )

        # Center image
        thumb_offset_x = (
            image_w - youtube_thumb.width
        ) // 2

        thumb_offset_y = (
            image_h - youtube_thumb.height
        ) // 2

        thumb_bg.paste(
            youtube_thumb,
            (
                thumb_offset_x,
                thumb_offset_y
            )
        )

        # -----------------------------------------
        # ROUNDED CORNERS
        # -----------------------------------------

        mask = Image.new(
            "L",
            (
                image_w,
                image_h
            ),
            0
        )

        mask_draw = ImageDraw.Draw(
            mask
        )

        mask_draw.rounded_rectangle(
            [
                (0, 0),
                (
                    image_w - 1,
                    image_h - 1
                )
            ],
            radius=25,
            fill=255
        )

        bg.paste(
            thumb_bg,
            (
                image_x,
                image_y
            ),
            mask
        )

        # -----------------------------------------
        # FONTS
        # -----------------------------------------

        font_title = get_font(
            "AloneMusic/assets/font.ttf",
            34
        )

        font_time = get_font(
            "AloneMusic/assets/font3.ttf",
            24
        )

        # -----------------------------------------
        # TITLE AREA
        # -----------------------------------------

        title_y = (
            image_y +
            image_h +
            28
        )

        max_title_width = (
            player_w - 100
        )

        title_lines = fit_title(
            draw,
            title,
            font_title,
            max_title_width,
            max_lines=2
        )

        # Center title
        line_height = 42

        for i, line in enumerate(
            title_lines
        ):

            text_width = get_text_width(
                draw,
                line,
                font_title
            )

            text_x = (
                canvas_w -
                text_width
            ) // 2

            draw.text(
                (
                    text_x,
                    title_y +
                    i * line_height
                ),
                line,
                fill="#111111",
                font=font_title
            )

        # -----------------------------------------
        # PROGRESS BAR
        # -----------------------------------------

        bar_x = player_x + 90

        bar_width = (
            player_w - 180
        )

        bar_y = (
            player_y +
            player_h -
            85
        )

        bar_height = 7

        # Background bar
        draw.rounded_rectangle(
            [
                (
                    bar_x,
                    bar_y
                ),
                (
                    bar_x + bar_width,
                    bar_y + bar_height
                )
            ],
            radius=4,
            fill="#aaaaaa"
        )

        # -----------------------------------------
        # PROGRESS
        # -----------------------------------------

        progress = 0.30

        progress_width = (
            bar_width * progress
        )

        draw.rounded_rectangle(
            [
                (
                    bar_x,
                    bar_y
                ),
                (
                    bar_x + progress_width,
                    bar_y + bar_height
                )
            ],
            radius=4,
            fill="#20b34b"
        )

        # -----------------------------------------
        # SLIDER DOT
        # -----------------------------------------

        dot_x = (
            bar_x +
            progress_width
        )

        dot_y = (
            bar_y +
            bar_height // 2
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
            fill="#20b34b"
        )

        # -----------------------------------------
        # TIME — LEFT
        # -----------------------------------------

        time_y = bar_y + 22

        draw.text(
            (
                bar_x,
                time_y
            ),
            "00:00",
            fill="#111111",
            font=font_time
        )

        # -----------------------------------------
        # TIME — RIGHT
        # -----------------------------------------

        duration_width = get_text_width(
            draw,
            duration,
            font_time
        )

        draw.text(
            (
                bar_x +
                bar_width -
                duration_width,
                time_y
            ),
            duration,
            fill="#111111",
            font=font_time
        )

        # -----------------------------------------
        # WATERMARK
        # -----------------------------------------

        watermark_font = get_font(
            "AloneMusic/assets/font2.ttf",
            28
        )

        watermark = "Meera Music"

        watermark_width = get_text_width(
            draw,
            watermark,
            watermark_font
        )

        draw.text(
            (
                canvas_w -
                watermark_width -
                40,
                25
            ),
            watermark,
            fill=(255, 255, 255, 230),
            font=watermark_font
        )

        # -----------------------------------------
        # SAVE
        # -----------------------------------------

        bg = bg.convert("RGB")

        bg.save(
            file_name,
            "PNG",
            quality=95
        )

        # -----------------------------------------
        # DELETE TEMP FILE
        # -----------------------------------------

        try:
            os.remove(thumb_file)
        except Exception:
            pass

        return file_name

    except Exception as e:

        print(
            "Thumbnail Error:",
            e
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


# -----------------------------------------
# GET ORIGINAL YOUTUBE THUMBNAIL
# -----------------------------------------

async def get_qthumb(vidid):

    try:

        # Direct YouTube 16:9 thumbnail
        return (
            f"https://i.ytimg.com/vi/"
            f"{vidid}/hqdefault.jpg"
        )

    except Exception as e:

        print(
            "QThumb Error:",
            e
        )

        return YOUTUBE_IMG_URL
