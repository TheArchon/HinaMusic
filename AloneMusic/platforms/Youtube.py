import os
import re
from typing import Optional, Union
from urllib.parse import urlparse, parse_qs, urlencode

import yt_dlp
from py_yt import VideosSearch
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message


# =========================================================
# CONFIG
# =========================================================

API_URL = os.environ.get(
    "SHRUTI_API_URL",
    "https://api01.shrutibots.site",
).rstrip("/")

API_KEY = os.environ.get(
    "SHRUTI_API_KEY",
    "ShrutiBotsAlSpfeG7JItQmuoxCqKd",
)

# Kept for compatibility with old code.
DOWNLOAD_DIR = "downloads"

os.makedirs(
    DOWNLOAD_DIR,
    exist_ok=True,
)


# =========================================================
# HELPERS
# =========================================================

def time_to_seconds(time_value) -> int:
    """
    Convert:
        HH:MM:SS
        MM:SS
        SS

    to seconds.
    """

    if not time_value:
        return 0

    try:
        value = str(time_value).strip()

        if not value:
            return 0

        parts = value.split(":")

        total = 0

        for part in parts:
            total = (
                total * 60
                + int(part)
            )

        return total

    except (
        ValueError,
        TypeError,
    ):
        return 0


def extract_video_id(
    link: str,
) -> Optional[str]:
    """
    Extract YouTube video ID from:

    youtube.com/watch?v=
    youtu.be/
    youtube.com/shorts/
    youtube.com/embed/
    youtube.com/live/
    direct video ID
    """

    if not link:
        return None

    link = str(link).strip()

    # -----------------------------------------------------
    # Direct video ID
    # -----------------------------------------------------

    if re.fullmatch(
        r"[A-Za-z0-9_-]{11}",
        link,
    ):
        return link

    try:
        parsed = urlparse(link)

        host = (
            parsed.netloc
            .lower()
            .replace(
                "www.",
                "",
            )
        )

        # -------------------------------------------------
        # youtu.be/VIDEO_ID
        # -------------------------------------------------

        if host == "youtu.be":

            video_id = (
                parsed.path
                .strip("/")
                .split("/")[0]
            )

            if re.fullmatch(
                r"[A-Za-z0-9_-]{11}",
                video_id,
            ):
                return video_id

        # -------------------------------------------------
        # youtube.com
        # -------------------------------------------------

        if (
            host == "youtube.com"
            or host.endswith(".youtube.com")
        ):

            query = parse_qs(
                parsed.query
            )

            # watch?v=
            if query.get("v"):

                video_id = query["v"][0]

                if re.fullmatch(
                    r"[A-Za-z0-9_-]{11}",
                    video_id,
                ):
                    return video_id

            parts = [
                x
                for x in parsed.path.split("/")
                if x
            ]

            if len(parts) >= 2:

                if parts[0] in (
                    "shorts",
                    "embed",
                    "live",
                    "v",
                ):

                    video_id = parts[1]

                    if re.fullmatch(
                        r"[A-Za-z0-9_-]{11}",
                        video_id,
                    ):
                        return video_id

    except Exception:
        pass

    return None


def normalize_youtube_url(
    link: str,
) -> Optional[str]:
    """
    Return clean YouTube watch URL.
    """

    if not link:
        return None

    link = str(link).strip()

    video_id = extract_video_id(
        link
    )

    if video_id:

        return (
            "https://www.youtube.com/watch?v="
            + video_id
        )

    return link


# =========================================================
# FAST SHRUTI API STREAM
# =========================================================

async def _stream_from_api(
    link: str,
    media_type: str,
) -> Optional[str]:
    """
    FAST STREAM MODE.

    Does NOT download the complete file.

    Returns the remote API URL immediately so the
    voice-call layer can start reading the stream.
    """

    video_id = extract_video_id(
        link
    )

    if not video_id:
        return None

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

    stream_url = (
        f"{API_URL}/download?"
        + urlencode(params)
    )

    return stream_url


# =========================================================
# FAST AUDIO
# =========================================================

async def download_song(
    link: str,
) -> Optional[str]:
    """
    Return audio stream URL immediately.
    """

    return await _stream_from_api(
        link,
        media_type="audio",
    )


# =========================================================
# FAST VIDEO
# =========================================================

async def download_video(
    link: str,
) -> Optional[str]:
    """
    Return video stream URL immediately.
    """

    return await _stream_from_api(
        link,
        media_type="video",
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
        videoid: Union[
            bool,
            str,
        ] = None,
    ):

        if not link:
            return False

        if videoid:

            return bool(
                extract_video_id(
                    str(link)
                )
            )

        return bool(
            self.regex.search(
                str(link)
            )
        )

    # =====================================================
    # GET URL FROM MESSAGE
    # =====================================================

    async def url(
        self,
        message_1: Message,
    ) -> Optional[str]:

        messages = [
            message_1
        ]

        if message_1.reply_to_message:

            messages.append(
                message_1.reply_to_message
            )

        for message in messages:

            # -------------------------------------------------
            # TEXT ENTITIES
            # -------------------------------------------------

            if message.entities:

                text = (
                    message.text
                    or ""
                )

                for entity in message.entities:

                    if (
                        entity.type
                        == MessageEntityType.URL
                    ):

                        try:

                            return text[
                                entity.offset:
                                entity.offset
                                + entity.length
                            ]

                        except Exception:
                            continue

                    if (
                        entity.type
                        == MessageEntityType.TEXT_LINK
                    ):

                        if entity.url:
                            return entity.url

            # -------------------------------------------------
            # CAPTION ENTITIES
            # -------------------------------------------------

            if message.caption_entities:

                caption = (
                    message.caption
                    or ""
                )

                for entity in (
                    message.caption_entities
                ):

                    if (
                        entity.type
                        == MessageEntityType.URL
                    ):

                        try:

                            return caption[
                                entity.offset:
                                entity.offset
                                + entity.length
                            ]

                        except Exception:
                            continue

                    if (
                        entity.type
                        == MessageEntityType.TEXT_LINK
                    ):

                        if entity.url:
                            return entity.url

            # -------------------------------------------------
            # FALLBACK TEXT SEARCH
            # -------------------------------------------------

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
                r"|youtube\.com/live/[\w-]+"
                r"|youtube\.com/embed/[\w-]+))",
                text,
                re.IGNORECASE,
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
        limit: int = 1,
    ):

        if not link:
            return []

        clean_link = (
            normalize_youtube_url(
                link
            )
        )

        if not clean_link:
            return []

        try:

            results = VideosSearch(
                clean_link,
                limit=limit,
            )

            response = await results.next()

            if not response:
                return []

            return (
                response.get("result")
                or []
            )

        except Exception:
            return []

    # =====================================================
    # RELATED VIDEOS / AUTOPLAY
    # =====================================================

    async def get_related_videos(
        self,
        video_id: str,
        limit: int = 10,
    ):
        """
        Return related YouTube video IDs.
        """

        if not video_id:
            return []

        try:

            video_id = extract_video_id(
                str(video_id)
            )

            if not video_id:
                return []

            current = await self._search(
                self.base + video_id,
                1,
            )

            if not current:
                return []

            current_data = current[0]

            title = current_data.get(
                "title"
            )

            if not title:
                return []

            results = await self._search(
                title,
                limit + 5,
            )

            if not results:
                return []

            related = []

            for item in results:

                if not item:
                    continue

                related_id = item.get(
                    "id"
                )

                if not related_id:
                    continue

                if related_id == video_id:
                    continue

                if related_id in related:
                    continue

                related.append(
                    related_id
                )

                if len(related) >= limit:
                    break

            return related

        except Exception:
            return []

    # =====================================================
    # DETAILS
    # =====================================================

    async def details(
        self,
        link: str,
        videoid: Union[
            bool,
            str,
        ] = None,
    ):

        if videoid:

            link = (
                self.base
                + str(link)
            )

        result = await self._search(
            link,
            1,
        )

        if not result:

            return (
                None,
                "0:00",
                0,
                None,
                extract_video_id(
                    link
                ),
            )

        data = result[0]

        title = data.get(
            "title",
            "Unknown Title",
        )

        duration_min = (
            data.get("duration")
            or "0:00"
        )

        duration_sec = (
            time_to_seconds(
                duration_min
            )
        )

        thumbnails = (
            data.get("thumbnails")
            or []
        )

        thumbnail = None

        if thumbnails:

            thumbnail = (
                thumbnails[-1]
                .get("url")
            )

            if thumbnail:
                thumbnail = (
                    thumbnail.split("?")[0]
                )

        vidid = (
            data.get("id")
            or extract_video_id(
                link
            )
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
        videoid: Union[
            bool,
            str,
        ] = None,
    ):

        if videoid:

            link = (
                self.base
                + str(link)
            )

        result = await self._search(
            link,
            1,
        )

        if not result:
            return None

        return result[0].get(
            "title",
            "Unknown Title",
        )

    # =====================================================
    # DURATION
    # =====================================================

    async def duration(
        self,
        link: str,
        videoid: Union[
            bool,
            str,
        ] = None,
    ):

        if videoid:

            link = (
                self.base
                + str(link)
            )

        result = await self._search(
            link,
            1,
        )

        if not result:
            return "0:00"

        return (
            result[0].get(
                "duration"
            )
            or "0:00"
        )

    # =====================================================
    # THUMBNAIL
    # =====================================================

    async def thumbnail(
        self,
        link: str,
        videoid: Union[
            bool,
            str,
        ] = None,
    ):

        if videoid:

            link = (
                self.base
                + str(link)
            )

        result = await self._search(
            link,
            1,
        )

        if not result:
            return None

        thumbnails = (
            result[0].get(
                "thumbnails"
            )
            or []
        )

        if not thumbnails:
            return None

        url = thumbnails[-1].get(
            "url"
        )

        if url:
            return url.split("?")[0]

        return None

    # =====================================================
    # VIDEO
    # =====================================================

    async def video(
        self,
        link: str,
        videoid: Union[
            bool,
            str,
        ] = None,
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
                "Invalid YouTube URL",
            )

        try:

            stream_url = await download_video(
                link
            )

            if stream_url:

                return (
                    1,
                    stream_url,
                )

            return (
                0,
                "Video stream failed",
            )

        except Exception as e:

            return (
                0,
                f"Video stream error: {e}",
            )

    # =====================================================
    # PLAYLIST
    # =====================================================

    async def playlist(
        self,
        link,
        limit,
        user_id=None,
        videoid: Union[
            bool,
            str,
        ] = None,
    ):

        if videoid:

            link = (
                self.listbase
                + str(link)
            )

        if not link:
            return []

        try:

            ytdl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "skip_download": True,
                "playlistend": int(limit),
            }

            with yt_dlp.YoutubeDL(
                ytdl_opts
            ) as ydl:

                info = ydl.extract_info(
                    link,
                    download=False,
                )

            if not info:
                return []

            entries = (
                info.get("entries")
                or []
            )

            ids = []

            for data in entries[
                :int(limit)
            ]:

                if not data:
                    continue

                vid = data.get(
                    "id"
                )

                if vid:
                    ids.append(
                        vid
                    )

            return ids

        except Exception:
            return []

    # =====================================================
    # TRACK
    # =====================================================

    async def track(
        self,
        link: str,
        videoid: Union[
            bool,
            str,
        ] = None,
    ):

        if videoid:

            link = (
                self.base
                + str(link)
            )

        result = await self._search(
            link,
            1,
        )

        if not result:

            return (
                None,
                None,
            )

        data = result[0]

        title = data.get(
            "title",
            "Unknown Title",
        )

        duration_min = (
            data.get(
                "duration"
            )
            or "0:00"
        )

        vidid = data.get(
            "id"
        )

        yturl = data.get(
            "link"
        )

        if not yturl and vidid:

            yturl = (
                self.base
                + vidid
            )

        thumbnails = (
            data.get(
                "thumbnails"
            )
            or []
        )

        thumbnail = None

        if thumbnails:

            thumbnail = (
                thumbnails[-1]
                .get("url")
            )

            if thumbnail:

                thumbnail = (
                    thumbnail.split("?")[0]
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
        videoid: Union[
            bool,
            str,
        ] = None,
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
                [],
                link,
            )

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
                    download=False,
                )

                if not info:

                    return (
                        [],
                        link,
                    )

                for fmt in (
                    info.get(
                        "formats",
                        [],
                    )
                ):

                    try:

                        format_name = str(
                            fmt.get(
                                "format",
                                "",
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
                link,
            )

        except Exception:
            return (
                [],
                link,
            )

    # =====================================================
    # SLIDER
    # =====================================================

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[
            bool,
            str,
        ] = None,
    ):

        if videoid:

            link = (
                self.base
                + str(link)
            )

        try:

            result = await self._search(
                link,
                10,
            )

            if not result:

                return (
                    None,
                    "0:00",
                    None,
                    None,
                )

            if query_type < 0:
                query_type = 0

            if query_type >= len(result):

                query_type = (
                    len(result) - 1
                )

            data = result[
                query_type
            ]

            title = data.get(
                "title",
                "Unknown Title",
            )

            duration_min = (
                data.get(
                    "duration"
                )
                or "0:00"
            )

            vidid = data.get(
                "id"
            )

            thumbnails = (
                data.get(
                    "thumbnails"
                )
                or []
            )

            thumbnail = None

            if thumbnails:

                thumbnail = (
                    thumbnails[-1]
                    .get("url")
                )

                if thumbnail:

                    thumbnail = (
                        thumbnail.split("?")[0]
                    )

            return (
                title,
                duration_min,
                thumbnail,
                vidid,
            )

        except Exception:

            return (
                None,
                "0:00",
                None,
                None,
            )

    # =====================================================
    # DOWNLOAD / FAST STREAM
    # =====================================================

    async def download(
        self,
        link: str,
        mystic,
        video: Union[
            bool,
            str,
        ] = None,
        videoid: Union[
            bool,
            str,
        ] = None,
        songaudio: Union[
            bool,
            str,
        ] = None,
        songvideo: Union[
            bool,
            str,
        ] = None,
        format_id: Union[
            bool,
            str,
        ] = None,
        title: Union[
            bool,
            str,
        ] = None,
    ):

        # -------------------------------------------------
        # Convert video ID to URL
        # -------------------------------------------------

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
                None,
                False,
            )

        try:

            # -------------------------------------------------
            # AUDIO
            # -------------------------------------------------

            if not video:

                stream_url = await download_song(
                    link
                )

            # -------------------------------------------------
            # VIDEO
            # -------------------------------------------------

            else:

                stream_url = await download_video(
                    link
                )

            if not stream_url:

                return (
                    None,
                    False,
                )

            # -------------------------------------------------
            # IMPORTANT:
            #
            # Do NOT check os.path.exists().
            #
            # stream_url is remote URL.
            # -------------------------------------------------

            return (
                stream_url,
                True,
            )

        except Exception:

            return (
                None,
                False,
            )


# =========================================================
# GLOBAL OBJECT
# =========================================================

YouTube = YouTubeAPI()
