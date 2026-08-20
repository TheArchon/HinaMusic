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
import logging
from AloneMusic import app, YouTube
from AloneMusic.core.call import Alone
from AloneMusic.utils.database import (autoplay_off, autoplay_on,
                                       is_autoplay_on, get_lang)
from AloneMusic.utils.decorators import language, AdminRightsCheck
from config import BANNED_USERS
from strings import get_string

logger = logging.getLogger(__name__)


@app.on_message(filters.command(["autoplay"]) & filters.group & ~BANNED_USERS)
@language
async def autoplay_command(client, message: Message, _):
    if len(message.command) < 2:
        playmode = await is_autoplay_on(message.chat.id)
        buttons = [
            [
                InlineKeyboardButton(
                    text="⌯ єɴʌʙʟє ⌯" if not playmode else "⌯ ᴅɪsʌʙʟє ⌯",
                    callback_data=f"AUTOPLAYCHANGE"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⌯ ᴄʟᴏsє ⌯", callback_data="close"
                ),
            ],
        ]
        return await message.reply_text(
            _["autoplay_1"],
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    state = message.text.split(None, 1)[1].strip().lower()
    if state == "on":
        await autoplay_on(message.chat.id)
        await message.reply_text("» ʌᴜᴛᴏᴘʟʌʏ єɴʌʙʟєᴅ sᴜᴄᴄєssғᴜʟʟʏ.")
    elif state == "off":
        await autoplay_off(message.chat.id)
        await message.reply_text("» ʌᴜᴛᴏᴘʟʌʏ ᴅɪsʌʙʟєᴅ sᴜᴄᴄєssғᴜʟʟʏ.")
    else:
        await message.reply_text("» ɪɴᴠʌʟɪᴅ ʌʀɢᴜϻєɴᴛ. ᴜsє ᴏɴ/ᴏғғ.")


@app.on_message(filters.command(["askip"]) & filters.group & ~BANNED_USERS)
@AdminRightsCheck
async def askip_command(client, message: Message, _, chat_id):
    from AloneMusic.misc import db
    from AloneMusic.utils.stream.stream import stream

    if not await is_autoplay_on(chat_id):
        return await message.reply_text(
            "» ɴᴏᴛ ᴏɴ ʌᴜᴛᴏ ᴘʟᴀʏ. ᴘʟᴇᴀsᴇ ᴏɴ ᴀᴜᴛᴏᴘʟᴀʏ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ."
        )

    check = db.get(chat_id)
    if not check:
        return

    old_mystic = check[0].get("mystic")
    popped = check.pop(0)

    try:
        if old_mystic:
            await old_mystic.delete()
    except Exception:
        pass

    vidid = popped.get("vidid")
    if not vidid:
        return

    try:
        related = await YouTube.get_related_videos(vidid, limit=10)
    except Exception as e:
        logger.exception("askip: get_related_videos failed for %s: %s", vidid, e)
        related = []

    logger.info("askip: related for %s -> %s", vidid, related)

    if not related:
        return

    candidates = list(related)
    random.shuffle(candidates)

    user_id = popped.get("user_id") or popped.get("userid") or popped.get("requested_by")
    by = popped.get("by") or popped.get("user_name") or "Autoplay"
    is_video = popped.get("streamtype") == "video"

    # Try several recommendations. A single bad YouTube result must
    # not terminate autoplay.
    for item in candidates:
        try:
            if isinstance(item, dict):
                video_id = item.get("id") or item.get("vidid") or item.get("link")
            else:
                video_id = str(item)

            if not video_id:
                continue

            try:
                details, track_id = await YouTube.track(video_id, True)
            except Exception as e:
                logger.exception("askip: failed to fetch track details for %s: %s", video_id, e)
                continue

            if not details or not details.get("title"):
                continue

            try:
                await stream(
                    _,
                    old_mystic,
                    user_id,
                    details,
                    chat_id,
                    by,
                    popped.get("chat_id", chat_id),
                    video=is_video,
                    streamtype="youtube",
                    forceplay=True,
                )
                return
            except Exception as e:
                logger.exception("askip: streaming failed for %s: %s", video_id, e)
                # fallback: queue the candidate as forceplay
                try:
                    from AloneMusic.utils.stream.queue import put_queue
                    await put_queue(
                        chat_id,
                        popped.get("chat_id", chat_id),
                        f"vid_{video_id}",
                        details.get("title", "Unknown"),
                        details.get("duration_min", "0:00"),
                        popped.get("by"),
                        video_id,
                        user_id,
                        popped.get("streamtype"),
                        forceplay=True,
                        mystic=None,
                    )
                    logger.info("askip: queued fallback vid_%s for chat %s", video_id, chat_id)
                    return
                except Exception as e:
                    logger.exception("askip: fallback queue insert failed for %s: %s", video_id, e)
                    continue
        except Exception:
            continue

  
