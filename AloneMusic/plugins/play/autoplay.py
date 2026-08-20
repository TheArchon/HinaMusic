#
# Copyright (C) 2021-2022 by TheAloneteam@Github, < https://github.com/TheAloneTeam >.
#
# This file is part of < https://github.com/TheAloneTeam/AloneMusic > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TheAloneTeam/AloneMusic/blob/master/LICENSE >
#
# All rights reserved.
#

from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import random

from AloneMusic import app, YouTube
from AloneMusic.core.call import Alone
from AloneMusic.utils.database import (
    autoplay_off,
    autoplay_on,
    is_autoplay_on,
    get_lang,
)
from AloneMusic.utils.decorators import (
    language,
    AdminRightsCheck,
)
from config import BANNED_USERS
from strings import get_string


# =========================================================
# AUTOPLAY HISTORY
# =========================================================
#
# Each group has its own played-song history.
#
# Example:
#
# Song A
#   ↓
# Song B
#   ↓
# Song C
#   ↓
# Song D
#
# Song A/B/C will not immediately come again.
#
# =========================================================

AUTOPLAY_HISTORY = {}


def get_history(chat_id):
    chat_id = int(chat_id)

    if chat_id not in AUTOPLAY_HISTORY:
        AUTOPLAY_HISTORY[chat_id] = set()

    return AUTOPLAY_HISTORY[chat_id]


def normalize_id(video_id):
    if not video_id:
        return None

    try:
        video_id = str(video_id).strip()

        if len(video_id) == 11:
            return video_id

    except Exception:
        pass

    return None


def reset_history(chat_id):
    chat_id = int(chat_id)

    AUTOPLAY_HISTORY.pop(
        chat_id,
        None,
    )


def add_played(chat_id, video_id):
    video_id = normalize_id(video_id)

    if not video_id:
        return

    history = get_history(chat_id)

    history.add(video_id)


# =========================================================
# AUTOPLAY COMMAND
# =========================================================

@app.on_message(
    filters.command(["autoplay"])
    & filters.group
    & ~BANNED_USERS
)
@language
async def autoplay_command(
    client,
    message: Message,
    _,
):

    if len(message.command) < 2:

        playmode = await is_autoplay_on(
            message.chat.id
        )

        buttons = [
            [
                InlineKeyboardButton(
                    text=(
                        "⌯ єɴʌʙʟє ⌯"
                        if not playmode
                        else "⌯ ᴅɪsʌʙʟє ⌯"
                    ),
                    callback_data="AUTOPLAYCHANGE",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⌯ ᴄʟᴏsє ⌯",
                    callback_data="close",
                ),
            ],
        ]

        return await message.reply_text(
            _["autoplay_1"],
            reply_markup=InlineKeyboardMarkup(
                buttons
            ),
        )

    state = (
        message.text
        .split(None, 1)[1]
        .strip()
        .lower()
    )

    if state == "on":

        await autoplay_on(
            message.chat.id
        )

        # New autoplay session
        reset_history(
            message.chat.id
        )

        await message.reply_text(
            "» ʌᴜᴛᴏᴘʟʌʏ єɴʌʙʟєᴅ sᴜᴄᴄєssғᴜʟʟʏ."
        )

    elif state == "off":

        await autoplay_off(
            message.chat.id
        )

        # Clear history when autoplay disabled
        reset_history(
            message.chat.id
        )

        await message.reply_text(
            "» ʌᴜᴛᴏᴘʟʌʏ ᴅɪsʌʙʟєᴅ sᴜᴄᴄєssғᴜʟʟʏ."
        )

    else:

        await message.reply_text(
            "» ɪɴᴠʌʟɪᴅ ʌʀɢᴜϻєɴᴛ. ᴜsє ᴏɴ/ᴏғғ."
        )


# =========================================================
# AUTOPLAY SKIP
# =========================================================

@app.on_message(
    filters.command(["askip"])
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck
async def askip_command(
    client,
    message: Message,
    _,
    chat_id,
):

    # =====================================================
    # CHECK AUTOPLAY
    # =====================================================

    if not await is_autoplay_on(
        chat_id
    ):

        return await message.reply_text(
            "» ɴᴏᴛ ᴏɴ ʌᴜᴛᴏ ᴘʟʌʏ "
            "ᴘʟєʌsє ᴏɴ ʌᴜᴛᴏ ᴘʟʌʏ "
            "ʌɴᴅ ᴛʀʏ ʌɢʌɪɴ."
        )

    # =====================================================
    # DATABASE
    # =====================================================

    from AloneMusic.misc import db
    from AloneMusic.utils.stream.stream import stream

    check = db.get(chat_id)

    if not check:
        return

    # =====================================================
    # CURRENT TRACK
    # =====================================================

    current = check[0]

    old_mystic = current.get(
        "mystic"
    )

    if old_mystic:

        try:
            await old_mystic.delete()

        except Exception:
            pass

    # =====================================================
    # CURRENT VIDEO ID
    # =====================================================

    current_id = normalize_id(
        current.get("vidid")
    )

    if current_id:

        # Current song is now considered played.
        add_played(
            chat_id,
            current_id,
        )

    # =====================================================
    # REMOVE CURRENT SONG
    # =====================================================

    popped = check.pop(0)

    try:

        # =================================================
        # PLAYED HISTORY
        # =================================================

        history = get_history(
            chat_id
        )

        # Make a copy so it can safely
        # be passed to YouTube search.
        excluded_ids = set(
            history
        )

        # Current song MUST NOT return.
        if current_id:
            excluded_ids.add(
                current_id
            )

        # =================================================
        # GET RELATED SONGS
        # =================================================

        related = await YouTube.get_related_videos(
            current_id,
            limit=20,
            exclude_ids=excluded_ids,
            session_id=chat_id,
        )

        # =================================================
        # REMOVE DUPLICATES AGAIN
        # =================================================

        unique_related = []

        seen = set(
            excluded_ids
        )

        for video_id in related:

            video_id = normalize_id(
                video_id
            )

            if not video_id:
                continue

            if video_id in seen:
                continue

            seen.add(
                video_id
            )

            unique_related.append(
                video_id
            )

        # =================================================
        # NO NEW SONG
        # =================================================

        if not unique_related:

            # If the history has become too large,
            # start a fresh autoplay cycle.
            #
            # The CURRENT song is kept excluded.

            reset_history(
                chat_id
            )

            if current_id:
                add_played(
                    chat_id,
                    current_id,
                )

            related = await YouTube.get_related_videos(
                current_id,
                limit=20,
                exclude_ids={
                    current_id
                } if current_id else set(),
                session_id=chat_id,
            )

            unique_related = []

            seen = set()

            if current_id:
                seen.add(
                    current_id
                )

            for video_id in related:

                video_id = normalize_id(
                    video_id
                )

                if not video_id:
                    continue

                if video_id in seen:
                    continue

                seen.add(
                    video_id
                )

                unique_related.append(
                    video_id
                )

        # =================================================
        # STILL NOTHING
        # =================================================

        if not unique_related:

            return

        # =================================================
        # SELECT NEXT SONG
        # =================================================

        video_id = random.choice(
            unique_related
        )

        # =================================================
        # SAVE AS PLAYED IMMEDIATELY
        # =================================================
        #
        # This is important.
        #
        # If the next callback happens very quickly,
        # the same song cannot be selected again.
        #

        add_played(
            chat_id,
            video_id,
        )

        # =================================================
        # GET TRACK DETAILS
        # =================================================

        details, track_id = await YouTube.track(
            video_id,
            True,
        )

        if not details:
            return

        track_id = normalize_id(
            track_id
        )

        if not track_id:
            return

        # =================================================
        # FINAL DUPLICATE CHECK
        # =================================================

        if current_id and track_id == current_id:
            return

        # =================================================
        # START NEXT SONG
        # =================================================

        await stream(
            _,
            old_mystic,
            popped["user_id"],
            details,
            chat_id,
            popped["by"],
            popped["chat_id"],
            video=(
                True
                if popped["streamtype"] == "video"
                else False
            ),
            streamtype="youtube",
            forceplay=True,
        )

    except Exception:
        pass
