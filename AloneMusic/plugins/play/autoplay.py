# Copyright (C) 2021-2022 by TheAloneTeam@Github
#
# Autoplay + /askip handlers.

import random

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from AloneMusic import app, YouTube
from AloneMusic.utils.database import (
    autoplay_off,
    autoplay_on,
    is_autoplay_on,
)
from AloneMusic.utils.decorators import language, AdminRightsCheck
from config import BANNED_USERS


async def _next_autoplay(_, chat_id, popped, old_mystic):
    """Fetch and start the next related YouTube track."""

    if not popped or not popped.get("vidid"):
        return False

    try:
        related = await YouTube.get_related_videos(
            popped["vidid"]
        )
    except Exception:
        return False

    if not related:
        return False

    candidates = list(related)
    random.shuffle(candidates)

    for video_id in candidates[:8]:
        try:
            details, track_id = await YouTube.track(
                video_id,
                True,
            )

            if not details:
                continue

            if not details.get("title"):
                continue

            from AloneMusic.utils.stream.stream import stream

            await stream(
                _,
                old_mystic,
                popped.get("user_id"),
                details,
                chat_id,
                popped.get("by", "Autoplay"),
                popped.get("chat_id", chat_id),
                video=(
                    str(popped.get("streamtype"))
                    == "video"
                ),
                streamtype="youtube",
                forceplay=True,
            )

            return True

        except Exception:
            continue

    return False


@app.on_message(
    filters.command(["autoplay"])
    & filters.group
    & ~BANNED_USERS
)
@language
async def autoplay_command(client, message: Message, _):

    if len(message.command) < 2:
        enabled = await is_autoplay_on(
            message.chat.id
        )

        buttons = [
            [
                InlineKeyboardButton(
                    text=(
                        "⌯ ᴅɪsᴀʙʟᴇ ⌯"
                        if enabled
                        else "⌯ ᴇɴᴀʙʟᴇ ⌯"
                    ),
                    callback_data="AUTOPLAYCHANGE",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⌯ ᴄʟᴏsᴇ ⌯",
                    callback_data="close",
                )
            ],
        ]

        return await message.reply_text(
            _["autoplay_1"],
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    state = message.command[1].strip().lower()

    if state == "on":
        await autoplay_on(message.chat.id)

        return await message.reply_text(
            "» ᴀᴜᴛᴏᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ."
        )

    if state == "off":
        await autoplay_off(message.chat.id)

        return await message.reply_text(
            "» ᴀᴜᴛᴏᴘʟᴀʏ ᴅɪsᴀʙʟᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ."
        )

    return await message.reply_text(
        "» ɪɴᴠᴀʟɪᴅ ᴀʀɢᴜᴍᴇɴᴛ. "
        "ᴜsᴇ /autoplay on ᴏʀ /autoplay off."
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
    from AloneMusic.core.call import Alone

    if not await is_autoplay_on(chat_id):
        return await message.reply_text(
            "» ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴏғғ. "
            "ᴜsᴇ /autoplay on ғɪʀsᴛ."
        )

    check = db.get(chat_id)

    if not check:
        return await message.reply_text(
            "» ɴᴏ ᴘʟᴀʏɪɴɢ sᴏɴɢ ғᴏᴜɴᴅ."
        )

    # Remove current song from queue
    popped = check.pop(0)

    old_mystic = popped.get("mystic")

    # Delete old "STARTED STREAMING NOW" message
    if old_mystic:
        try:
            await old_mystic.delete()
        except Exception:
            pass

    # Play next autoplay song
    success = await _next_autoplay(
        _,
        chat_id,
        popped,
        old_mystic,
    )

    if success:
        return

    # Nothing found
    try:
        await Alone.stop_stream(chat_id)
    except Exception:
        pass

    await message.reply_text(
        "» ɴᴇxᴛ ᴀᴜᴛᴏᴘʟᴀʏ sᴏɴɢ "
        "ᴄᴏᴜʟᴅ ɴᴏᴛ ʙᴇ ғᴏᴜɴᴅ."
          )
