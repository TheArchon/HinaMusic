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
).rstrip("/")

API_KEY = os.environ.get(
    "SHRUTI_API_KEY",
    ""
)

DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# =========================================================
# SAFE HELPERS
# =========================================================

def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def time_to_seconds(time_value) -> int:
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

    except (TypeError, ValueError):
        return 0


def extract_video_id(link: str) -> Optional[str]:
    """
    Supports:

    youtube.com/watch?v=ID
    youtube.com/watch?v=ID&list=...
    youtu.be/ID
    youtube.com/shorts/ID
    youtube.com/embed/ID
    youtube.com/live/ID
    youtube.com/v/ID
    Direct 11 character video ID
    """

    if not link:
        return None

    try:
        link = str(link).strip()
    except Exception:
        return None

    if not link:
        return None

    # Direct YouTube ID
    if re.fullmatch(
        r"[A-Za-z0-9_-]{11}",
        link
    ):
        return link

    try:
        parsed = urlparse(link)

        host = (
            parsed.netloc
            .lower()
            .replace("www.", "")
        )

        path = parsed.path.strip("/")

        # ---------------------------------------------
        # youtu.be/VIDEO_ID
        # ---------------------------------------------

        if host in (
            "youtu.be",
            "youtube-nocookie.com",
        ):

            parts = [
                x for x in path.split("/")
                if x
            ]

            if parts:
                candidate = parts[0]

                if re.fullmatch(
                    r"[A-Za-z0-9_-]{11}",
                    candidate
                ):
                    return candidate

        # ---------------------------------------------
        # youtube.com
        # ---------------------------------------------

        if (
            host == "youtube.com"
            or host.endswith(".youtube.com")
        ):

            query = parse_qs(
                parsed.query
            )

            # watch?v=ID
            if query.get("v"):

                candidate = query["v"][0]

                if candidate:
                    return candidate[:11]

            parts = [
                x for x in path.split("/")
                if x
            ]

            if len(parts) >= 2:

                if parts[0].lower() in (
                    "shorts",
                    "embed",
                    "live",
                    "v",
                ):

                    candidate = parts[1]

                    if re.fullmatch(
                        r"[A-Za-z0-9_-]{11}",
                        candidate
                    ):
                        return candidate

    except Exception:
        return None

    return None


def normalize_youtube_url(
    link: str
) -> Optional[str]:

    if not link:
        return None

    try:
        link = str(link).strip()
    except Exception:
        return None

    if not link:
        return None

    video_id = extract_video_id(link)

    if video_id:
        return (
            "https://www.youtube.com/watch?v="
            + video_id
        )

    return link


def clean_youtube_link(link: str) -> str:

    if not link:
        return ""

    try:
        link = str(link).strip()
    except Exception:
        return ""

    video_id = extract_video_id(link)

    if video_id:
        return (
            "https://www.youtube.com/watch?v="
            + video_id
        )

    return link


# =========================================================
# DOWNLOAD FROM API
# =========================================================

async def _download_from_api(
    link: str,
    media_type: str,
    extension: str,
    timeout_seconds: int,
) -> Optional[str]:

    video_id = extract_video_id(link)

    if not video_id:
        return None

    file_path = os.path.join(
        DOWNLOAD_DIR,
        f"{video_id}.{extension}"
    )

    # Already downloaded
    try:
        if (
            os.path.exists(file_path)
            and os.path.getsize(file_path) > 0
        ):
            return file_path
    except OSError:
        pass

    temp_path = file_path + ".part"

    youtube_url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )

    params = {
        "url": youtube_url,
        "type": media_type,
    }

    if API_KEY:
        params["api_key"] = API_KEY

    timeout = aiohttp.ClientTimeout(
        total=timeout_seconds,
        connect=30,
        sock_connect=30,
        sock_read=timeout_seconds,
    )

    try:

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(
                f"{API_URL}/download",
                params=params,
                allow_redirects=True,
            ) as response:

                if response.status != 200:
                    return None

                content_type = (
                    response.headers.get(
                        "Content-Type",
                        ""
                    ).lower()
                )

                # API error JSON
                if (
                    "application/json"
                    in content_type
                ):
                    return None

                total_size = 0

                with open(
                    temp_path,
                    "wb"
                ) as file:

                    async for chunk in response.content.iter_chunked(
                        256 * 1024
                    ):

                        if not chunk:
                            continue

                        file.write(chunk)
                        total_size += len(chunk)

        if total_size <= 0:
            return None

        if not os.path.exists(temp_path):
            return None

        if os.path.getsize(temp_path) <= 0:
            return None

        os.replace(
            temp_path,
            file_path
        )

        return file_path

    except Exception:
        return None

    finally:

        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


async def download_song(
    link: str
) -> Optional[str]:

    return await _download_from_api(
        link=link,
        media_type="audio",
        extension="mp3",
        timeout_seconds=300,
    )


async def download_video(
    link: str
) -> Optional[str]:

    return await _download_from_api(
        link=link,
        media_type="video",
        extension="mp4",
        timeout_seconds=600,
    )


# =========================================================
# YOUTUBE API
# =========================================================

class YouTubeAPI:

    def __init__(self):

        self.base = (
            "https://www.youtube.com/watch?v="
        )

        self.listbase = (
            "https://www.youtube.com/playlist?list="
        )

        self.regex = re.compile(
            r"(?:youtube\.com|youtu\.be)",
            re.IGNORECASE,
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
            return (
                extract_video_id(
                    str(link)
                )
                is not None
            )

        return bool(
            self.regex.search(
                str(link)
            )
        )

    # =====================================================
    # MESSAGE URL
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

            # -----------------------------------------
            # TEXT
            # -----------------------------------------

            text = (
                message.text
                or ""
            )

            entities = (
                message.entities
                or []
            )

            for entity in entities:

                try:

                    if (
                        entity.type
                        == MessageEntityType.URL
                    ):

                        return text[
                            entity.offset:
                            entity.offset + entity.length
                        ]

                    if (
                        entity.type
                        == MessageEntityType.TEXT_LINK
                    ):

                        if entity.url:
                            return entity.url

                except Exception:
                    continue

            # -----------------------------------------
            # CAPTION
            # -----------------------------------------

            caption = (
                message.caption
                or ""
            )

            caption_entities = (
                message.caption_entities
                or []
            )

            for entity in caption_entities:

                try:

                    if (
                        entity.type
                        == MessageEntityType.URL
                    ):

                        return caption[
                            entity.offset:
                            entity.offset + entity.length
                        ]

                    if (
                        entity.type
                        == MessageEntityType.TEXT_LINK
                    ):

                        if entity.url:
                            return entity.url

                except Exception:
                    continue

            # -----------------------------------------
            # FALLBACK
            # -----------------------------------------

            full_text = (
                text
                or caption
                or ""
            )

            match = re.search(
                r"https?://(?:www\.)?"
                r"(?:youtube\.com/"
                r"(?:watch\?v=|shorts/|live/|embed/)"
                r"[\w-]+"
                r"|youtu\.be/[\w-]+)",
                full_text,
                re.IGNORECASE,
            )

            if match:
                return match.group(0)

        return None

    # =====================================================
    # SEARCH
    # =====================================================

    async def _search(
        self,
        query: str,
        limit: int = 1,
    ):

        if not query:
            return []

        try:
            limit = max(
                1,
                safe_int(limit, 1)
            )
        except Exception:
            limit = 1

        clean_query = normalize_youtube_url(
            query
        )

        if not clean_query:
            return []

        try:

            results = VideosSearch(
                clean_query,
                limit=limit,
            )

            response = (
                await results.next()
            )

            if not isinstance(
                response,
                dict
            ):
                return []

            result = (
                response.get("result")
                or []
            )

            if not isinstance(
                result,
                list
            ):
                return []

            return result

        except Exception:
            return []

    # =====================================================
    # DETAILS
    # =====================================================

    async def details(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = (
                self.base
                + str(link)
            )

        result = await self._search(
            link,
            1
        )

        if not result:
            return (
                None,
                "0:00",
                0,
                None,
                extract_video_id(link),
            )

        data = result[0]

        if not isinstance(
            data,
            dict
        ):
            return (
                None,
                "0:00",
                0,
                None,
                extract_video_id(link),
            )

        title = (
            data.get("title")
            or "Unknown Title"
        )

        duration_min = (
            data.get("duration")
            or "0:00"
        )

        duration_sec = time_to_seconds(
            duration_min
        )

        thumbnails = (
            data.get("thumbnails")
            or []
        )

        thumbnail = None

        if isinstance(
            thumbnails,
            list
        ) and thumbnails:

            try:
                thumbnail = (
                    thumbnails[0]
                    .get("url")
                )

                if thumbnail:
                    thumbnail = (
                        thumbnail
                        .split("?")[0]
                    )

            except Exception:
                thumbnail = None

        vidid = (
            data.get("id")
            or extract_video_id(link)
        )

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

        if videoid:
            link = (
                self.base
                + str(link)
            )

        result = await self._search(
            link,
            1
        )

        if not result:
            return None

        data = result[0]

        if not isinstance(
            data,
            dict
        ):
            return None

        return (
            data.get("title")
            or "Unknown Title"
        )

    # =====================================================
    # DURATION
    # =====================================================

    async def duration(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = (
                self.base
                + str(link)
            )

        result = await self._search(
            link,
            1
        )

        if not result:
            return "0:00"

        data = result[0]

        if not isinstance(
            data,
            dict
        ):
            return "0:00"

        return (
            data.get("duration")
            or "0:00"
        )

    # =====================================================
    # THUMBNAIL
    # =====================================================

    async def thumbnail(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = (
                self.base
                + str(link)
            )

        result = await self._search(
            link,
            1
        )

        if not result:
            return None

        data = result[0]

        if not isinstance(
            data,
            dict
        ):
            return None

        thumbnails = (
            data.get("thumbnails")
            or []
        )

        if not isinstance(
            thumbnails,
            list
        ):
            return None

        if not thumbnails:
            return None

        try:
            url = thumbnails[0].get(
                "url"
            )

            if url:
                return url.split("?")[0]

        except Exception:
            pass

        return None

    # =====================================================
    # VIDEO
    # =====================================================

    async def video(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = (
                self.base
                + str(link)
            )

        link = normalize_youtube_url(
            link
        )

        if not link:
            return (
                0,
                "Invalid YouTube URL"
            )

        try:

            downloaded_file = (
                await download_video(
                    link
                )
            )

            if (
                downloaded_file
                and os.path.exists(
                    downloaded_file
                )
            ):

                return (
                    1,
                    downloaded_file
                )

            return (
                0,
                "Video download failed"
            )

        except Exception as e:

            return (
                0,
                f"Video download error: {e}"
            )

    # =====================================================
    # PLAYLIST
    # =====================================================

    async def playlist(
        self,
        link,
        limit,
        user_id=None,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = (
                self.listbase
                + str(link)
            )

        if not link:
            return []

        try:

            limit = max(
                1,
                safe_int(
                    limit,
                    10
                )
            )

        except Exception:
            limit = 10

        try:

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "skip_download": True,
                "playlistend": limit,
            }

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:

                info = ydl.extract_info(
                    link,
                    download=False
                )

            if not isinstance(
                info,
                dict
            ):
                return []

            entries = (
                info.get("entries")
                or []
            )

            ids = []

            for data in entries[:limit]:

                if not isinstance(
                    data,
                    dict
                ):
                    continue

                vid = data.get("id")

                if not vid:
                    continue

                vid = str(vid)

                if (
                    vid not in ids
                    and len(vid) == 11
                ):
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
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = (
                self.base
                + str(link)
            )

        result = await self._search(
            link,
            1
        )

        if not result:
            return None, None

        data = result[0]

        if not isinstance(
            data,
            dict
        ):
            return None, None

        vidid = (
            data.get("id")
            or extract_video_id(link)
        )

        if not vidid:
            return None, None

        title = (
            data.get("title")
            or "Unknown Title"
        )

        duration_min = (
            data.get("duration")
            or "0:00"
        )

        yturl = (
            data.get("link")
            or (
                self.base
                + vidid
            )
        )

        thumbnails = (
            data.get("thumbnails")
            or []
        )

        thumbnail = None

        if (
            isinstance(
                thumbnails,
                list
            )
            and thumbnails
        ):

            try:
                thumbnail = (
                    thumbnails[0]
                    .get("url")
                )

                if thumbnail:
                    thumbnail = (
                        thumbnail
                        .split("?")[0]
                    )

            except Exception:
                thumbnail = None

        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }

        return (
            track_details,
            vidid
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
            link = (
                self.base
                + str(link)
            )

        link = normalize_youtube_url(
            link
        )

        if not link:
            return [], link

        try:

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
            }

            formats_available = []

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:

                info = ydl.extract_info(
                    link,
                    download=False
                )

            if not isinstance(
                info,
                dict
            ):
                return [], link

            for fmt in (
                info.get("formats")
                or []
            ):

                if not isinstance(
                    fmt,
                    dict
                ):
                    continue

                try:

                    format_name = str(
                        fmt.get(
                            "format",
                            ""
                        )
                    )

                    if (
                        "dash"
                        in format_name.lower()
                    ):
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

            return (
                formats_available,
                link
            )

        except Exception:
            return [], link

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
            link = (
                self.base
                + str(link)
            )

        try:

            query_type = max(
                0,
                safe_int(
                    query_type,
                    0
                )
            )

        except Exception:
            query_type = 0

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

        if query_type >= len(
            result
        ):
            query_type = (
                len(result) - 1
            )

        data = result[
            query_type
        ]

        if not isinstance(
            data,
            dict
        ):
            return (
                None,
                "0:00",
                None,
                None
            )

        title = (
            data.get("title")
            or "Unknown Title"
        )

        duration = (
            data.get("duration")
            or "0:00"
        )

        vidid = data.get(
            "id"
        )

        thumbnails = (
            data.get("thumbnails")
            or []
        )

        thumbnail = None

        if (
            isinstance(
                thumbnails,
                list
            )
            and thumbnails
        ):

            try:
                thumbnail = (
                    thumbnails[0]
                    .get("url")
                )

                if thumbnail:
                    thumbnail = (
                        thumbnail
                        .split("?")[0]
                    )

            except Exception:
                thumbnail = None

        return (
            title,
            duration,
            thumbnail,
            vidid
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

        try:

            if not link:
                return None, False

            if videoid:
                link = (
                    self.base
                    + str(link)
                )

            link = normalize_youtube_url(
                link
            )

            if not link:
                return None, False

            # -----------------------------------------
            # VIDEO / AUDIO
            # -----------------------------------------

            is_video = bool(
                video
                or songvideo
            )

            if is_video:

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

            if not downloaded_file:
                return None, False

            if not os.path.exists(
                downloaded_file
            ):
                return None, False

            try:
                file_size = os.path.getsize(
                    downloaded_file
                )
            except OSError:
                return None, False

            if file_size <= 0:
                return None, False

            return (
                downloaded_file,
                True
            )

        except Exception:
            return None, False


# =========================================================
# GLOBAL
# =========================================================

YouTube = YouTubeAPI()
