#
# Copyright (C) 2021-2022 by TheAloneteam@Github, < https://github.com/TheAloneTeam >.
#
# This file is part of < https://github.com/TheAloneTeam/AloneMusic > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TheAloneTeam/AloneMusic/blob/master/LICENSE >
#
# All rights reserved.

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import random

from AloneMusic import app, YouTube
from AloneMusic.utils.database import (
    autoplay_off,
    autoplay_on,
    is_autoplay_on,
    get_lang,
)
from AloneMusic.utils.decorators import language, AdminRightsCheck
from config import BANNED_USERS
from strings import get_string


@app.on_message(
    filters.command(["autoplay"])
    & filters.group
    & ~BANNED_USERS
)
@language
async def autoplay_command(client, message: Message, _):

    if len(message.command) < 2:
        playmode = await is_autoplay_on(message.chat.id)

        buttons = [
            [
                InlineKeyboardButton(
                    text="⌯ єɴʌʙʟє ⌯"
                    if not playmode
                    else "⌯ ᴅɪsʌʙʟє ⌯",
                    callback_data="AUTOPLAYCHANGE",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⌯ ᴄʟᴏsє",
                    callback_data="close",
                ),
            ],
        ]

        return await message.reply_text(
            _["autoplay_1"],
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    state = (
        message.text.split(None, 1)[1]
        .strip()
        .lower()
    )

    if state == "on":

        await autoplay_on(message.chat.id)

        await message.reply_text(
            "» ʌᴜᴛᴏᴘʟʌʏ єɴʌʙʟєᴅ sᴜᴄᴄєssғᴜʟʟʏ."
        )

    elif state == "off":

        await autoplay_off(message.chat.id)

        await message.reply_text(
            "» ʌᴜᴛᴏᴘʟʌʏ ᴅɪsʌʙʟєᴅ sᴜᴄᴄєssғᴜʟʟʏ."
        )

    else:

        await message.reply_text(
            "» ɪɴᴠʌʟɪᴅ ʌʀɢᴜϻєɴᴛ. ᴜsє ᴏɴ/ᴏғғ."
        )


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

    from AloneMusic.misc import db
    from AloneMusic.utils.stream.stream import stream

    # Check autoplay status
    if not await is_autoplay_on(chat_id):

        return await message.reply_text(
            "» ɴᴏᴛ ᴏɴ ᴀᴜᴛᴏᴘʟᴀʏ. "
            "ᴘʟᴇᴀsᴇ ᴏɴ ᴀᴜᴛᴏᴘʟᴀʏ "
            "ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ."
        )

    # Get current queue
    check = db.get(chat_id)

    if not check:

        return await message.reply_text(
            "» ɴᴏ ᴛʀᴀᴄᴋ ғᴏᴜɴᴅ ɪɴ ᴛʜᴇ ᴘʟᴀʏᴇʀ."
        )

    # Remove current track
    popped = check.pop(0)

    try:

        # Delete old now-playing message
        old_mystic = popped.get("mystic")

        if old_mystic:

            try:
                await old_mystic.delete()

            except Exception:
                pass

        # Get current video ID
        vidid = popped.get("vidid")

        if not vidid:

            return await message.reply_text(
                "» ᴄᴜʀʀᴇɴᴛ ᴛʀᴀᴄᴋ "
                "ɪᴅ ɴᴏᴛ ғᴏᴜɴᴅ."
            )

        # Get related YouTube videos
        related = await YouTube.get_related_videos(
            vidid
        )

        if not related:

            return await message.reply_text(
                "» ɴᴏ ʀᴇʟᴀᴛᴇᴅ sᴏɴɢ ғᴏᴜɴᴅ."
            )

        # Randomize related songs
        random.shuffle(related)

        # Try related songs one by one
        for video_id in related:

            try:

                # Fetch track information
                details, track_id = await YouTube.track(
                    video_id,
                    True,
                )

                if not details:
                    continue

                # Start the next song
                await stream(
                    _,
                    None,
                    popped.get("user_id"),
                    details,
                    chat_id,
                    popped.get("by"),
                    popped.get(
                        "chat_id",
                        chat_id,
                    ),
                    video=(
                        popped.get("streamtype")
                        == "video"
                    ),
                    streamtype="youtube",
                    forceplay=True,
                )

                # Successfully started
                return

            except Exception as e:

                print(
                    f"Autoplay skip failed "
                    f"for {video_id}: {e}"
                )

                continue

        # No playable song found
        await message.reply_text(
            "» ᴀᴜᴛᴏᴘʟᴀʏ ᴄᴏᴜʟᴅ ɴᴏᴛ ғɪɴᴅ "
            "ᴀ ᴘʟᴀʏᴀʙʟᴇ sᴏɴɢ."
        )

    except Exception as e:

        print(
            f"Autoplay skip error: {e}"
        )

        await message.reply_text(
            "» ᴀᴜᴛᴏᴘʟᴀʏ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ."
      )
