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
# FONT
# ==========================================================

def get_font(size, bold=False):

    if bold:
        names = [
            "font.ttf",
            "DejaVuSans-Bold.ttf",
            "LiberationSans-Bold.ttf",
        ]
    else:
        names = [
            "font2.ttf",
            "DejaVuSans.ttf",
            "LiberationSans-Regular.ttf",
        ]

    paths = []

    for name in names:
        paths.extend([
            os.path.join(FONT_DIR, name),
            os.path.join("assets", name),
            name,
        ])

    for path in paths:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception:
            pass

    fallback = (
        "/usr/share/fonts/truetype/dejavu/"
        + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
    )

    try:
        return ImageFont.truetype(fallback, size)
    except Exception:
        return ImageFont.load_default()


# ==========================================================
# TEXT WIDTH
# ==========================================================

def text_width(draw, text, font):
    try:
        return draw.textlength(text, font=font)
    except Exception:
        box = draw.textbbox(
            (0, 0),
            text,
            font=font
        )
        return box[2] - box[0]


# ==========================================================
# TRUNCATE
# ==========================================================

def shorten(text, limit):
    text = str(text).strip()

    if len(text) <= limit:
        return text

    return text[:limit - 3] + "..."


# ==========================================================
# DOWNLOAD
# ==========================================================

async def download_image(url, path):

    try:

        timeout = aiohttp.ClientTimeout(
            total=20
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(url) as response:

                if response.status != 200:
                    return False

                data = await response.read()

                async with aiofiles.open(
                    path,
                    "wb"
                ) as file:

                    await file.write(data)

        return True

    except Exception as e:
        print(
            f"Download Error: {e}"
        )
        return False


# ==========================================================
# ROUNDED IMAGE
# ==========================================================

def rounded_image(
    image,
    size,
    radius=30
):

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
# GET THUMB
# ==========================================================

async def get_thumb(
    videoid,
    user_name=None,
    next_title=None
):

    output = f"{CACHE_DIR}/{videoid}.png"

    if os.path.isfile(output):
        return output

    temp = f"{CACHE_DIR}/temp_{videoid}.jpg"

    try:

        # ==================================================
        # YOUTUBE
        # ==================================================

        url = (
            f"https://www.youtube.com/"
            f"watch?v={videoid}"
        )

        results = VideosSearch(
            url,
            limit=1
        )

        data = await results.next()

        if not data:
            return YOUTUBE_IMG_URL

        items = data.get(
            "result",
            []
        )

        if not items:
            return YOUTUBE_IMG_URL

        result = items[0]

        # ==================================================
        # TITLE
        # ==================================================

        title = result.get(
            "title",
            "Unknown Song"
        )

        title = re.sub(
            r"\s+",
            " ",
            title
        ).strip()

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
        # DURATION
        # ==================================================

        duration = result.get(
            "duration",
            "0:00"
        )

        if not duration:
            duration = "0:00"

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

        if not await download_image(
            thumbnail,
            temp
        ):
            return YOUTUBE_IMG_URL

        youtube = Image.open(
            temp
        ).convert("RGB")

        # ==================================================
        # BACKGROUND
        # ==================================================

        background = ImageOps.fit(
            youtube,
            (WIDTH, HEIGHT),
            method=Image.Resampling.LANCZOS
        )

        background = background.filter(
            ImageFilter.GaussianBlur(35)
        )

        background = ImageEnhance.Brightness(
            background
        ).enhance(0.22)

        background = ImageEnhance.Contrast(
            background
        ).enhance(0.75)

        background = background.convert(
            "RGBA"
        )

        # Dark layer
        dark = Image.new(
            "RGBA",
            (WIDTH, HEIGHT),
            (0, 0, 0, 115)
        )

        background = Image.alpha_composite(
            background,
            dark
        )

        draw = ImageDraw.Draw(
            background
        )

        # ==================================================
        # MAIN BLACK PLAYER CARD
        # ==================================================

        card_x = 55
        card_y = 85
        card_w = 1170
        card_h = 600

        # Shadow
        shadow = Image.new(
            "RGBA",
            (card_w + 40, card_h + 40),
            (0, 0, 0, 0)
        )

        shadow_draw = ImageDraw.Draw(
            shadow
        )

        shadow_draw.rounded_rectangle(
            (
                20,
                20,
                card_w + 10,
                card_h + 10
            ),
            radius=55,
            fill=(0, 0, 0, 180)
        )

        shadow = shadow.filter(
            ImageFilter.GaussianBlur(20)
        )

        background.alpha_composite(
            shadow,
            (
                card_x - 10,
                card_y - 5
            )
        )

        # Main card
        draw.rounded_rectangle(
            (
                card_x,
                card_y,
                card_x + card_w,
                card_y + card_h
            ),
            radius=55,
            fill=(8, 10, 10, 235)
        )

        # ==================================================
        # ALBUM ART
        # ==================================================

        album_size = 500

        album_x = 85
        album_y = 140

        album = rounded_image(
            youtube,
            album_size,
            radius=30
        )

        background.alpha_composite(
            album,
            (
                album_x,
                album_y
            )
        )

        # ==================================================
        # ALBUM DARK OVERLAY
        # ==================================================

        album_overlay = Image.new(
            "RGBA",
            (
                album_size,
                album_size
            ),
            (0, 0, 0, 65)
        )

        album_mask = Image.new(
            "L",
            (
                album_size,
                album_size
            ),
            0
        )

        md = ImageDraw.Draw(
            album_mask
        )

        md.rounded_rectangle(
            (
                0,
                0,
                album_size,
                album_size
            ),
            radius=30,
            fill=255
        )

        album_overlay.putalpha(
            album_mask
        )

        background.alpha_composite(
            album_overlay,
            (
                album_x,
                album_y
            )
        )

        # ==================================================
        # ALBUM TITLE
        # ==================================================

        album_font = get_font(
            22
        )

        album_text = shorten(
            title.upper(),
            25
        )

        bbox = draw.textbbox(
            (0, 0),
            album_text,
            font=album_font
        )

        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        draw.text(
            (
                album_x +
                (album_size - tw) / 2,
                album_y +
                (album_size - th) / 2
            ),
            album_text,
            font=album_font,
            fill="white"
        )

        # ==================================================
        # RIGHT SECTION
        # ==================================================

        right_x = 620

        title_font = get_font(
            32,
            bold=True
        )

        artist_font = get_font(
            27
        )

        time_font = get_font(
            18
        )

        small_font = get_font(
            18,
            bold=True
        )

        # ==================================================
        # TITLE
        # ==================================================

        display_title = shorten(
            title,
            25
        )

        draw.text(
            (
                right_x,
                142
            ),
            display_title,
            font=title_font,
            fill="white"
        )

        # ==================================================
        # ARTIST
        # ==================================================

        display_artist = shorten(
            channel,
            28
        )

        draw.text(
            (
                right_x,
                180
            ),
            display_artist,
            font=artist_font,
            fill=(170, 170, 175)
        )

        # ==================================================
        # MENU BUTTON
        # ==================================================

        menu_x = 1150
        menu_y = 145

        draw.ellipse(
            (
                menu_x,
                menu_y,
                menu_x + 55,
                menu_y + 55
            ),
            fill=(80, 80, 82, 190)
        )

        menu_font = get_font(
            28,
            bold=True
        )

        draw.text(
            (
                menu_x + 15,
                menu_y + 4
            ),
            "⋯",
            font=menu_font,
            fill="white"
        )

        # ==================================================
        # PROGRESS BAR
        # ==================================================

        bar_x = right_x
        bar_y = 255
        bar_w = 560
        bar_h = 15

        # Background
        draw.rounded_rectangle(
            (
                bar_x,
                bar_y,
                bar_x + bar_w,
                bar_y + bar_h
            ),
            radius=8,
            fill=(85, 85, 88, 210)
        )

        # Progress
        progress = 0.62

        progress_w = int(
            bar_w * progress
        )

        draw.rounded_rectangle(
            (
                bar_x,
                bar_y,
                bar_x + progress_w,
                bar_y + bar_h
            ),
            radius=8,
            fill=(225, 225, 228)
        )

        # ==================================================
        # PROGRESS DOT
        # ==================================================

        dot_x = bar_x + progress_w
        dot_y = bar_y + bar_h // 2

        draw.ellipse(
            (
                dot_x - 11,
                dot_y - 11,
                dot_x + 11,
                dot_y + 11
            ),
            fill="white"
        )

        # ==================================================
        # TIME
        # ==================================================

        draw.text(
            (
                right_x,
                290
            ),
            "3:23",
            font=time_font,
            fill=(205, 205, 208)
        )

        remaining = "-1:57"

        rw = text_width(
            draw,
            remaining,
            time_font
        )

        draw.text(
            (
                right_x +
                bar_w -
                rw,
                290
            ),
            remaining,
            font=time_font,
            fill=(205, 205, 208)
        )

        # ==================================================
        # PREVIOUS BUTTON
        # ==================================================

        prev_x = 760
        prev_y = 420

        draw.polygon(
            [
                (prev_x, prev_y),
                (prev_x + 38, prev_y - 28),
                (prev_x + 38, prev_y + 28)
            ],
            fill="white"
        )

        draw.polygon(
            [
                (prev_x + 38, prev_y),
                (prev_x + 76, prev_y - 28),
                (prev_x + 76, prev_y + 28)
            ],
            fill="white"
        )

        # ==================================================
        # PAUSE
        # ==================================================

        pause_x = 900

        draw.rounded_rectangle(
            (
                pause_x,
                prev_y - 35,
                pause_x + 18,
                prev_y + 35
            ),
            radius=4,
            fill="white"
        )

        draw.rounded_rectangle(
            (
                pause_x + 30,
                prev_y - 35,
                pause_x + 48,
                prev_y + 35
            ),
            radius=4,
            fill="white"
        )

        # ==================================================
        # NEXT
        # ==================================================

        next_x = 1045

        draw.polygon(
            [
                (next_x, prev_y - 28),
                (next_x + 38, prev_y),
                (next_x, prev_y + 28)
            ],
            fill="white"
        )

        draw.polygon(
            [
                (next_x + 38, prev_y - 28),
                (next_x + 76, prev_y),
                (next_x + 38, prev_y + 28)
            ],
            fill="white"
        )

        # ==================================================
        # VOLUME ICON
        # ==================================================

        volume_font = get_font(
            22,
            bold=True
        )

        draw.text(
            (
                right_x,
                585
            ),
            "◀",
            font=volume_font,
            fill=(180, 180, 185)
        )

        # ==================================================
        # VOLUME BAR
        # ==================================================

        volume_x = right_x + 45
        volume_y = 600
        volume_w = 450

        draw.rounded_rectangle(
            (
                volume_x,
                volume_y,
                volume_x + volume_w,
                volume_y + 14
            ),
            radius=7,
            fill=(80, 80, 83)
        )

        volume_progress = 0.48

        draw.rounded_rectangle(
            (
                volume_x,
                volume_y,
                volume_x +
                int(volume_w * volume_progress),
                volume_y + 14
            ),
            radius=7,
            fill=(220, 220, 223)
        )

        # Volume icon right
        draw.text(
            (
                volume_x + volume_w + 25,
                585
            ),
            ")))",
            font=volume_font,
            fill=(180, 180, 185)
        )

        # ==================================================
        # OUTPUT BUTTON
        # ==================================================

        output_text = "◉  iPhone"

        output_font = get_font(
            20
        )

        output_w = text_width(
            draw,
            output_text,
            output_font
        )

        pill_w = int(
            output_w + 45
        )

        pill_h = 55

        pill_x = 850
        pill_y = 650

        draw.rounded_rectangle(
            (
                pill_x,
                pill_y,
                pill_x + pill_w,
                pill_y + pill_h
            ),
            radius=28,
            fill=(65, 65, 68, 210)
        )

        draw.text(
            (
                pill_x + 22,
                pill_y + 13
            ),
            output_text,
            font=output_font,
            fill="white"
        )

        # ==================================================
        # BOTTOM HOME INDICATOR
        # ==================================================

        draw.rounded_rectangle(
            (
                525,
                835 - 5,
                755,
                845
            ),
            radius=5,
            fill="white"
        )

        # ==================================================
        # SAVE
        # ==================================================

        background = background.convert(
            "RGB"
        )

        background.save(
            output,
            "PNG",
            optimize=True
        )

        # ==================================================
        # CLEAN TEMP
        # ==================================================

        try:
            os.remove(temp)
        except Exception:
            pass

        return output

    except Exception as e:

        print(
            f"Thumbnail Error: {e}"
        )

        try:
            if os.path.exists(temp):
                os.remove(temp)
        except Exception:
            pass

        return YOUTUBE_IMG_URL


# ==========================================================
# GET YOUTUBE THUMBNAIL
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

        items = data.get(
            "result",
            []
        )

        if not items:
            return YOUTUBE_IMG_URL

        thumbnails = items[0].get(
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
