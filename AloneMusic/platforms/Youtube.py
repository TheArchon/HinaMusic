# Copyright (C) 2021-2022 by TheAloneTeam@Github
#
# This file is part of AloneMusic project.

import asyncio
import os
import random
import re
import urllib.parse
from typing import Union

import httpx
import yt_dlp
from py_yt import VideosSearch
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

from AloneMusic import LOGGER
from AloneMusic.utils.formatters import time_to_seconds
import config


API_URL = os.getenv(
    "API_URL",
    "https://api.riteshyt.in",
).rstrip("/")

API_KEY = os.getenv(
    "API_KEY",
    "riteshfree576fd88ed84a3f46c84fd556",
)


async def download_assistant(
    query: str,
    dl_type: str,
) -> str:

    safe_query = urllib.parse.quote(query)
    ext = "mp4" if dl_type == "video" else "mp3"

    if API_KEY:
        return (
            f"{API_URL}/downloads/"
            f"{API_KEY}/{safe_query}.{ext}"
        )

    return (
        f"{API_URL}/downloads/stream"
        f"?query={safe_query}"
        f"&dl_type={dl_type}"
    )


async def download_song(link: str) -> str:
    return await download_assistant(link, "audio")


async def download_video(link: str) -> str:
    return await download_assistant(link, "video")


class YouTubeAPI:

    def __init__(self):

        self.base = (
            "https://www.youtube.com/watch?v="
        )

        self.regex = (
            r"(?:youtube\.com|youtu\.be)"
        )

        self.status = (
            "https://www.youtube.com/oembed?url="
        )

        self.listbase = (
            "https://youtube.com/playlist?list="
        )

        self.reg = re.compile(
            r"\x1B(?:[@-Z\\-_]|\[[0-?]*"
            r"[ -/]*[@-~])"
        )

        self._client = None

    async def get_client(self):

        if (
            self._client is None
            or self._client.is_closed
        ):
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    120.0,
                    connect=10.0,
                ),
                follow_redirects=True,
            )

        return self._client

    async def exists(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        return bool(
            re.search(self.regex, link)
        )

    async def url(
        self,
        message_1: Message,
    ):

        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(
                message_1.reply_to_message
            )

        for message in messages:

            if message.entities:

                for entity in message.entities:

                    if (
                        entity.type
                        == MessageEntityType.URL
                    ):

                        text = (
                            message.text
                            or message.caption
                            or ""
                        )

                        return text[
                            entity.offset:
                            entity.offset
                            + entity.length
                        ]

            elif message.caption_entities:

                for entity in (
                    message.caption_entities
                ):

                    if (
                        entity.type
                        == MessageEntityType.TEXT_LINK
                    ):
                        return entity.url

        return None

    def _clean_link(self, link):

        if not link:
            return ""

        link = str(link).strip()

        # Remove Telegram/YouTube tracking
        link = re.sub(
            r"[&?](?:si|feature|pp|spm|"
            r"ab_channel)=[^&]+",
            "",
            link,
        )

        # Keep only the actual YouTube URL
        if "&" in link:
            link = link.split("&")[0]

        return link

    async def _fetch_details(self, link):

        link = self._clean_link(link)

        client = await self.get_client()

        params = {
            "link": link,
        }

        if API_KEY:
            params["api_key"] = API_KEY

        try:

            response = await client.get(
                f"{API_URL}/details",
                params=params,
            )

            if response.status_code == 200:

                data = response.json()

                if isinstance(data, dict):
                    return data

            LOGGER(__name__).error(
                "YouTube details API error: "
                f"{response.status_code}"
            )

        except Exception as e:

            LOGGER(__name__).error(
                f"YouTube details error: {e}"
            )

        return None

    async def details(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        data = await self._fetch_details(link)

        if data:

            return (
                data.get("title"),
                data.get("duration_min"),
                data.get("duration_sec", 0),
                data.get("thumbnail"),
                data.get("vidid"),
            )

        return None, None, 0, None, None

    async def title(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        data = await self._fetch_details(link)

        return (
            data.get("title")
            if data
            else None
        )

    async def duration(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        data = await self._fetch_details(link)

        return (
            data.get("duration_min")
            if data
            else None
        )

    async def thumbnail(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        data = await self._fetch_details(link)

        return (
            data.get("thumbnail")
            if data
            else None
        )

    async def video(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        try:

            stream_url, status = await self.download(
                link,
                None,
                video=True,
            )

            if status:
                return 1, stream_url

            return 0, "Video URL generation failed"

        except Exception as e:

            return (
                0,
                f"Video URL generation error: {e}",
            )

    async def get_related_videos(
        self,
        vidid: str,
    ):

        autoplay_limit = min(
            getattr(
                config,
                "DURATION_LIMIT",
                600,
            ),
            600,
        )

        url = (
            f"https://www.youtube.com/watch?v="
            f"{vidid}&list=RD{vidid}"
        )

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlist_items": "2-20",
        }

        try:

            loop = asyncio.get_running_loop()

            info = await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(
                    ydl_opts
                ).extract_info(
                    url,
                    download=False,
                ),
            )

            if info and "entries" in info:

                ids = []

                for entry in info["entries"]:

                    if not entry:
                        continue

                    video_id = entry.get("id")

                    if (
                        not video_id
                        or video_id == vidid
                    ):
                        continue

                    duration = entry.get(
                        "duration"
                    )

                    if (
                        duration
                        and duration > autoplay_limit
                    ):
                        continue

                    ids.append(video_id)

                if ids:
                    return ids

        except Exception as e:

            LOGGER(__name__).warning(
                f"YouTube radio failed: {e}"
            )

        # Search fallback

        title = await self.title(
            vidid,
            True,
        )

        if title:

            try:

                results = VideosSearch(
                    f"{title} related songs",
                    limit=10,
                )

                data = await results.next()

                related = []

                for result in data.get(
                    "result",
                    [],
                ):

                    video_id = result.get("id")

                    if (
                        not video_id
                        or video_id == vidid
                    ):
                        continue

                    duration_str = result.get(
                        "duration"
                    )

                    if duration_str:

                        try:

                            seconds = (
                                time_to_seconds(
                                    duration_str
                                )
                            )

                            if (
                                seconds
                                > autoplay_limit
                            ):
                                continue

                        except Exception:
                            pass

                    related.append(video_id)

                if related:
                    return related

            except Exception as e:

                LOGGER(__name__).warning(
                    f"YouTube search failed: {e}"
                )

        return []

    async def track(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        data = await self._fetch_details(link)

        if data:

            track_details = {
                "title": data.get("title"),
                "link": data.get(
                    "link",
                    link,
                ),
                "vidid": data.get(
                    "vidid"
                ),
                "duration_min": data.get(
                    "duration_min"
                ),
                "thumb": data.get(
                    "thumbnail"
                ),
            }

            return (
                track_details,
                data.get("vidid"),
            )

        return None, None

    async def download(
        self,
        link,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        link = self._clean_link(link)

        dl_type = (
            "video"
            if video or songvideo
            else "audio"
        )

        regex = (
            r"(?:youtube\.com\/(?:"
            r"[^\/]+\/.+\/|"
            r"(?:v|e(?:mbed)?)\/|"
            r".*[?&]v=)"
            r"|youtu\.be\/)"
            r"([^\"&?\/\s]{11})"
        )

        match = re.search(
            regex,
            link,
        )

        vidid = (
            match.group(1)
            if match
            else None
        )

        if vidid:

            ext = (
                "mp4"
                if dl_type == "video"
                else "mp3"
            )

            # IMPORTANT:
            # Do NOT wait for prefetch.
            # It was causing slow playback.
            if API_KEY:

                stream_url = (
                    f"{API_URL}/downloads/"
                    f"{API_KEY}/youtube.com/"
                    f"{vidid}.{ext}"
                )

            else:

                stream_url = (
                    f"{API_URL}/downloads/"
                    f"youtube.com/"
                    f"{vidid}.{ext}"
                )

            return stream_url, True

        # Non-YouTube search/query fallback
        stream_url = await download_assistant(
            link,
            dl_type,
        )

        return stream_url, True

    async def prefetch(
        self,
        link,
        video=False,
    ):

        # Kept for compatibility with old code.
        # It runs in background and is NOT awaited
        # by download().

        dl_type = (
            "video"
            if video
            else "audio"
        )

        link = self._clean_link(link)

        client = await self.get_client()

        params = {
            "query": link,
            "dl_type": dl_type,
            "prefetch": "true",
        }

        if API_KEY:
            params["api_key"] = API_KEY

        try:

            asyncio.create_task(
                client.get(
                    f"{API_URL}/download",
                    params=params,
                )
            )

            return True

        except Exception as e:

            LOGGER(__name__).warning(
                f"Prefetch failed: {e}"
            )

            return False

    async def formats(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        link = self._clean_link(link)

        client = await self.get_client()

        params = {
            "link": link,
        }

        if API_KEY:
            params["api_key"] = API_KEY

        try:

            response = await client.get(
                f"{API_URL}/formats",
                params=params,
            )

            if response.status_code == 200:

                data = response.json()

                formats = data.get(
                    "formats",
                    [],
                )

                for fmt in formats:
                    fmt["yturl"] = link

                return formats, link

        except Exception as e:

            LOGGER(__name__).error(
                f"Formats error: {e}"
            )

        return [], link

    async def playlist(
        self,
        link,
        limit,
        user_id,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.listbase + link

        link = self._clean_link(link)

        client = await self.get_client()

        params = {
            "link": link,
            "limit": limit,
        }

        if API_KEY:
            params["api_key"] = API_KEY

        try:

            response = await client.get(
                f"{API_URL}/playlist",
                params=params,
            )

            if response.status_code == 200:

                return response.json().get(
                    "videos"
                )

        except Exception as e:

            LOGGER(__name__).error(
                f"Playlist error: {e}"
            )

        return None

    async def slider(
        self,
        link,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        link = self._clean_link(link)

        client = await self.get_client()

        params = {
            "query": link,
            "limit": 10,
        }

        if API_KEY:
            params["api_key"] = API_KEY

        try:

            response = await client.get(
                f"{API_URL}/search",
                params=params,
            )

            if response.status_code == 200:

                data = response.json()
                result = data.get("result")

                if (
                    result
                    and len(result) > query_type
                ):

                    item = result[query_type]

                    thumbs = item.get(
                        "thumbnails",
                        [],
                    )

                    thumb = (
                        thumbs[0]["url"]
                        .split("?")[0]
                        if thumbs
                        else None
                    )

                    return (
                        item.get("title"),
                        item.get("duration"),
                        thumb,
                        item.get("id"),
                    )

        except Exception as e:

            LOGGER(__name__).error(
                f"Search error: {e}"
            )

        return (
            None,
            None,
            None,
            None,
        )

    async def close(self):

        if (
            self._client
            and not self._client.is_closed
        ):
            await self._client.aclose()
