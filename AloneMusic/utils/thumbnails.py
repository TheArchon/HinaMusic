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
        ]
    else:
        names = [
            "font2.ttf",
            "font3.ttf",
            "DejaVuSans.ttf",
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
            if os.path.isfile(path):
                return ImageFont.truetype(
                    path,
                    size
                )
        except Exception:
            pass

    system_fonts = [
        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans-Bold.ttf",

        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans.ttf",
    ]

    for path in system_fonts:
        try:
            if os.path.isfile(path):
                return ImageFont.truetype(
                    path,
                    size
                )
        except Exception:
            pass

    return ImageFont.load_default()


# ==========================================================
# TEXT WIDTH
# ==========================================================

def text_width(draw, text, font):

    try:
        return draw.textlength(
            text,
            font=font
        )
    except Exception:

        box = draw.textbbox(
            (0, 0),
            text,
            font=font
        )

        return box[2] - box[0]


# ==========================================================
# SHORT TEXT
# ==========================================================

def shorten(text, limit):

    text = str(
        text or ""
    ).strip()

    if not text:
        return "Unknown Song"

    if len(text) <= limit:
        return text

    return text[:limit - 3] + "..."


# ==========================================================
# DOWNLOAD IMAGE
# ==========================================================

async def download_image(url, path):

    try:

        timeout = aiohttp.ClientTimeout(
            total=20
        )

        headers = {
            "User-Agent":
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
        }

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers
        ) as session:

            async with session.get(
                url
            ) as response:

                if response.status != 200:
                    return False

                data = await response.read()

                if not data:
                    return False

                async with aiofiles.open(
                    path,
                    "wb"
                ) as file:

                    await file.write(data)

        return True

    except Exception as e:

        print(
            f"Thumbnail download error: {e}"
        )

        return False


# ==========================================================
# GET FULL YOUTUBE THUMBNAIL
# ==========================================================

async def get_youtube_thumbnail(
    videoid,
    fallback=None
):

    temp = os.path.join(
        CACHE_DIR,
        f"thumb_{videoid}.jpg"
    )

    urls = [

        # Best quality
        f"https://i.ytimg.com/vi/"
        f"{videoid}/maxresdefault.jpg",

        # Fallbacks
        f"https://i.ytimg.com/vi/"
        f"{videoid}/sddefault.jpg",

        f"https://i.ytimg.com/vi/"
        f"{videoid}/hqdefault.jpg",

        f"https://i.ytimg.com/vi/"
        f"{videoid}/mqdefault.jpg",
    ]

    if fallback:
        urls.append(
            fallback.split("?")[0]
        )

    for url in urls:

        try:

            success = await download_image(
                url,
                temp
            )

            if not success:
                continue

            image = Image.open(
                temp
            ).convert("RGB")

            if image.width < 100:
                continue

            if image.height < 100:
                continue

            # Check black/invalid image
            check = image.resize(
                (1, 1)
            )

            pixel = check.getpixel(
                (0, 0)
            )

            if sum(pixel) < 10:
                continue

            return image

        except Exception as e:

            print(
                f"Thumbnail check error: {e}"
            )

            continue

    return None


# ==========================================================
# FULL 16:9 IMAGE
# ==========================================================

def make_full_thumbnail(
    image,
    width,
    height,
    radius=25
):

    image = image.convert("RGB")

    # IMPORTANT:
    # Do NOT use ImageOps.fit()
    # because it crops YouTube image.

    ratio = min(
        width / image.width,
        height / image.height
    )

    new_width = int(
        image.width * ratio
    )

    new_height = int(
        image.height * ratio
    )

    image = image.resize(
        (
            new_width,
            new_height
        ),
        Image.Resampling.LANCZOS
    )

    # Dark canvas
    canvas = Image.new(
        "RGB",
        (
            width,
            height
        ),
        (5, 5, 5)
    )

    x = (
        width - new_width
    ) // 2

    y = (
        height - new_height
    ) // 2

    canvas.paste(
        image,
        (
            x,
            y
        )
    )

    # Rounded mask
    mask = Image.new(
        "L",
        (
            width,
            height
        ),
        0
    )

    mask_draw = ImageDraw.Draw(
        mask
    )

    mask_draw.rounded_rectangle(
        (
            0,
            0,
            width,
            height
        ),
        radius=radius,
        fill=255
    )

    result = Image.new(
        "RGBA",
        (
            width,
            height
        ),
        (0, 0, 0, 0)
    )

    result.paste(
        canvas,
        (0, 0),
        mask
    )

    return result


# ==========================================================
# MAIN THUMBNAIL
# ==========================================================

async def get_thumb(
    videoid,
    user_name=None,
    next_title=None
):

    output_file = os.path.join(
        CACHE_DIR,
        f"{videoid}.png"
    )

    # ======================================================
    # CACHE
    # ======================================================

    if os.path.isfile(output_file):

        try:

            check = Image.open(
                output_file
            )

            if (
                check.width >= 1000
                and check.height >= 500
            ):
                return output_file

        except Exception:
            pass

    try:

        # ==================================================
        # SEARCH YOUTUBE
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

        result_list = data.get(
            "result",
            []
        )

        if not result_list:
            return YOUTUBE_IMG_URL

        result = result_list[0]

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
            str(title)
        ).strip()

        if not title:
            title = "Unknown Song"

        # ==================================================
        # CHANNEL
        # ==================================================

        try:

            channel_data = result.get(
                "channel",
                {}
            )

            channel = channel_data.get(
                "name",
                "Unknown Artist"
            )

        except Exception:

            channel = "Unknown Artist"

        channel = str(
            channel or "Unknown Artist"
        ).strip()

        # ==================================================
        # DURATION
        # ==================================================

        duration = result.get(
            "duration",
            "0:00"
        )

        if not duration:
            duration = "0:00"

        duration = str(
            duration
        )

        # ==================================================
        # FALLBACK THUMBNAIL
        # ==================================================

        fallback = None

        try:

            thumbnails = result.get(
                "thumbnails",
                []
            )

            if thumbnails:

                fallback = thumbnails[-1].get(
                    "url"
                )

        except Exception:

            fallback = None

        # ==================================================
        # GET YOUTUBE IMAGE
        # ==================================================

        youtube = await get_youtube_thumbnail(
            videoid,
            fallback
        )

        if youtube is None:

            print(
                f"Thumbnail not found: {videoid}"
            )

            return YOUTUBE_IMG_URL

        # ==================================================
        # BACKGROUND
        # ==================================================

        background = youtube.resize(
            (
                WIDTH,
                HEIGHT
            ),
            Image.Resampling.LANCZOS
        )

        background = background.filter(
            ImageFilter.GaussianBlur(45)
        )

        background = ImageEnhance.Brightness(
            background
        ).enhance(0.15)

        background = ImageEnhance.Contrast(
            background
        ).enhance(0.70)

        background = background.convert(
            "RGBA"
        )

        # Dark overlay
        overlay = Image.new(
            "RGBA",
            (
                WIDTH,
                HEIGHT
            ),
            (0, 0, 0, 130)
        )

        background = Image.alpha_composite(
            background,
            overlay
        )

        draw = ImageDraw.Draw(
            background
        )

        # ==================================================
        # MAIN CARD
        # ==================================================

        card_x = 55
        card_y = 85

        card_w = 1170
        card_h = 600

        # Shadow
        shadow = Image.new(
            "RGBA",
            (
                card_w + 50,
                card_h + 50
            ),
            (0, 0, 0, 0)
        )

        shadow_draw = ImageDraw.Draw(
            shadow
        )

        shadow_draw.rounded_rectangle(
            (
                15,
                15,
                card_w + 15,
                card_h + 15
            ),
            radius=55,
            fill=(0, 0, 0, 180)
        )

        shadow = shadow.filter(
            ImageFilter.GaussianBlur(18)
        )

        background.alpha_composite(
            shadow,
            (
                card_x - 5,
                card_y - 5
            )
        )

        # Card
        draw.rounded_rectangle(
            (
                card_x,
                card_y,
                card_x + card_w,
                card_y + card_h
            ),
            radius=55,
            fill=(5, 7, 7, 245)
        )

        # ==================================================
        # FULL YOUTUBE PICTURE
        # ==================================================

        # 16:9 size
        album_w = 560
        album_h = 315

        album_x = 85

        # Center vertically
        album_y = (
            card_y +
            (card_h - album_h) // 2
        )

        # Picture shadow
        picture_shadow = Image.new(
            "RGBA",
            (
                album_w + 30,
                album_h + 30
            ),
            (0, 0, 0, 0)
        )

        picture_shadow_draw = ImageDraw.Draw(
            picture_shadow
        )

        picture_shadow_draw.rounded_rectangle(
            (
                12,
                12,
                album_w + 12,
                album_h + 12
            ),
            radius=28,
            fill=(0, 0, 0, 180)
        )

        picture_shadow = picture_shadow.filter(
            ImageFilter.GaussianBlur(12)
        )

        background.alpha_composite(
            picture_shadow,
            (
                album_x - 5,
                album_y - 3
            )
        )

        # FULL IMAGE
        album = make_full_thumbnail(
            youtube,
            album_w,
            album_h,
            radius=28
        )

        background.alpha_composite(
            album,
            (
                album_x,
                album_y
            )
        )

        # ==================================================
        # RIGHT SIDE
        # ==================================================

        right_x = 700

        # ==================================================
        # FONTS
        # ==================================================

        title_font = get_font(
            30,
            bold=True
        )

        artist_font = get_font(
            25
        )

        time_font = get_font(
            17
        )

        output_font = get_font(
            20
        )

        # ==================================================
        # TITLE
        # ==================================================

        display_title = shorten(
            title,
            30
        )

        draw.text(
            (
                right_x,
                150
            ),
            display_title,
            font=title_font,
            fill="white"
        )

        # ==================================================
        # ARTIST
        # ==================================================

        display_channel = shorten(
            channel,
            25
        )

        draw.text(
            (
                right_x,
                190
            ),
            display_channel,
            font=artist_font,
            fill=(175, 175, 180)
        )

        # ==================================================
        # MENU
        # ==================================================

        menu_x = 1150
        menu_y = 145
        menu_size = 52

        draw.ellipse(
            (
                menu_x,
                menu_y,
                menu_x + menu_size,
                menu_y + menu_size
            ),
            fill=(80, 80, 83)
        )

        menu_font = get_font(
            26,
            bold=True
        )

        draw.text(
            (
                menu_x + 13,
                menu_y + 2
            ),
            "⋯",
            font=menu_font,
            fill="white"
        )

        # ==================================================
        # PROGRESS
        # ==================================================

        bar_x = right_x
        bar_y = 270

        bar_w = 535
        bar_h = 13

        draw.rounded_rectangle(
            (
                bar_x,
                bar_y,
                bar_x + bar_w,
                bar_y + bar_h
            ),
            radius=7,
            fill=(70, 70, 73)
        )

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
            radius=7,
            fill=(240, 240, 242)
        )

        # Slider
        dot_x = (
            bar_x +
            progress_w
        )

        dot_y = (
            bar_y +
            bar_h // 2
        )

        draw.ellipse(
            (
                dot_x - 12,
                dot_y - 12,
                dot_x + 12,
                dot_y + 12
            ),
            fill="white"
        )

        # ==================================================
        # TIME
        # ==================================================

        draw.text(
            (
                bar_x,
                302
            ),
            "0:00",
            font=time_font,
            fill=(205, 205, 210)
        )

        duration_text = duration

        duration_w = text_width(
            draw,
            duration_text,
            time_font
        )

        draw.text(
            (
                bar_x +
                bar_w -
                duration_w,
                302
            ),
            duration_text,
            font=time_font,
            fill=(205, 205, 210)
        )

        # ==================================================
        # CONTROLS
        # ==================================================

        control_y = 500

        # --------------------------------------------------
        # PREVIOUS
        # --------------------------------------------------

        prev_x = 820

        draw.polygon(
            [
                (
                    prev_x,
                    control_y
                ),
                (
                    prev_x + 38,
                    control_y - 30
                ),
                (
                    prev_x + 38,
                    control_y + 30
                )
            ],
            fill="white"
        )

        draw.polygon(
            [
                (
                    prev_x + 38,
                    control_y
                ),
                (
                    prev_x + 78,
                    control_y - 30
                ),
                (
                    prev_x + 78,
                    control_y + 30
                )
            ],
            fill="white"
        )

        # --------------------------------------------------
        # PAUSE
        # --------------------------------------------------

        pause_x = 955

        draw.rounded_rectangle(
            (
                pause_x,
                control_y - 38,
                pause_x + 18,
                control_y + 38
            ),
            radius=5,
            fill="white"
        )

        draw.rounded_rectangle(
            (
                pause_x + 30,
                control_y - 38,
                pause_x + 48,
                control_y + 38
            ),
            radius=5,
            fill="white"
        )

        # --------------------------------------------------
        # NEXT
        # --------------------------------------------------

        next_x = 1085

        draw.polygon(
            [
                (
                    next_x,
                    control_y - 30
                ),
                (
                    next_x + 38,
                    control_y
                ),
                (
                    next_x,
                    control_y + 30
                )
            ],
            fill="white"
        )

        draw.polygon(
            [
                (
                    next_x + 38,
                    control_y - 30
                ),
                (
                    next_x + 78,
                    control_y
                ),
                (
                    next_x + 38,
                    control_y + 30
                )
            ],
            fill="white"
        )

        # ==================================================
        # VOLUME
        # ==================================================

        volume_y = 610

        # Speaker left
        draw.text(
            (
                right_x - 3,
                volume_y - 17
            ),
            "◀",
            font=artist_font,
            fill=(175, 175, 180)
        )

        volume_x = right_x + 45
        volume_w = 440
        volume_h = 12

        draw.rounded_rectangle(
            (
                volume_x,
                volume_y,
                volume_x + volume_w,
                volume_y + volume_h
            ),
            radius=6,
            fill=(70, 70, 73)
        )

        volume_progress = 0.48

        volume_w2 = int(
            volume_w *
            volume_progress
        )

        draw.rounded_rectangle(
            (
                volume_x,
                volume_y,
                volume_x + volume_w2,
                volume_y + volume_h
            ),
            radius=6,
            fill=(230, 230, 233)
        )

        # Speaker right
        draw.text(
            (
                volume_x +
                volume_w +
                20,
                volume_y - 17
            ),
            ")))",
            font=artist_font,
            fill=(175, 175, 180)
        )

        # ==================================================
        # IPHONE OUTPUT
        # ==================================================

        output_text = "◉  iPhone"

        output_w = text_width(
            draw,
            output_text,
            output_font
        )

        pill_w = int(
            output_w + 48
        )

        pill_h = 54

        pill_x = 890
        pill_y = 650

        draw.rounded_rectangle(
            (
                pill_x,
                pill_y,
                pill_x + pill_w,
                pill_y + pill_h
            ),
            radius=27,
            fill=(65, 65, 68)
        )

        draw.text(
            (
                pill_x + 24,
                pill_y + 13
            ),
            output_text,
            font=output_font,
            fill="white"
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

        temp = os.path.join(
            CACHE_DIR,
            f"thumb_{videoid}.jpg"
        )

        try:

            if os.path.exists(temp):
                os.remove(temp)

        except Exception:
            pass

        return output_file

    except Exception as e:

        print(
            f"get_thumb Error: {e}"
        )

        return YOUTUBE_IMG_URL


# ==========================================================
# GET QUICK THUMBNAIL
# ==========================================================

async def get_qthumb(vidid):

    try:

        urls = [

            f"https://i.ytimg.com/vi/"
            f"{vidid}/maxresdefault.jpg",

            f"https://i.ytimg.com/vi/"
            f"{vidid}/hqdefault.jpg",
        ]

        for url in urls:

            try:

                temp = os.path.join(
                    CACHE_DIR,
                    f"qthumb_{vidid}.jpg"
                )

                success = await download_image(
                    url,
                    temp
                )

                if success:

                    image = Image.open(
                        temp
                    )

                    if (
                        image.width > 100
                        and image.height > 100
                    ):

                        try:
                            os.remove(temp)
                        except Exception:
                            pass

                        return url

            except Exception:
                continue

        # Search fallback
        search_url = (
            f"https://www.youtube.com/"
            f"watch?v={vidid}"
        )

        results = VideosSearch(
            search_url,
            limit=1
        )

        data = await results.next()

        items = data.get(
            "result",
            []
        )

        if items:

            thumbnails = items[0].get(
                "thumbnails",
                []
            )

            if thumbnails:

                url = thumbnails[-1].get(
                    "url"
                )

                if url:
                    return url.split("?")[0]

        return YOUTUBE_IMG_URL

    except Exception as e:

        print(
            f"get_qthumb Error: {e}"
        )

        return YOUTUBE_IMG_URL
