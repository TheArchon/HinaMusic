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
# FONT LOADER
# ==========================================================

def get_font(size, bold=False):

    if bold:
        font_names = [
            "font.ttf",
            "DejaVuSans-Bold.ttf",
            "LiberationSans-Bold.ttf",
        ]
    else:
        font_names = [
            "font2.ttf",
            "DejaVuSans.ttf",
            "LiberationSans-Regular.ttf",
        ]

    search_paths = []

    for name in font_names:
        search_paths.extend([
            os.path.join(FONT_DIR, name),
            os.path.join("assets", name),
            name,
        ])

    for path in search_paths:
        try:
            if os.path.isfile(path):
                return ImageFont.truetype(path, size)
        except Exception:
            pass

    system_fonts = [
        (
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf"
        ),
        (
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf"
        ),
    ]

    for path in system_fonts:
        try:
            if os.path.isfile(path):
                return ImageFont.truetype(path, size)
        except Exception:
            pass

    return ImageFont.load_default()


# ==========================================================
# TEXT WIDTH
# ==========================================================

def get_text_width(draw, text, font):

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
# SHORTEN TEXT
# ==========================================================

def shorten_text(text, limit):

    text = str(text or "").strip()

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

            async with session.get(url) as response:

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
            f"Image Download Error: {e}"
        )

        return False


# ==========================================================
# GET VALID THUMBNAIL
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
        (
            f"https://i.ytimg.com/vi/"
            f"{videoid}/maxresdefault.jpg"
        ),
        (
            f"https://i.ytimg.com/vi/"
            f"{videoid}/sddefault.jpg"
        ),
        (
            f"https://i.ytimg.com/vi/"
            f"{videoid}/hqdefault.jpg"
        ),
        (
            f"https://i.ytimg.com/vi/"
            f"{videoid}/mqdefault.jpg"
        ),
    ]

    if fallback:
        urls.append(
            fallback.split("?")[0]
        )

    for image_url in urls:

        try:

            success = await download_image(
                image_url,
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

            # Detect completely black/invalid image
            small = image.resize(
                (1, 1)
            )

            pixel = small.getpixel(
                (0, 0)
            )

            if sum(pixel) < 10:
                continue

            return image

        except Exception as e:

            print(
                f"Thumbnail Error: {e}"
            )

            continue

    return None


# ==========================================================
# ROUNDED IMAGE
# ==========================================================

def make_rounded_image(
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

    mask_draw = ImageDraw.Draw(
        mask
    )

    mask_draw.rounded_rectangle(
        (
            0,
            0,
            size,
            size
        ),
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

            test = Image.open(
                output_file
            )

            if (
                test.width > 100
                and test.height > 100
            ):
                return output_file

        except Exception:
            pass

    try:

        # ==================================================
        # YOUTUBE SEARCH
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
        # ARTIST / CHANNEL
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
        # SEARCH RESULT THUMBNAIL
        # ==================================================

        fallback_thumbnail = None

        try:

            thumbnails = result.get(
                "thumbnails",
                []
            )

            if thumbnails:

                fallback_thumbnail = (
                    thumbnails[-1].get(
                        "url"
                    )
                )

        except Exception:
            fallback_thumbnail = None

        # ==================================================
        # GET REAL YOUTUBE THUMBNAIL
        # ==================================================

        youtube = await get_youtube_thumbnail(
            videoid,
            fallback_thumbnail
        )

        if youtube is None:

            print(
                "Unable to load YouTube thumbnail"
            )

            return YOUTUBE_IMG_URL

        # ==================================================
        # BACKGROUND
        # ==================================================

        background = ImageOps.fit(
            youtube,
            (
                WIDTH,
                HEIGHT
            ),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5)
        )

        background = background.filter(
            ImageFilter.GaussianBlur(35)
        )

        background = ImageEnhance.Brightness(
            background
        ).enhance(0.18)

        background = ImageEnhance.Contrast(
            background
        ).enhance(0.70)

        background = background.convert(
            "RGBA"
        )

        # ==================================================
        # DARK BACKGROUND
        # ==================================================

        dark_background = Image.new(
            "RGBA",
            (
                WIDTH,
                HEIGHT
            ),
            (0, 0, 0, 130)
        )

        background = Image.alpha_composite(
            background,
            dark_background
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
                20,
                20,
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
                card_x - 10,
                card_y - 5
            )
        )

        # Main black card
        draw.rounded_rectangle(
            (
                card_x,
                card_y,
                card_x + card_w,
                card_y + card_h
            ),
            radius=55,
            fill=(7, 9, 9, 245)
        )

        # ==================================================
        # ALBUM COVER
        # ==================================================

        album_size = 500

        album_x = 85
        album_y = 135

        # Album shadow
        album_shadow = Image.new(
            "RGBA",
            (
                album_size + 40,
                album_size + 40
            ),
            (0, 0, 0, 0)
        )

        album_shadow_draw = ImageDraw.Draw(
            album_shadow
        )

        album_shadow_draw.rounded_rectangle(
            (
                15,
                15,
                album_size + 15,
                album_size + 15
            ),
            radius=35,
            fill=(0, 0, 0, 150)
        )

        album_shadow = album_shadow.filter(
            ImageFilter.GaussianBlur(12)
        )

        background.alpha_composite(
            album_shadow,
            (
                album_x - 5,
                album_y - 3
            )
        )

        album = make_rounded_image(
            youtube,
            album_size,
            32
        )

        background.alpha_composite(
            album,
            (
                album_x,
                album_y
            )
        )

        # ==================================================
        # ALBUM DARK GRADIENT
        # ==================================================

        album_dark = Image.new(
            "RGBA",
            (
                album_size,
                album_size
            ),
            (0, 0, 0, 0)
        )

        album_dark_draw = ImageDraw.Draw(
            album_dark
        )

        # Bottom dark overlay
        for i in range(180):

            alpha = int(
                170 * (i / 180)
            )

            y = album_size - i - 1

            album_dark_draw.line(
                (
                    0,
                    y,
                    album_size,
                    y
                ),
                fill=(
                    0,
                    0,
                    0,
                    alpha
                )
            )

        album_mask = Image.new(
            "L",
            (
                album_size,
                album_size
            ),
            0
        )

        album_mask_draw = ImageDraw.Draw(
            album_mask
        )

        album_mask_draw.rounded_rectangle(
            (
                0,
                0,
                album_size,
                album_size
            ),
            radius=32,
            fill=255
        )

        album_dark.putalpha(
            Image.composite(
                album_dark.getchannel("A"),
                Image.new(
                    "L",
                    album_dark.size,
                    0
                ),
                album_mask
            )
        )

        background.alpha_composite(
            album_dark,
            (
                album_x,
                album_y
            )
        )

        # ==================================================
        # ALBUM TITLE
        # ==================================================

        album_font = get_font(
            22,
            bold=True
        )

        album_title = shorten_text(
            title.upper(),
            28
        )

        album_box = draw.textbbox(
            (
                0,
                0
            ),
            album_title,
            font=album_font
        )

        album_tw = (
            album_box[2]
            - album_box[0]
        )

        album_th = (
            album_box[3]
            - album_box[1]
        )

        draw.text(
            (
                album_x +
                (album_size - album_tw) / 2,
                album_y +
                (album_size - album_th) / 2
                + 110
            ),
            album_title,
            font=album_font,
            fill="white"
        )

        # ==================================================
        # RIGHT SIDE
        # ==================================================

        right_x = 620

        # ==================================================
        # FONTS
        # ==================================================

        title_font = get_font(
            31,
            bold=True
        )

        artist_font = get_font(
            26
        )

        time_font = get_font(
            17
        )

        output_font = get_font(
            20
        )

        # ==================================================
        # SONG TITLE
        # ==================================================

        display_title = shorten_text(
            title,
            27
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

        display_channel = shorten_text(
            channel,
            28
        )

        draw.text(
            (
                right_x,
                181
            ),
            display_channel,
            font=artist_font,
            fill=(170, 170, 175)
        )

        # ==================================================
        # MENU BUTTON
        # ==================================================

        menu_x = 1150
        menu_y = 145
        menu_size = 54

        draw.ellipse(
            (
                menu_x,
                menu_y,
                menu_x + menu_size,
                menu_y + menu_size
            ),
            fill=(85, 85, 88, 210)
        )

        menu_font = get_font(
            27,
            bold=True
        )

        draw.text(
            (
                menu_x + 14,
                menu_y + 3
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
        bar_h = 14

        draw.rounded_rectangle(
            (
                bar_x,
                bar_y,
                bar_x + bar_w,
                bar_y + bar_h
            ),
            radius=7,
            fill=(75, 75, 78)
        )

        # 62% progress
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
            fill=(235, 235, 238)
        )

        # Slider dot
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
                291
            ),
            "3:23",
            font=time_font,
            fill=(210, 210, 215)
        )

        remaining = "-1:57"

        remaining_w = get_text_width(
            draw,
            remaining,
            time_font
        )

        draw.text(
            (
                bar_x +
                bar_w -
                remaining_w,
                291
            ),
            remaining,
            font=time_font,
            fill=(210, 210, 215)
        )

        # ==================================================
        # PLAYER CONTROLS
        # ==================================================

        control_y = 495

        # --------------------------------------------------
        # PREVIOUS
        # --------------------------------------------------

        prev_x = 765

        draw.polygon(
            [
                (
                    prev_x,
                    control_y
                ),
                (
                    prev_x + 42,
                    control_y - 31
                ),
                (
                    prev_x + 42,
                    control_y + 31
                )
            ],
            fill="white"
        )

        draw.polygon(
            [
                (
                    prev_x + 40,
                    control_y
                ),
                (
                    prev_x + 82,
                    control_y - 31
                ),
                (
                    prev_x + 82,
                    control_y + 31
                )
            ],
            fill="white"
        )

        # --------------------------------------------------
        # PAUSE
        # --------------------------------------------------

        pause_x = 900

        draw.rounded_rectangle(
            (
                pause_x,
                control_y - 38,
                pause_x + 19,
                control_y + 38
            ),
            radius=5,
            fill="white"
        )

        draw.rounded_rectangle(
            (
                pause_x + 31,
                control_y - 38,
                pause_x + 50,
                control_y + 38
            ),
            radius=5,
            fill="white"
        )

        # --------------------------------------------------
        # NEXT
        # --------------------------------------------------

        next_x = 1045

        draw.polygon(
            [
                (
                    next_x,
                    control_y - 31
                ),
                (
                    next_x + 42,
                    control_y
                ),
                (
                    next_x,
                    control_y + 31
                )
            ],
            fill="white"
        )

        draw.polygon(
            [
                (
                    next_x + 40,
                    control_y - 31
                ),
                (
                    next_x + 82,
                    control_y
                ),
                (
                    next_x + 40,
                    control_y + 31
                )
            ],
            fill="white"
        )

        # ==================================================
        # VOLUME SECTION
        # ==================================================

        volume_y = 605

        # Left speaker
        speaker_font = get_font(
            22,
            bold=True
        )

        draw.text(
            (
                right_x - 3,
                volume_y - 14
            ),
            "◀",
            font=speaker_font,
            fill=(170, 170, 175)
        )

        # Volume bar
        volume_x = right_x + 50
        volume_w = 450
        volume_h = 13

        draw.rounded_rectangle(
            (
                volume_x,
                volume_y,
                volume_x + volume_w,
                volume_y + volume_h
            ),
            radius=7,
            fill=(75, 75, 78)
        )

        volume_progress = 0.48

        volume_progress_w = int(
            volume_w *
            volume_progress
        )

        draw.rounded_rectangle(
            (
                volume_x,
                volume_y,
                volume_x +
                volume_progress_w,
                volume_y +
                volume_h
            ),
            radius=7,
            fill=(225, 225, 228)
        )

        # Right speaker
        draw.text(
            (
                volume_x +
                volume_w +
                25,
                volume_y - 17
            ),
            ")))",
            font=speaker_font,
            fill=(170, 170, 175)
        )

        # ==================================================
        # MEDIA OUTPUT / IPHONE
        # ==================================================

        output_text = "◉  iPhone"

        output_w = get_text_width(
            draw,
            output_text,
            output_font
        )

        output_pill_w = int(
            output_w + 48
        )

        output_pill_h = 54

        output_x = 850
        output_y = 645

        draw.rounded_rectangle(
            (
                output_x,
                output_y,
                output_x +
                output_pill_w,
                output_y +
                output_pill_h
            ),
            radius=27,
            fill=(70, 70, 73, 225)
        )

        draw.text(
            (
                output_x + 24,
                output_y + 13
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
        # DELETE TEMP
        # ==================================================

        temp_file = os.path.join(
            CACHE_DIR,
            f"thumb_{videoid}.jpg"
        )

        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass

        return output_file

    except Exception as e:

        print(
            f"get_thumb Error: {e}"
        )

        temp_file = os.path.join(
            CACHE_DIR,
            f"thumb_{videoid}.jpg"
        )

        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass

        return YOUTUBE_IMG_URL


# ==========================================================
# GET YOUTUBE THUMBNAIL URL
# ==========================================================

async def get_qthumb(vidid):

    try:

        # Direct YouTube thumbnail
        urls = [
            (
                f"https://i.ytimg.com/vi/"
                f"{vidid}/maxresdefault.jpg"
            ),
            (
                f"https://i.ytimg.com/vi/"
                f"{vidid}/hqdefault.jpg"
            ),
        ]

        for url in urls:

            try:

                temp = os.path.join(
                    CACHE_DIR,
                    f"qthumb_{vidid}.jpg"
                )

                if await download_image(
                    url,
                    temp
                ):

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
