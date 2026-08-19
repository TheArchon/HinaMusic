#
# YouTube helper for AloneMusic
# Fixed YouTube URL handling + autoplay related videos
#

import asyncio
import os
import re
from typing import Optional, Union
from urllib.parse import parse_qs, urlparse

import aiohttp
import yt_dlp
from py_yt import VideosSearch
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

import config


API_URL = os.environ.get(
    "SHRUTI_API_URL",
    "https://api01.shrutibots.site",
)

# IMPORTANT:
# Put your NEW API key in environment variable.
API_KEY = os.environ.get("SHRUTI_API_KEY", "")

DOWNLOAD_DIR = "downloads"


# =========================================================
# HELPERS
# =========================================================

def time_to_seconds(time):
    if not time:
        return 0

    try:
        stringt = str(time)
        return sum(
            int(x) * 60 ** i
            for i, x in enumerate(reversed(stringt.split(":")))
        )
    except Exception:
        return 0


def extract_video_id(link: str) -> Optional[str]:
    """
    Extract YouTube video ID from:
      youtube.com/watch?v=xxxx
      www.youtube.com/watch?v=xxxx
      youtu.be/xxxx
      youtube.com/shorts/xxxx
      youtube.com/embed/xxxx
      youtube.com/live/xxxx
      plain video ID
    """

    if not link:
        return None

    link = str(link).strip()

    # Already a video ID
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", link):
        return link

    try:
        parsed = urlparse(link)
        host = parsed.netloc.lower().replace("www.", "")

        # youtu.be/VIDEO_ID
        if host == "youtu.be":
            video_id = parsed.path.strip("/").split("/")[0]
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                return video_id

        # youtube.com
        if "youtube.com" in host:

            # /watch?v=VIDEO_ID
            query = parse_qs(parsed.query)
            video_id = query.get("v", [None])[0]

            if video_id and re.fullmatch(
                r"[A-Za-z0-9_-]{11}",
                video_id,
            ):
                return video_id

            # /shorts/VIDEO_ID
            # /embed/VIDEO_ID
            # /live/VIDEO_ID
            parts = [
                x for x in parsed.path.split("/")
                if x
            ]

            if len(parts) >= 2:
                if parts[0].lower() in {
                    "shorts",
                    "embed",
                    "live",
                }:
                    video_id = parts[1]

                    if re.fullmatch(
                        r"[A-Za-z0-9_-]{11}",
                        video_id,
                    ):
                        return video_id

    except Exception:
        pass

    # Last fallback
    match = re.search(
        r"(?:v=|youtu\.be/|shorts/|embed/|live/)"
        r"([A-Za-z0-9_-]{11})",
        link,
    )

    if match:
        return match.group(1)

    return None


def clean_youtube_url(link: str) -> str:
    """
    Return clean YouTube watch URL.
    """

    video_id = extract_video_id(link)

    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"

    return str(link).strip()


# =========================================================
# DOWNLOAD
# =========================================================

async def _download_from_api(
    link: str,
    media_type: str,
    timeout_seconds: int,
) -> Optional[str]:

    video_id = extract_video_id(link)

    if not video_id:
        return None

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    extension = "mp3" if media_type == "audio" else "mp4"

    file_path = os.path.join(
        DOWNLOAD_DIR,
        f"{video_id}.{extension}",
    )

    if (
        os.path.exists(file_path)
        and os.path.getsize(file_path) > 0
    ):
        return file_path

    if not API_KEY:
        return None

    try:
        async with aiohttp.ClientSession() as session:

            async with session.get(
                f"{API_URL}/download",
                params={
                    "url": video_id,
                    "type": media_type,
                    "api_key": API_KEY,
                },
                timeout=aiohttp.ClientTimeout(
                    total=timeout_seconds
                ),
            ) as resp:

                if resp.status != 200:
                    return None

                content_type = (
                    resp.headers.get("Content-Type", "")
                    .lower()
                )

                # Don't save API error JSON as mp3/mp4.
                if (
                    "application/json" in content_type
                    or "text/" in content_type
                ):
                    return None

                with open(file_path, "wb") as f:

                    async for chunk in resp.content.iter_chunked(
                        131072
                    ):
                        if chunk:
                            f.write(chunk)

        if (
            os.path.exists(file_path)
            and os.path.getsize(file_path) > 0
        ):
            return file_path

    except Exception:
        pass

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

    return None


async def download_song(link: str) -> Optional[str]:
    return await _download_from_api(
        link,
        "audio",
        300,
    )


async def download_video(link: str) -> Optional[str]:
    return await _download_from_api(
        link,
        "video",
        600,
    )


# =========================================================
# YOUTUBE API
# =========================================================

class YouTubeAPI:

    def __init__(self):

        self.base = (
            "https://www.youtube.com/watch?v="
        )

        self.regex = re.compile(
            r"(youtube\.com|youtu\.be)",
            re.IGNORECASE,
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

    # =====================================================
    # EXISTS
    # =====================================================

    async def exists(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        if not link:
            return False

        if videoid:
            link = self.base + str(link)

        link = str(link).strip()

        return bool(
            self.regex.search(link)
        )

    # =====================================================
    # URL FROM TELEGRAM MESSAGE
    # =====================================================

    async def url(
        self,
        message_1: Message,
    ) -> Optional[str]:

        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(
                message_1.reply_to_message
            )

        for message in messages:

            # Normal URL entities
            entities = message.entities or []

            for entity in entities:

                if entity.type == MessageEntityType.URL:

                    text = (
                        message.text
                        or message.caption
                        or ""
                    )

                    return text[
                        entity.offset:
                        entity.offset + entity.length
                    ]

                if entity.type == MessageEntityType.TEXT_LINK:
                    return entity.url

            # Caption entities
            caption_entities = (
                message.caption_entities or []
            )

            for entity in caption_entities:

                if entity.type == MessageEntityType.TEXT_LINK:
                    return entity.url

                if entity.type == MessageEntityType.URL:

                    text = (
                        message.caption
                        or message.text
                        or ""
                    )

                    return text[
                        entity.offset:
                        entity.offset + entity.length
                    ]

        return None

    # =====================================================
    # SEARCH
    # =====================================================

    async def _search(
        self,
        query: str,
        limit: int = 1,
    ):

        results = VideosSearch(
            query,
            limit=limit,
        )

        data = await results.next()

        if not data:
            return []

        return data.get("result", []) or []

    # =====================================================
    # DETAILS
    # =====================================================

    async def details(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + str(link)

        extracted_id = extract_video_id(link)

        # Direct YouTube URL
        if extracted_id:

            clean_url = (
                self.base + extracted_id
            )

            try:
                data = await self._search(
                    clean_url,
                    1,
                )

                if data:

                    result = data[0]

                    title = result.get(
                        "title",
                        "Unknown",
                    )

                    duration_min = result.get(
                        "duration"
                    )

                    duration_sec = time_to_seconds(
                        duration_min
                    )

                    thumbnail = ""

                    thumbs = result.get(
                        "thumbnails"
                    ) or []

                    if thumbs:
                        thumbnail = (
                            thumbs[0]
                            .get("url", "")
                            .split("?")[0]
                        )

                    vidid = (
                        result.get("id")
                        or extracted_id
                    )

                    return (
                        title,
                        duration_min,
                        duration_sec,
                        thumbnail,
                        vidid,
                    )

            except Exception:
                pass

            # yt-dlp fallback
            try:
                loop = asyncio.get_running_loop()

                info = await loop.run_in_executor(
                    None,
                    lambda: self._extract_info(
                        clean_url
                    ),
                )

                if info:

                    title = info.get(
                        "title",
                        "Unknown",
                    )

                    duration_sec = int(
                        info.get("duration")
                        or 0
                    )

                    duration_min = (
                        self._seconds_to_duration(
                            duration_sec
                        )
                    )

                    thumbnail = (
                        info.get("thumbnail")
                        or ""
                    )

                    return (
                        title,
                        duration_min,
                        duration_sec,
                        thumbnail,
                        extracted_id,
                    )

            except Exception:
                pass

            raise RuntimeError(
                "Unable to fetch YouTube video"
            )

        # Normal search query
        data = await self._search(
            link,
            1,
        )

        if not data:
            raise RuntimeError(
                "No YouTube result found"
            )

        result = data[0]

        title = result.get(
            "title",
            "Unknown",
        )

        duration_min = result.get(
            "duration"
        )

        duration_sec = time_to_seconds(
            duration_min
        )

        thumbs = result.get(
            "thumbnails"
        ) or []

        thumbnail = ""

        if thumbs:
            thumbnail = (
                thumbs[0]
                .get("url", "")
                .split("?")[0]
            )

        vidid = result.get("id")

        return (
            title,
            duration_min,
            duration_sec,
            thumbnail,
            vidid,
        )

    # =====================================================
    # TITLE
    # =====================================================

    async def title(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        details = await self.details(
            link,
            videoid,
        )

        return details[0]

    # =====================================================
    # DURATION
    # =====================================================

    async def duration(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        details = await self.details(
            link,
            videoid,
        )

        return details[1]

    # =====================================================
    # THUMBNAIL
    # =====================================================

    async def thumbnail(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        details = await self.details(
            link,
            videoid,
        )

        return details[3]

    # =====================================================
    # VIDEO
    # =====================================================

    async def video(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + str(link)

        try:

            downloaded_file = (
                await download_video(link)
            )

            if downloaded_file:
                return (
                    1,
                    downloaded_file,
                )

            return (
                0,
                "Video download failed",
            )

        except Exception as e:

            return (
                0,
                f"Video download error: {e}",
            )

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
            link = self.listbase + str(link)

        link = str(link).strip()

        # Don't destroy playlist URL incorrectly.
        if "playlist" not in link.lower():
            if "list=" not in link.lower():
                link = (
                    self.listbase
                    + link
                )

        try:

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "skip_download": True,
                "playlistend": int(limit),
            }

            loop = asyncio.get_running_loop()

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:

                info = await loop.run_in_executor(
                    None,
                    lambda: ydl.extract_info(
                        link,
                        download=False,
                    ),
                )

            ids = []

            for entry in (
                info.get("entries") or []
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

        except Exception:
            return []

    # =====================================================
    # AUTOPLAY RELATED VIDEOS
    # =====================================================

    async def get_related_videos(
        self,
        vidid: str,
    ):
        """
        Return YouTube video IDs for autoplay.

        This function:
        1. Uses YouTube Mix/Radio.
        2. Filters long videos.
        3. Removes current video.
        4. Falls back to search.
        """

        if not vidid:
            return []

        # Make sure we have only video ID.
        extracted = extract_video_id(
            str(vidid)
        )

        if extracted:
            vidid = extracted

        # Duration limit.
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

        # Hard maximum for autoplay.
        autoplay_limit = min(
            configured_limit,
            600,
        )

        related = []

        # -------------------------------------------------
        # METHOD 1: YouTube Mix
        # -------------------------------------------------

        mix_url = (
            "https://www.youtube.com/watch?v="
            f"{vidid}&list=RD{vidid}"
        )

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "playlist_items": "1-30",
        }

        try:

            loop = asyncio.get_running_loop()

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:

                info = await loop.run_in_executor(
                    None,
                    lambda: ydl.extract_info(
                        mix_url,
                        download=False,
                    ),
                )

            entries = (
                info.get("entries")
                or []
            )

            for entry in entries:

                if not entry:
                    continue

                candidate = entry.get("id")

                if not candidate:
                    continue

                if candidate == vidid:
                    continue

                if candidate in related:
                    continue

                duration = entry.get(
                    "duration"
                )

                if duration:

                    try:
                        if (
                            float(duration)
                            > autoplay_limit
                        ):
                            continue
                    except Exception:
                        pass

                related.append(candidate)

                if len(related) >= 10:
                    break

        except Exception:
            pass

        if related:
            return related

        # -------------------------------------------------
        # METHOD 2: Current song title search
        # -------------------------------------------------

        try:

            current_title = await self.title(
                vidid,
                True,
            )

            if not current_title:
                return []

            # Remove common junk from title.
            search_query = (
                f"{current_title} "
                "official audio"
            )

            results = await self._search(
                search_query,
                10,
            )

            for result in results:

                candidate = result.get(
                    "id"
                )

                if not candidate:
                    continue

                if candidate == vidid:
                    continue

                if candidate in related:
                    continue

                duration_str = result.get(
                    "duration"
                )

                if duration_str:

                    try:

                        if (
                            time_to_seconds(
                                duration_str
                            )
                            > autoplay_limit
                        ):
                            continue

                    except Exception:
                        pass

                related.append(candidate)

                if len(related) >= 10:
                    break

        except Exception:
            pass

        return related

    # =====================================================
    # TRACK
    # =====================================================

    async def track(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + str(link)

        extracted_id = extract_video_id(
            link
        )

        # -------------------------------------------------
        # Direct YouTube URL
        # -------------------------------------------------

        if extracted_id:

            try:

                details = await self.details(
                    extracted_id,
                    True,
                )

                (
                    title,
                    duration_min,
                    duration_sec,
                    thumbnail,
                    vidid,
                ) = details

                yturl = (
                    self.base + vidid
                )

                return (
                    {
                        "title": title,
                        "link": yturl,
                        "vidid": vidid,
                        "duration_min": duration_min,
                        "thumb": thumbnail,
                    },
                    vidid,
                )

            except Exception:
                pass

        # -------------------------------------------------
        # Normal search
        # -------------------------------------------------

        data = await self._search(
            link,
            1,
        )

        if not data:
            raise RuntimeError(
                "No YouTube result found"
            )

        result = data[0]

        title = result.get(
            "title",
            "Unknown",
        )

        duration_min = result.get(
            "duration"
        )

        vidid = result.get("id")

        yturl = result.get(
            "link"
        ) or self.base + str(vidid)

        thumbs = result.get(
            "thumbnails"
        ) or []

        thumbnail = ""

        if thumbs:
            thumbnail = (
                thumbs[0]
                .get("url", "")
                .split("?")[0]
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

    # =====================================================
    # FORMATS
    # =====================================================

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

        def extract():

            with yt_dlp.YoutubeDL(
                ytdl_opts
            ) as ydl:

                return ydl.extract_info(
                    link,
                    download=False,
                )

        r = await loop.run_in_executor(
            None,
            extract,
        )

        formats_available = []

        for fmt in r.get("formats", []):

            try:

                if (
                    "dash"
                    not in str(
                        fmt.get("format", "")
                    ).lower()
                ):

                    formats_available.append(
                        {
                            "format": fmt.get(
                                "format"
                            ),
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

    # =====================================================
    # SLIDER
    # =====================================================

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
            10,
        )

        if not results:
            raise RuntimeError(
                "No YouTube search result"
            )

        try:
            result = results[
                int(query_type)
            ]
        except IndexError:
            result = results[0]

        title = result.get(
            "title",
            "Unknown",
        )

        duration_min = result.get(
            "duration"
        )

        vidid = result.get(
            "id"
        )

        thumbs = result.get(
            "thumbnails"
        ) or []

        thumbnail = ""

        if thumbs:
            thumbnail = (
                thumbs[0]
                .get("url", "")
                .split("?")[0]
            )

        return (
            title,
            duration_min,
            thumbnail,
            vidid,
        )

    # =====================================================
    # DOWNLOAD
    # =====================================================

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

        if videoid:
            link = self.base + str(link)

        try:

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

        except Exception:
            return (
                None,
                False,
            )

    # =====================================================
    # INTERNAL YT-DLP
    # =====================================================

    @staticmethod
    def _extract_info(link: str):

        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(
                link,
                download=False,
            )

    # =====================================================
    # SECONDS -> HH:MM:SS
    # =====================================================

    @staticmethod
    def _seconds_to_duration(
        seconds: int,
    ) -> str:

        seconds = int(seconds or 0)

        hours, remainder = divmod(
            seconds,
            3600,
        )

        minutes, secs = divmod(
            remainder,
            60,
        )

        if hours:
            return (
                f"{hours}:{minutes:02d}:{secs:02d}"
            )

        return (
            f"{minutes}:{secs:02d}"
        )


# =========================================================
# INSTANCE
# =========================================================

YouTube = YouTubeAPI()
