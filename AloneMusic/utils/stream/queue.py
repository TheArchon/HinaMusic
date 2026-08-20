#
# Copyright (C) 2021-2022 by TheAloneteam@Github, < https://github.com/TheAloneTeam >.
#
# This file is part of < https://github.com/TheAloneTeam/AloneMusic > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TheAloneTeam/AloneMusic/blob/master/LICENSE >
#
# All rights reserved.

import asyncio
import logging
from typing import Union, Optional

from AloneMusic.misc import db
from AloneMusic.utils.formatters import check_duration, seconds_to_min
from config import autoclean, time_to_seconds

logger = logging.getLogger(__name__)


async def put_queue(
    chat_id,
    original_chat_id,
    file,
    title,
    duration,
    user,
    vidid,
    user_id,
    stream,
    forceplay: Union[bool, str] = None,
    mystic: Union[bool, str] = None,
):
    """Add a track entry to the in-memory queue (db).

    This function is defensive: it ensures the queue list exists before
    inserting/appending and logs unexpected errors instead of silently
    swallowing them.
    """
    title = title.title() if title else title
    try:
        duration_in_seconds = time_to_seconds(duration) - 3
    except Exception as e:
        logger.debug("put_queue: time_to_seconds failed for %s: %s", duration, e)
        duration_in_seconds = 0

    put = {
        "title": title,
        "dur": duration,
        "streamtype": stream,
        "by": user,
        "user_id": user_id,
        "chat_id": original_chat_id,
        "file": file,
        "vidid": vidid,
        "seconds": duration_in_seconds,
        "played": 0,
        "mystic": mystic,
    }

    try:
        queue = db.get(chat_id)
        if forceplay:
            if queue:
                queue.insert(0, put)
            else:
                db[chat_id] = [put]
        else:
            if queue is None:
                db[chat_id] = [put]
            else:
                queue.append(put)
    except Exception as e:
        # Log unexpected failures when manipulating the shared queue
        logger.exception("put_queue: failed to add item to queue for chat %s: %s", chat_id, e)
        # As a last resort, initialise the queue atomically
        try:
            db[chat_id] = [put]
        except Exception:
            # If even this fails, there's nothing more we can do here
            logger.exception("put_queue: fatal - could not initialize queue for chat %s", chat_id)
            return

    try:
        # record for later cleanup (autoclean may be a list)
        autoclean.append(file)
    except Exception:
        logger.debug("put_queue: autoclean append failed for %s", file)


async def put_queue_index(
    chat_id,
    original_chat_id,
    file,
    title,
    duration,
    user,
    vidid,
    stream,
    forceplay: Union[bool, str] = None,
    mystic: Union[bool, str] = None,
):
    """Put an index (m3u/stream) entry into the queue.

    Safely handles missing vidid values and logs duration extraction errors.
    """
    dur = 0
    try:
        if vidid and "20.212.146.162" in str(vidid):
            try:
                dur = await asyncio.get_event_loop().run_in_executor(None, check_duration, vidid)
                duration = seconds_to_min(dur)
            except Exception as e:
                logger.exception("put_queue_index: check_duration failed for %s: %s", vidid, e)
                duration = "ᴜʀʟ sᴛʀᴇᴀᴍ"
                dur = 0
    except Exception as e:
        logger.debug("put_queue_index: unexpected vidid check failure for %s: %s", vidid, e)

    put = {
        "title": title,
        "dur": duration,
        "streamtype": stream,
        "by": user,
        "chat_id": original_chat_id,
        "file": file,
        "vidid": vidid,
        "seconds": dur,
        "played": 0,
        "mystic": mystic,
    }

    try:
        queue = db.get(chat_id)
        if forceplay:
            if queue:
                queue.insert(0, put)
            else:
                db[chat_id] = [put]
        else:
            if queue is None:
                db[chat_id] = [put]
            else:
                queue.append(put)
    except Exception as e:
        logger.exception("put_queue_index: failed to add item to queue for chat %s: %s", chat_id, e)
        try:
            db[chat_id] = [put]
        except Exception:
            logger.exception("put_queue_index: fatal - could not initialize queue for chat %s", chat_id)
            return
