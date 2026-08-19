#
# Copyright (C) 2021-2022 by TheAloneteam@Github
# GNU General Public License v3.0
#

import asyncio
import os
import re
from typing import Union
from urllib.parse import parse_qs, urlparse

import aiohttp
import yt_dlp

import config


# ==========================================================
# CONFIG
# ==========================================================

API_URL = os.environ.get(
    "SHRUTI_API_URL",
    "https://api01.shrutibots.site",
)

# IMPORTANT:
# API key ko environment variable me rakho.
API_KEY = os.environ.get(
    "SHRUTI_API_KEY",
    "",
)

DOWNLOAD_DIR = "downloads"


# ==========================================================
# HELPERS
# ==========================================================

def time_to_seconds(value):
    """
    Convert:
        1:20 -> 80
        10:30 -> 630
        1:02:30 -> 3750
    """
    if value is None:
        return 0

    try:
        value = str(value).strip()

        if not value:
            return 0

        parts = value.split(":")

        total = 0

        for part in parts:
            total = total * 60 + int(part)

        return total

    except Exception:
        return 0


def clean_youtube_url(url: str) -> str:
    """
    Convert different YouTube URLs into a clean watch URL.
    """

    if not url:
        return ""

    url = str(url).strip()

    # Remove Telegram / text garbage
    url = url.strip("<>[](){}")

    # Add protocol if missing
    if url.startswith("www.youtube.com"):
        url = "https://" + url

    if url.startswith("youtube.com"):
        url = "https://" + url

    if url.startswith("youtu.be"):
        url = "https://" + url

    # youtu.be/VIDEO_ID
    match = re.search(
        r"(?:https?://)?(?:www\.)?youtu\.be/([A-Za-z0-9_-]{6,})",
        url,
    )

    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"

    # /shorts/VIDEO_ID
    match = re.search(
        r"(?:youtube\.com)/shorts/([A-Za-z0-9_-]{6,})",
        url,
        re.I,
    )

    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"

    # /live/VIDEO_ID
    match = re.search(
        r"(?:youtube\.com)/live/([A-Za-z0-9_-]{6,})",
        url,
        re.I,
    )

    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"

    # /embed/VIDEO_ID
    match = re.search(
        r"(?:youtube\.com)/embed/([A-Za-z0-9_-]{6,})",
        url,
        re.I,
    )

    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"

    # Normal youtube.com/watch?v=
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        if "v" in query and query["v"]:
            video_id = query["v"][0]

            if re.fullmatch(r"[A-Za-z0-9_-]{6,}", video_id):
                return f"https://www.youtube.com/watch?v={video_id}"

    except Exception:
        pass

    return url


def extract_video_id(url: str):
    """
    Extract YouTube video ID.
    """

    if not url:
        return None

    url = str(url).strip()

    # youtu.be
    match = re.search(
        r"(?:youtu\.be/)([A-Za-z0-9_-]{6,})",
        url,
        re.I,
    )

    if match:
        return match.group(1)

    # watch?v=
    try:
        parsed = urlparse(url)

        query = parse_qs(parsed.query)

        if "v" in query and query["v"]:
            video_id = query["v"][0]

            if re.fullmatch(r"[A-Za-z0-9_-]{6,}", video_id):
                return video_id

    except Exception:
        pass

    # shorts/live/embed
    match = re.search(
        r"youtube\.com/(?:shorts|live|embed)/([A-Za-z0-9_-]{6,})",
        url,
        re.I,
    )

    if match:
        return match.group(1)

    # Raw video ID
    if re.fullmatch(r"[A-Za-z0-9_-]{6,}", url):
        return url

    return None


def youtube_watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


# ==========================================================
# DOWNLOAD
# ==========================================================

async def _download_from_api(
    link: str,
    media_type: str,
    timeout_seconds: int,
):
    """
    Download audio/video using external API.
    """

    if not link:
        return None

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    video_id = extract_video_id(link)

    if not video_id:
        return None

    extension = "mp3" if media_type == "audio" else "mp4"

    file_path = os.path.join(
        DOWNLOAD_DIR,
        f"{video_id}.{extension}",
    )

    if os.path.exists(file_path):
        try:
            if os.path.getsize(file_path) > 0:
                return file_path
        except Exception:
            pass

    # IMPORTANT:
    # Full YouTube URL API ko bhejna hai.
    youtube_url = youtube_watch_url(video_id)

    params = {
        "url": youtube_url,
        "type": media_type,
    }

    if API_KEY:
        params["api_key"] = API_KEY

    try:
        timeout = aiohttp.ClientTimeout(
            total=timeout_seconds
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(
                f"{API_URL.rstrip('/')}/download",
                params=params,
            ) as response:

                if response.status != 200:
                    return None

                content_type = (
                    response.headers.get(
                        "Content-Type",
                        "",
                    ).lower()
                )

                # API kabhi JSON error return kar sakti hai
                if "application/json" in content_type:
                    return None

                with open(file_path, "wb") as file:

                    async for chunk in response.content.iter_chunked(
                        128 * 1024
                    ):
                        if chunk:
                            file.write(chunk)

        if (
            os.path.exists(file_path)
            and os.path.getsize(file_path) > 0
        ):
            return file_path

    except Exception as e:
        print(
            f"[YouTube API Download Error] "
            f"{type(e).__name__}: {e}"
        )

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

    return None


async def download_song(link: str) -> str:
    return await _download_from_api(
        link,
        "audio",
        600,
    )


async def download_video(link: str) -> str:
    return await _download_from_api(
        link,
        "video",
        900,
    )


# ==========================================================
# YOUTUBE API CLASS
# ==========================================================

class YouTubeAPI:

    def __init__(self):

        self.base = (
            "https://www.youtube.com/watch?v="
        )

        self.regex = re.compile(
            r"(?:youtube\.com|youtu\.be)",
            re.I,
        )

        self.status = (
            "https://www.youtube.com/oembed?url="
        )

        self.listbase = (
            "https://youtube.com/playlist?list="
        )

        self.reg = re.compile(
            r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
        )

    # ======================================================
    # EXISTS
    # ======================================================

    async def exists(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if not link:
            return False

        if videoid:
            link = self.base + str(link)

        return bool(
            self.regex.search(str(link))
        )

    # ======================================================
    # URL FROM TELEGRAM MESSAGE
    # ======================================================

    async def url(
        self,
        message_1: "Message",
    ) -> Union[str, None]:

        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(
                message_1.reply_to_message
            )

        for message in messages:

            # Message text
            text = (
                message.text
                or message.caption
                or ""
            )

            # entities
            entities = (
                message.entities
                or message.caption_entities
                or []
            )

            for entity in entities:

                try:

                    # Telegram clickable URL
                    if entity.type == "text_link":
                        if entity.url:
                            return entity.url

                    # Normal URL
                    if entity.type == "url":
                        return text[
                            entity.offset:
                            entity.offset + entity.length
                        ]

                except Exception:
                    continue

            # Fallback regex
            match = re.search(
                r"https?://(?:www\.)?"
                r"(?:youtube\.com|youtu\.be)"
                r"/[^\s]+",
                text,
                re.I,
            )

            if match:
                return match.group(0)

        return None

    # ======================================================
    # YT-DLP EXTRACT
    # ======================================================

    async def _extract(
        self,
        link: str,
        flat: bool = False,
    ):

        link = clean_youtube_url(link)

        if not link:
            raise ValueError(
                "Invalid YouTube URL"
            )

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "ignoreerrors": False,
        }

        if flat:
            ydl_opts["extract_flat"] = True

        loop = asyncio.get_running_loop()

        def extract():

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:

                return ydl.extract_info(
                    link,
                    download=False,
                )

        return await loop.run_in_executor(
            None,
            extract,
        )

    # ======================================================
    # SEARCH
    # ======================================================

    async def _search(
        self,
        query: str,
        limit: int = 10,
    ):

        if not query:
            return []

        # Direct YouTube URL
        if await self.exists(query):

            try:

                info = await self._extract(
                    query,
                    flat=True,
                )

                if info:
                    return [info]

            except Exception as e:

                print(
                    f"[YouTube Direct Error] "
                    f"{type(e).__name__}: {e}"
                )

        search_query = (
            f"ytsearch{limit}:{query}"
        )

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
        }

        loop = asyncio.get_running_loop()

        def search():

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:

                data = ydl.extract_info(
                    search_query,
                    download=False,
                )

                return data or {}

        data = await loop.run_in_executor(
            None,
            search,
        )

        return data.get("entries") or []

    # ======================================================
    # DETAILS
    # ======================================================

    async def details(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + str(link)

        info_list = await self._search(
            link,
            limit=1,
        )

        if not info_list:
            raise ValueError(
                "YouTube video not found"
            )

        result = info_list[0]

        title = (
            result.get("title")
            or "Unknown Title"
        )

        duration_sec = int(
            result.get("duration")
            or 0
        )

        duration_min = (
            seconds_to_duration(
                duration_sec
            )
            if duration_sec
            else None
        )

        thumbnail = (
            result.get("thumbnail")
            or ""
        )

        vidid = (
            result.get("id")
            or extract_video_id(link)
        )

        if not vidid:
            raise ValueError(
                "YouTube video ID not found"
            )

        return (
            title,
            duration_min,
            duration_sec,
            thumbnail,
            vidid,
        )

    # ======================================================
    # TITLE
    # ======================================================

    async def title(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + str(link)

        info_list = await self._search(
            link,
            limit=1,
        )

        if not info_list:
            return None

        return info_list[0].get(
            "title"
        )

    # ======================================================
    # DURATION
    # ======================================================

    async def duration(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + str(link)

        info_list = await self._search(
            link,
            limit=1,
        )

        if not info_list:
            return None

        duration_sec = int(
            info_list[0].get(
                "duration"
            )
            or 0
        )

        return (
            seconds_to_duration(
                duration_sec
            )
            if duration_sec
            else None
        )

    # ======================================================
    # THUMBNAIL
    # ======================================================

    async def thumbnail(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + str(link)

        info_list = await self._search(
            link,
            limit=1,
        )

        if not info_list:
            return None

        return info_list[0].get(
            "thumbnail"
        )

    # ======================================================
    # VIDEO
    # ======================================================

    async def video(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + str(link)

        try:

            file_path = await download_video(
                clean_youtube_url(link)
            )

            if file_path:
                return 1, file_path

            return 0, "Video download failed"

        except Exception as e:

            return (
                0,
                f"Video download error: "
                f"{type(e).__name__}: {e}",
            )

    # ======================================================
    # PLAYLIST
    # ======================================================

    async def playlist(
        self,
        link,
        limit,
        user_id,
        videoid: Union[bool, str] = None,
    ):

        try:

            if videoid:
                link = (
                    self.listbase
                    + str(link)
                )

            if not link:
                return []

            link = str(link).strip()

            # Playlist URL ko unnecessarily clean
            # nahi karna
            if "playlist" not in link.lower():

                if "list=" not in link:
                    return []

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "skip_download": True,
                "playlistend": int(limit),
            }

            loop = asyncio.get_running_loop()

            def extract_playlist():

                with yt_dlp.YoutubeDL(
                    ydl_opts
                ) as ydl:

                    return ydl.extract_info(
                        link,
                        download=False,
                    )

            info = await loop.run_in_executor(
                None,
                extract_playlist,
            )

            if not info:
                return []

            ids = []

            for entry in (
                info.get("entries")
                or []
            ):

                if not entry:
                    continue

                vid = entry.get("id")

                if (
                    vid
                    and vid not in ids
                ):
                    ids.append(vid)

                if len(ids) >= int(limit):
                    break

            return ids

        except Exception as e:

            print(
                f"[YouTube Playlist Error] "
                f"{type(e).__name__}: {e}"
            )

            return []

    # ======================================================
    # RELATED / AUTOPLAY
    # ======================================================

    async def get_related_videos(
        self,
        vidid: str,
    ):

        """
        Autoplay ke liye related YouTube videos.

        1. YouTube Mix
        2. Search fallback
        """

        if not vidid:
            return []

        try:

            configured_limit = int(
                getattr(
                    config,
                    "DURATION_LIMIT",
                    600,
                )
            )

        except Exception:

            configured_limit = 600

        autoplay_limit = min(
            configured_limit,
            600,
        )

        related = []

        # ==================================================
        # METHOD 1: YOUTUBE MIX
        # ==================================================

        mix_url = (
            f"https://www.youtube.com/watch?v="
            f"{vidid}&list=RD{vidid}"
        )

        try:

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "skip_download": True,
                "playlist_items": "2-20",
            }

            loop = asyncio.get_running_loop()

            def get_mix():

                with yt_dlp.YoutubeDL(
                    ydl_opts
                ) as ydl:

                    return ydl.extract_info(
                        mix_url,
                        download=False,
                    )

            info = await loop.run_in_executor(
                None,
                get_mix,
            )

            if info:

                for entry in (
                    info.get("entries")
                    or []
                ):

                    if not entry:
                        continue

                    candidate = entry.get(
                        "id"
                    )

                    if not candidate:
                        continue

                    if candidate == vidid:
                        continue

                    if candidate in related:
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

                    related.append(
                        candidate
                    )

                    if len(related) >= 10:
                        break

        except Exception as e:

            print(
                f"[YouTube Mix Error] "
                f"{type(e).__name__}: {e}"
            )

        if related:
            return related

        # ==================================================
        # METHOD 2: TITLE SEARCH FALLBACK
        # ==================================================

        try:

            current_title = await self.title(
                vidid,
                True,
            )

            if not current_title:
                return []

            search_query = (
                f"{current_title} "
                f"official audio"
            )

            results = await self._search(
                search_query,
                limit=10,
            )

            for entry in results:

                if not entry:
                    continue

                candidate = entry.get(
                    "id"
                )

                if not candidate:
                    continue

                if candidate == vidid:
                    continue

                if candidate in related:
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

                related.append(
                    candidate
                )

                if len(related) >= 10:
                    break

        except Exception as e:

            print(
                f"[YouTube Related Error] "
                f"{type(e).__name__}: {e}"
            )

        return related

    # ======================================================
    # TRACK
    # ======================================================

    async def track(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if not link:
            raise ValueError(
                "Empty YouTube query"
            )

        if videoid:
            link = self.base + str(link)

        info_list = await self._search(
            link,
            limit=1,
        )

        if not info_list:
            raise ValueError(
                "No YouTube result found"
            )

        result = info_list[0]

        title = (
            result.get("title")
            or "Unknown Title"
        )

        duration_sec = int(
            result.get("duration")
            or 0
        )

        duration_min = (
            seconds_to_duration(
                duration_sec
            )
            if duration_sec
            else None
        )

        vidid = (
            result.get("id")
            or extract_video_id(link)
        )

        if not vidid:
            raise ValueError(
                "YouTube video ID missing"
            )

        yturl = (
            result.get("webpage_url")
            or youtube_watch_url(
                vidid
            )
        )

        thumbnail = (
            result.get("thumbnail")
            or f"https://i.ytimg.com/vi/"
            f"{vidid}/hqdefault.jpg"
        )

        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }

        return (
            track_details,
            vidid,
        )

    # ======================================================
    # FORMATS
    # ======================================================

    async def formats(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + str(link)

        link = clean_youtube_url(link)

        ytdl_opts = {
            "quiet": True,
            "no_warnings": True,
        }

        loop = asyncio.get_running_loop()

        def get_formats():

            with yt_dlp.YoutubeDL(
                ytdl_opts
            ) as ydl:

                return ydl.extract_info(
                    link,
                    download=False,
                )

        result = await loop.run_in_executor(
            None,
            get_formats,
        )

        formats_available = []

        for fmt in (
            result.get("formats")
            or []
        ):

            try:

                format_string = str(
                    fmt.get("format")
                    or ""
                )

                if "dash" in format_string.lower():
                    continue

                formats_available.append(
                    {
                        "format": format_string,
                        "filesize": fmt.get(
                            "filesize"
                        ),
                        "format_id": fmt.get(
                            "format_id"
                        ),
                        "ext": fmt.get(
                            "ext"
                        ),
                        "format_note": fmt.get(
                            "format_note"
                        ),
                        "yturl": link,
                    }
                )

            except Exception:
                continue

        return (
            formats_available,
            link,
        )

    # ======================================================
    # SLIDER
    # ======================================================

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + str(link)

        results = await self._search(
            link,
            limit=10,
        )

        if not results:
            raise ValueError(
                "No YouTube search results"
            )

        query_type = int(query_type)

        if query_type < 0:
            query_type = 0

        if query_type >= len(results):
            query_type = len(results) - 1

        result = results[query_type]

        title = (
            result.get("title")
            or "Unknown Title"
        )

        duration_sec = int(
            result.get("duration")
            or 0
        )

        duration_min = (
            seconds_to_duration(
                duration_sec
            )
            if duration_sec
            else None
        )

        vidid = result.get(
            "id"
        )

        thumbnail = (
            result.get("thumbnail")
            or (
                f"https://i.ytimg.com/vi/"
                f"{vidid}/hqdefault.jpg"
            )
        )

        return (
            title,
            duration_min,
            thumbnail,
            vidid,
        )

    # ======================================================
    # DOWNLOAD
    # ======================================================

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> tuple:

        try:

            if videoid:
                link = self.base + str(link)

            link = clean_youtube_url(link)

            if not link:
                return None, False

            if video:
                downloaded_file = (
                    await download_video(
                        link
                    )
                )

            else:
                downloaded_file = (
                    await download_song(
                        link
                    )
                )

            if downloaded_file:
                return (
                    downloaded_file,
                    True,
                )

            return (
                None,
                False,
            )

        except Exception as e:

            print(
                f"[YouTube Download Error] "
                f"{type(e).__name__}: {e}"
            )

            return (
                None,
                False,
            )


# ==========================================================
# DURATION FORMATTER
# ==========================================================

def seconds_to_duration(seconds: int):

    try:
        seconds = int(seconds)

        hours, remainder = divmod(
            seconds,
            3600,
        )

        minutes, seconds = divmod(
            remainder,
            60,
        )

        if hours:
            return (
                f"{hours}:"
                f"{minutes:02d}:"
                f"{seconds:02d}"
            )

        return (
            f"{minutes}:"
            f"{seconds:02d}"
        )

    except Exception:
        return None


# ==========================================================
# GLOBAL INSTANCE
# ==========================================================

YouTube = YouTubeAPI()
