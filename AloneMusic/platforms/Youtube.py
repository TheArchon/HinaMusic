import os
import re
from typing import Optional, Union
from urllib.parse import urlparse, parse_qs

import aiohttp
import yt_dlp
from py_yt import VideosSearch
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message


# =========================================================
# CONFIG
# =========================================================

API_URL = os.environ.get(
    "SHRUTI_API_URL",
    "https://api01.shrutibots.site"
)

API_KEY = os.environ.get(
    "SHRUTI_API_KEY",
    "ShrutiBotsAlSpfeG7JItQmuoxCqKd"
)

DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# =========================================================
# HELPERS
# =========================================================

def time_to_seconds(time_value) -> int:
    """Convert HH:MM:SS / MM:SS to seconds safely."""
    if not time_value:
        return 0

    try:
        value = str(time_value).strip()

        if not value:
            return 0

        parts = value.split(":")

        total = 0

        for part in parts:
            total = total * 60 + int(part)

        return total

    except (ValueError, TypeError):
        return 0


def extract_video_id(link: str) -> Optional[str]:
    """
    Extract YouTube video ID from:
    - youtube.com/watch?v=
    - youtu.be/
    - youtube.com/shorts/
    - youtube.com/embed/
    - youtube.com/live/
    - direct video ID
    """

    if not link:
        return None

    link = str(link).strip()

    # Already a YouTube ID
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", link):
        return link

    try:
        parsed = urlparse(link)

        host = parsed.netloc.lower().replace("www.", "")

        # youtu.be/VIDEO_ID
        if host == "youtu.be":
            video_id = parsed.path.strip("/").split("/")[0]

            if video_id:
                return video_id[:11]

        # youtube.com
        if "youtube.com" in host:

            query = parse_qs(parsed.query)

            # watch?v=
            if query.get("v"):
                return query["v"][0][:11]

            parts = [x for x in parsed.path.split("/") if x]

            if len(parts) >= 2:
                if parts[0] in (
                    "shorts",
                    "embed",
                    "live",
                    "v"
                ):
                    return parts[1][:11]

    except Exception:
        pass

    return None


def normalize_youtube_url(link: str) -> Optional[str]:
    """Return clean YouTube watch URL."""

    if not link:
        return None

    link = str(link).strip()

    video_id = extract_video_id(link)

    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"

    # Search query / other input
    return link


# =========================================================
# DOWNLOAD
# =========================================================

async def _download_from_api(
    link: str,
    media_type: str,
    extension: str,
    timeout_seconds: int
):
    """Download media from Shruti API."""

    video_id = extract_video_id(link)

    if not video_id:
        return None

    file_path = os.path.join(
        DOWNLOAD_DIR,
        f"{video_id}.{extension}"
    )

    # Already downloaded
    if (
        os.path.exists(file_path)
        and os.path.getsize(file_path) > 0
    ):
        return file_path

    temp_path = f"{file_path}.part"

    try:
        params = {
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "type": media_type,
            "api_key": API_KEY,
        }

        timeout = aiohttp.ClientTimeout(
            total=timeout_seconds,
            connect=30,
            sock_read=timeout_seconds,
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
                        ""
                    ).lower()
                )

                # API sometimes returns JSON/error instead
                if "application/json" in content_type:
                    return None

                with open(temp_path, "wb") as file:

                    async for chunk in response.content.iter_chunked(
                        256 * 1024
                    ):
                        if chunk:
                            file.write(chunk)

        if (
            os.path.exists(temp_path)
            and os.path.getsize(temp_path) > 0
        ):
            os.replace(temp_path, file_path)
            return file_path

        return None

    except Exception:
        return None

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


async def download_song(link: str) -> Optional[str]:
    return await _download_from_api(
        link,
        media_type="audio",
        extension="mp3",
        timeout_seconds=300,
    )


async def download_video(link: str) -> Optional[str]:
    return await _download_from_api(
        link,
        media_type="video",
        extension="mp4",
        timeout_seconds=600,
    )


# =========================================================
# YOUTUBE API
# =========================================================

class YouTubeAPI:

    def __init__(self):

        self.base = "https://www.youtube.com/watch?v="
        self.listbase = "https://www.youtube.com/playlist?list="

        self.regex = re.compile(
            r"(?:youtube\.com|youtu\.be)",
            re.IGNORECASE
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
        videoid: Union[bool, str] = None
    ):

        if not link:
            return False

        if videoid:
            return bool(
                extract_video_id(str(link))
            )

        return bool(
            self.regex.search(str(link))
        )

    # =====================================================
    # GET URL FROM MESSAGE
    # =====================================================

    async def url(
        self,
        message_1: Message
    ) -> Optional[str]:

        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(
                message_1.reply_to_message
            )

        for message in messages:

            # -------------------------------
            # TEXT ENTITIES
            # -------------------------------

            if message.entities:

                text = message.text or ""

                for entity in message.entities:

                    if entity.type == MessageEntityType.URL:

                        try:
                            return text[
                                entity.offset:
                                entity.offset + entity.length
                            ]
                        except Exception:
                            continue

                    if entity.type == MessageEntityType.TEXT_LINK:

                        if entity.url:
                            return entity.url

            # -------------------------------
            # CAPTION ENTITIES
            # -------------------------------

            if message.caption_entities:

                caption = message.caption or ""

                for entity in message.caption_entities:

                    if entity.type == MessageEntityType.URL:

                        try:
                            return caption[
                                entity.offset:
                                entity.offset + entity.length
                            ]
                        except Exception:
                            continue

                    if entity.type == MessageEntityType.TEXT_LINK:

                        if entity.url:
                            return entity.url

            # -------------------------------
            # FALLBACK TEXT SEARCH
            # -------------------------------

            text = (
                message.text
                or message.caption
                or ""
            )

            match = re.search(
                r"(https?://(?:www\.)?"
                r"(?:youtube\.com/watch\?v=[\w-]+"
                r"|youtu\.be/[\w-]+"
                r"|youtube\.com/shorts/[\w-]+"
                r"|youtube\.com/live/[\w-]+))",
                text,
                re.IGNORECASE
            )

            if match:
                return match.group(1)

        return None

    # =====================================================
    # SEARCH
    # =====================================================

    async def _search(
        self,
        link: str,
        limit: int = 1
    ):

        if not link:
            return []

        clean_link = normalize_youtube_url(link)

        try:
            results = VideosSearch(
                clean_link,
                limit=limit
            )

            response = await results.next()

            if not response:
                return []

            return response.get("result") or []

        except Exception:
            return []

    # =====================================================
    # DETAILS
    # =====================================================

    async def details(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + str(link)

        result = await self._search(link, 1)

        if not result:
            return (
                None,
                "0:00",
                0,
                None,
                extract_video_id(link)
            )

        data = result[0]

        title = data.get(
            "title",
            "Unknown Title"
        )

        duration_min = data.get(
            "duration"
        ) or "0:00"

        duration_sec = time_to_seconds(
            duration_min
        )

        thumbnails = data.get(
            "thumbnails"
        ) or []

        thumbnail = None

        if thumbnails:
            thumbnail = (
                thumbnails[0]
                .get("url")
            )

            if thumbnail:
                thumbnail = thumbnail.split("?")[0]

        vidid = data.get(
            "id"
        ) or extract_video_id(link)

        return (
            title,
            duration_min,
            duration_sec,
            thumbnail,
            vidid
        )

    # =====================================================
    # TITLE
    # =====================================================

    async def title(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + str(link)

        result = await self._search(link, 1)

        if not result:
            return None

        return result[0].get(
            "title",
            "Unknown Title"
        )

    # =====================================================
    # DURATION
    # =====================================================

    async def duration(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + str(link)

        result = await self._search(link, 1)

        if not result:
            return "0:00"

        return result[0].get(
            "duration"
        ) or "0:00"

    # =====================================================
    # THUMBNAIL
    # =====================================================

    async def thumbnail(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + str(link)

        result = await self._search(link, 1)

        if not result:
            return None

        thumbnails = result[0].get(
            "thumbnails"
        ) or []

        if not thumbnails:
            return None

        url = thumbnails[0].get("url")

        if url:
            return url.split("?")[0]

        return None

    # =====================================================
    # VIDEO
    # =====================================================

    async def video(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + str(link)

        link = normalize_youtube_url(link)

        if not link:
            return 0, "Invalid YouTube URL"

        try:

            downloaded_file = await download_video(
                link
            )

            if downloaded_file:
                return 1, downloaded_file

            return 0, "Video download failed"

        except Exception as e:

            return 0, f"Video download error: {e}"

    # =====================================================
    # PLAYLIST
    # =====================================================

    async def playlist(
        self,
        link,
        limit,
        user_id=None,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.listbase + str(link)

        if not link:
            return []

        try:

            ytdl_opts = {
                "quiet": True,
                "extract_flat": True,
                "skip_download": True,
                "playlistend": int(limit),
            }

            with yt_dlp.YoutubeDL(
                ytdl_opts
            ) as ydl:

                info = ydl.extract_info(
                    link,
                    download=False
                )

            if not info:
                return []

            entries = (
                info.get("entries")
                or []
            )

            ids = []

            for data in entries[:int(limit)]:

                if not data:
                    continue

                vid = data.get("id")

                if vid:
                    ids.append(vid)

            return ids

        except Exception:
            return []

    # =====================================================
    # TRACK
    # =====================================================

    async def track(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + str(link)

        result = await self._search(
            link,
            1
        )

        if not result:
            return None, None

        data = result[0]

        title = data.get(
            "title",
            "Unknown Title"
        )

        duration_min = data.get(
            "duration"
        ) or "0:00"

        vidid = data.get(
            "id"
        )

        yturl = data.get(
            "link"
        )

        if not yturl and vidid:
            yturl = self.base + vidid

        thumbnails = data.get(
            "thumbnails"
        ) or []

        thumbnail = None

        if thumbnails:
            thumbnail = thumbnails[0].get(
                "url"
            )

            if thumbnail:
                thumbnail = thumbnail.split("?")[0]

        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }

        return track_details, vidid

    # =====================================================
    # FORMATS
    # =====================================================

    async def formats(
        self,
        link: str,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + str(link)

        link = normalize_youtube_url(link)

        if not link:
            return [], link

        try:

            ytdl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
            }

            formats_available = []

            with yt_dlp.YoutubeDL(
                ytdl_opts
            ) as ydl:

                info = ydl.extract_info(
                    link,
                    download=False
                )

                if not info:
                    return [], link

                for fmt in info.get(
                    "formats",
                    []
                ):

                    try:

                        format_name = str(
                            fmt.get("format", "")
                        )

                        if "dash" in format_name.lower():
                            continue

                        formats_available.append(
                            {
                                "format": format_name,
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

            return formats_available, link

        except Exception:
            return [], link

    # =====================================================
    # SLIDER
    # =====================================================

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None
    ):

        if videoid:
            link = self.base + str(link)

        try:

            result = await self._search(
                link,
                10
            )

            if not result:
                return (
                    None,
                    "0:00",
                    None,
                    None
                )

            if query_type < 0:
                query_type = 0

            if query_type >= len(result):
                query_type = len(result) - 1

            data = result[query_type]

            title = data.get(
                "title",
                "Unknown Title"
            )

            duration_min = data.get(
                "duration"
            ) or "0:00"

            vidid = data.get(
                "id"
            )

            thumbnails = data.get(
                "thumbnails"
            ) or []

            thumbnail = None

            if thumbnails:
                thumbnail = thumbnails[0].get(
                    "url"
                )

                if thumbnail:
                    thumbnail = thumbnail.split("?")[0]

            return (
                title,
                duration_min,
                thumbnail,
                vidid
            )

        except Exception:
            return (
                None,
                "0:00",
                None,
                None
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
    ):

        if videoid:
            link = self.base + str(link)

        link = normalize_youtube_url(link)

        if not link:
            return None, False

        try:

            if video:
                downloaded_file = await download_video(
                    link
                )
            else:
                downloaded_file = await download_song(
                    link
                )

            if (
                downloaded_file
                and os.path.exists(downloaded_file)
                and os.path.getsize(downloaded_file) > 0
            ):
                return downloaded_file, True

            return None, False

        except Exception:
            return None, False


# =========================================================
# GLOBAL OBJECT
# =========================================================

YouTube = YouTubeAPI()
