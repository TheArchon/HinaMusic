# Copyright (C) 2021-2022 by TheAloneTeam@Github
#
# This file is part of AloneMusic project.

import asyncio
import os
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


# =========================================================
# CONFIG
# =========================================================

API_URL = os.getenv(
    "API_URL",
    "https://yt.riteshyt.in",
).rstrip("/")

API_KEY = os.getenv(
    "API_KEY",
    "riteshfree576fd88ed84a3f46c84fd556",
)


# Optional yt-dlp cookies file.
# Set YT_COOKIES_FILE in environment if required.
COOKIES_FILE = os.getenv(
    "YT_COOKIES_FILE",
    "",
)


# =========================================================
# YT-DLP OPTIONS
# =========================================================

def _base_ydl_options():
    options = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "geo_bypass": True,
        "extractor_args": {
            "youtube": {
                "player_client": [
                    "android",
                    "web",
                ]
            }
        },
    }

    if COOKIES_FILE and os.path.exists(COOKIES_FILE):
        options["cookiefile"] = COOKIES_FILE

    return options


def _extract_info_sync(url, options):
    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info(
            url,
            download=False,
        )


# =========================================================
# API DOWNLOAD FALLBACK
# =========================================================

async def download_assistant(
    query: str,
    dl_type: str,
) -> str:

    safe_query = urllib.parse.quote(
        str(query),
        safe="",
    )

    ext = (
        "mp4"
        if dl_type == "video"
        else "mp3"
    )

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
    return await download_assistant(
        link,
        "audio",
    )


async def download_video(link: str) -> str:
    return await download_assistant(
        link,
        "video",
    )


# =========================================================
# YOUTUBE CLASS
# =========================================================

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


    # =====================================================
    # HTTP CLIENT
    # =====================================================

    async def get_client(self):

        if (
            self._client is None
            or self._client.is_closed
        ):
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    30.0,
                    connect=10.0,
                ),
                follow_redirects=True,
            )

        return self._client


    # =====================================================
    # CHECK YOUTUBE URL
    # =====================================================

    async def exists(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        return bool(
            re.search(
                self.regex,
                str(link),
                re.IGNORECASE,
            )
        )


    # =====================================================
    # EXTRACT URL FROM TELEGRAM MESSAGE
    # =====================================================

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

                text = (
                    message.text
                    or message.caption
                    or ""
                )

                for entity in message.entities:

                    if (
                        entity.type
                        == MessageEntityType.URL
                    ):

                        return text[
                            entity.offset:
                            entity.offset
                            + entity.length
                        ]

                    if (
                        entity.type
                        == MessageEntityType.TEXT_LINK
                    ):
                        return entity.url

            if message.caption_entities:

                text = (
                    message.caption
                    or ""
                )

                for entity in (
                    message.caption_entities
                ):

                    if (
                        entity.type
                        == MessageEntityType.TEXT_LINK
                    ):
                        return entity.url

                    if (
                        entity.type
                        == MessageEntityType.URL
                    ):

                        return text[
                            entity.offset:
                            entity.offset
                            + entity.length
                        ]

        return None


    # =====================================================
    # CLEAN URL
    # =====================================================

    def _clean_link(
        self,
        link,
    ):

        if not link:
            return ""

        link = str(link).strip()

        link = re.sub(
            r"[&?](?:si|feature|pp|spm|"
            r"ab_channel)=[^&]+",
            "",
            link,
            flags=re.IGNORECASE,
        )

        return link


    # =====================================================
    # VIDEO ID
    # =====================================================

    def _get_video_id(
        self,
        link,
    ):

        if not link:
            return None

        link = str(link).strip()

        patterns = [
            r"(?:youtube\.com/watch\?v=)([^&\s]{11})",
            r"(?:youtu\.be/)([^?\s]{11})",
            r"(?:youtube\.com/shorts/)([^?\s]{11})",
            r"(?:youtube\.com/embed/)([^?\s]{11})",
            r"(?:youtube\.com/v/)([^?\s]{11})",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                link,
                re.IGNORECASE,
            )

            if match:
                return match.group(1)

        if re.fullmatch(
            r"[A-Za-z0-9_-]{11}",
            link,
        ):
            return link

        return None


    # =====================================================
    # YT-DLP INFO
    # =====================================================

    async def _yt_info(
        self,
        link,
        video=False,
    ):

        link = self._clean_link(link)

        if not link:
            return None

        loop = asyncio.get_running_loop()

        if video:
            format_selector = (
                "best[ext=mp4]/"
                "bestvideo+bestaudio/"
                "best"
            )
        else:
            format_selector = (
                "bestaudio[ext=m4a]/"
                "bestaudio/"
                "best"
            )

        options = _base_ydl_options()

        options.update({
            "format": format_selector,
            "skip_download": True,
            "noplaylist": True,
        })

        try:

            return await loop.run_in_executor(
                None,
                lambda: _extract_info_sync(
                    link,
                    options,
                ),
            )

        except Exception as e:

            LOGGER(__name__).warning(
                f"yt-dlp info failed: {e}"
            )

            return None


    # =====================================================
    # DETAILS
    # =====================================================

    async def _fetch_details(
        self,
        link,
    ):

        link = self._clean_link(link)

        info = await self._yt_info(
            link,
            video=False,
        )

        if info:

            duration = info.get(
                "duration",
                0,
            ) or 0

            try:
                duration = int(duration)
            except Exception:
                duration = 0

            title = info.get(
                "title"
            )

            thumbnail = info.get(
                "thumbnail"
            )

            vidid = info.get(
                "id"
            )

            return {
                "title": title,
                "duration_sec": duration,
                "duration_min": (
                    self._seconds_to_time(
                        duration
                    )
                    if duration
                    else "00:00"
                ),
                "thumbnail": thumbnail,
                "vidid": vidid,
                "link": (
                    self.base + vidid
                    if vidid
                    else link
                ),
            }

        # -------------------------------------------------
        # API FALLBACK
        # -------------------------------------------------

        if not API_URL:
            return None

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

                if isinstance(
                    data,
                    dict,
                ):
                    return data

        except Exception as e:

            LOGGER(__name__).warning(
                f"API details failed: {e}"
            )

        return None


    # =====================================================
    # SECONDS -> HH:MM:SS
    # =====================================================

    def _seconds_to_time(
        self,
        seconds,
    ):

        try:
            seconds = int(seconds)
        except Exception:
            return "00:00"

        hours = seconds // 3600
        minutes = (
            seconds % 3600
        ) // 60
        secs = seconds % 60

        if hours:
            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{secs:02d}"
            )

        return (
            f"{minutes:02d}:"
            f"{secs:02d}"
        )


    # =====================================================
    # DETAILS PUBLIC
    # =====================================================

    async def details(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        data = await self._fetch_details(
            link
        )

        if data:

            return (
                data.get("title"),
                data.get("duration_min"),
                data.get(
                    "duration_sec",
                    0,
                ),
                data.get("thumbnail"),
                data.get("vidid"),
            )

        return (
            None,
            None,
            0,
            None,
            None,
        )


    # =====================================================
    # TITLE
    # =====================================================

    async def title(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        data = await self._fetch_details(
            link
        )

        return (
            data.get("title")
            if data
            else None
        )


    # =====================================================
    # DURATION
    # =====================================================

    async def duration(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        data = await self._fetch_details(
            link
        )

        if not data:
            return None

        duration = data.get(
            "duration_min"
        )

        if duration:
            return duration

        seconds = data.get(
            "duration_sec",
            0,
        )

        return self._seconds_to_time(
            seconds
        )


    # =====================================================
    # THUMBNAIL
    # =====================================================

    async def thumbnail(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        data = await self._fetch_details(
            link
        )

        return (
            data.get("thumbnail")
            if data
            else None
        )


    # =====================================================
    # VIDEO STREAM
    # =====================================================

    async def video(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        try:

            stream_url, status = (
                await self.download(
                    link,
                    None,
                    video=True,
                )
            )

            if status:
                return 1, stream_url

            return (
                0,
                "Video URL generation failed",
            )

        except Exception as e:

            LOGGER(__name__).error(
                f"Video stream error: {e}"
            )

            return (
                0,
                f"Video URL generation error: {e}",
            )


    # =====================================================
    # DIRECT STREAM URL
    # =====================================================

    async def _get_stream_url(
        self,
        link,
        video=False,
    ):

        link = self._clean_link(link)

        loop = asyncio.get_running_loop()

        if video:

            format_selector = (
                "best[ext=mp4][protocol^=http]/"
                "best[protocol^=http]/"
                "best"
            )

        else:

            format_selector = (
                "bestaudio[ext=m4a][protocol^=http]/"
                "bestaudio[protocol^=http]/"
                "bestaudio/best"
            )

        options = _base_ydl_options()

        options.update({
            "format": format_selector,
            "noplaylist": True,
            "skip_download": True,
        })

        try:

            info = await loop.run_in_executor(
                None,
                lambda: _extract_info_sync(
                    link,
                    options,
                ),
            )

            if not info:
                return None

            # Sometimes yt-dlp returns direct URL
            direct_url = info.get(
                "url"
            )

            if direct_url:
                return direct_url

            formats = info.get(
                "formats",
                [],
            )

            # Prefer formats containing direct URL
            candidates = [
                fmt
                for fmt in formats
                if fmt.get("url")
            ]

            if not candidates:
                return None

            if video:

                candidates.sort(
                    key=lambda x: (
                        x.get(
                            "height",
                            0,
                        ) or 0,
                        x.get(
                            "tbr",
                            0,
                        ) or 0,
                    ),
                    reverse=True,
                )

            else:

                candidates.sort(
                    key=lambda x: (
                        x.get(
                            "abr",
                            0,
                        ) or 0,
                        x.get(
                            "asr",
                            0,
                        ) or 0,
                    ),
                    reverse=True,
                )

            return candidates[0].get(
                "url"
            )

        except Exception as e:

            LOGGER(__name__).warning(
                f"Direct yt-dlp stream failed: {e}"
            )

            return None


    # =====================================================
    # DOWNLOAD / STREAM
    # =====================================================

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

        dl_type_video = bool(
            video or songvideo
        )

        # -------------------------------------------------
        # PRIMARY: DIRECT YT-DLP
        # -------------------------------------------------

        stream_url = await self._get_stream_url(
            link,
            video=dl_type_video,
        )

        if stream_url:
            return stream_url, True

        # -------------------------------------------------
        # FALLBACK: API
        # -------------------------------------------------

        try:

            dl_type = (
                "video"
                if dl_type_video
                else "audio"
            )

            fallback_url = (
                await download_assistant(
                    link,
                    dl_type,
                )
            )

            if fallback_url:
                return fallback_url, True

        except Exception as e:

            LOGGER(__name__).error(
                f"API fallback failed: {e}"
            )

        return (
            None,
            False,
        )


    # =====================================================
    # AUTOPLAY / RELATED VIDEOS
    # =====================================================

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

        ydl_opts = _base_ydl_options()

        ydl_opts.update({
            "extract_flat": True,
            "playlist_items": "1-20",
            "noplaylist": False,
        })

        try:

            loop = asyncio.get_running_loop()

            info = await loop.run_in_executor(
                None,
                lambda: _extract_info_sync(
                    url,
                    ydl_opts,
                ),
            )

            if info and "entries" in info:

                ids = []

                for entry in info["entries"]:

                    if not entry:
                        continue

                    video_id = entry.get(
                        "id"
                    )

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
                        and duration
                        > autoplay_limit
                    ):
                        continue

                    ids.append(
                        video_id
                    )

                if ids:
                    return ids

        except Exception as e:

            LOGGER(__name__).warning(
                f"YouTube radio failed: {e}"
            )

        # -------------------------------------------------
        # SEARCH FALLBACK
        # -------------------------------------------------

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

                    video_id = result.get(
                        "id"
                    )

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

                    related.append(
                        video_id
                    )

                if related:
                    return related

            except Exception as e:

                LOGGER(__name__).warning(
                    f"YouTube search failed: {e}"
                )

        return []


    # =====================================================
    # TRACK
    # =====================================================

    async def track(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        data = await self._fetch_details(
            link
        )

        if data:

            vidid = data.get(
                "vidid"
            ) or data.get(
                "id"
            )

            track_details = {
                "title": data.get(
                    "title"
                ),
                "link": data.get(
                    "link",
                    self.base + vidid
                    if vidid
                    else link,
                ),
                "vidid": vidid,
                "duration_min": data.get(
                    "duration_min"
                ),
                "thumb": data.get(
                    "thumbnail"
                ),
            }

            return (
                track_details,
                vidid,
            )

        # -------------------------------------------------
        # FINAL YT-DLP FALLBACK
        # -------------------------------------------------

        info = await self._yt_info(
            link,
            video=False,
        )

        if info:

            vidid = info.get(
                "id"
            )

            duration = info.get(
                "duration",
                0,
            ) or 0

            track_details = {
                "title": info.get(
                    "title"
                ),
                "link": (
                    self.base + vidid
                    if vidid
                    else link
                ),
                "vidid": vidid,
                "duration_min": (
                    self._seconds_to_time(
                        duration
                    )
                ),
                "thumb": info.get(
                    "thumbnail"
                ),
            }

            return (
                track_details,
                vidid,
            )

        return None, None


    # =====================================================
    # PREFETCH
    # =====================================================

    async def prefetch(
        self,
        link,
        video=False,
    ):

        # Direct yt-dlp extraction is already fast.
        # Kept only for compatibility.

        try:

            asyncio.create_task(
                self._get_stream_url(
                    link,
                    video=video,
                )
            )

            return True

        except Exception as e:

            LOGGER(__name__).warning(
                f"Prefetch failed: {e}"
            )

            return False


    # =====================================================
    # FORMATS
    # =====================================================

    async def formats(
        self,
        link,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        link = self._clean_link(link)

        loop = asyncio.get_running_loop()

        options = _base_ydl_options()

        options.update({
            "skip_download": True,
            "noplaylist": True,
        })

        try:

            info = await loop.run_in_executor(
                None,
                lambda: _extract_info_sync(
                    link,
                    options,
                ),
            )

            if not info:
                return [], link

            formats = []

            for fmt in info.get(
                "formats",
                [],
            ):

                if not fmt.get("url"):
                    continue

                formats.append({
                    "format_id": fmt.get(
                        "format_id"
                    ),
                    "ext": fmt.get(
                        "ext"
                    ),
                    "format": fmt.get(
                        "format"
                    ),
                    "filesize": fmt.get(
                        "filesize"
                    ),
                    "height": fmt.get(
                        "height"
                    ),
                    "width": fmt.get(
                        "width"
                    ),
                    "fps": fmt.get(
                        "fps"
                    ),
                    "tbr": fmt.get(
                        "tbr"
                    ),
                    "abr": fmt.get(
                        "abr"
                    ),
                    "vcodec": fmt.get(
                        "vcodec"
                    ),
                    "acodec": fmt.get(
                        "acodec"
                    ),
                    "yturl": link,
                    "url": fmt.get(
                        "url"
                    ),
                })

            return formats, link

        except Exception as e:

            LOGGER(__name__).error(
                f"Formats error: {e}"
            )

        return [], link


    # =====================================================
    # PLAYLIST
    # =====================================================

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

        loop = asyncio.get_running_loop()

        options = _base_ydl_options()

        options.update({
            "extract_flat": True,
            "playlistend": int(limit),
            "noplaylist": False,
        })

        try:

            info = await loop.run_in_executor(
                None,
                lambda: _extract_info_sync(
                    link,
                    options,
                ),
            )

            if not info:
                return None

            videos = []

            for entry in info.get(
                "entries",
                [],
            ):

                if not entry:
                    continue

                video_id = entry.get(
                    "id"
                )

                if not video_id:
                    continue

                videos.append({
                    "title": entry.get(
                        "title"
                    ),
                    "id": video_id,
                    "url": (
                        self.base
                        + video_id
                    ),
                    "duration": entry.get(
                        "duration"
                    ),
                    "thumbnail": (
                        entry.get(
                            "thumbnail"
                        )
                        or
                        f"https://i.ytimg.com/vi/"
                        f"{video_id}/hqdefault.jpg"
                    ),
                })

            return videos

        except Exception as e:

            LOGGER(__name__).error(
                f"Playlist error: {e}"
            )

        return None


    # =====================================================
    # SEARCH SLIDER
    # =====================================================

    async def slider(
        self,
        link,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        link = self._clean_link(link)

        try:

            results = VideosSearch(
                link,
                limit=10,
            )

            data = await results.next()

            result = data.get(
                "result",
                [],
            )

            if (
                not result
                or len(result)
                <= query_type
            ):
                return (
                    None,
                    None,
                    None,
                    None,
                )

            item = result[
                query_type
            ]

            video_id = item.get(
                "id"
            )

            thumb = item.get(
                "thumbnails",
                [],
            )

            thumbnail = (
                thumb[0].get("url")
                if thumb
                else (
                    f"https://i.ytimg.com/vi/"
                    f"{video_id}/hqdefault.jpg"
                    if video_id
                    else None
                )
            )

            return (
                item.get("title"),
                item.get("duration"),
                thumbnail,
                video_id,
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


    # =====================================================
    # CLOSE CLIENT
    # =====================================================

    async def close(self):

        if (
            self._client
            and not self._client.is_closed
        ):
            await self._client.aclose()
            self._client = None
