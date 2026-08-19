import asyncio
import os
import re
from typing import Union

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

API_KEY = os.environ.get(
    "SHRUTI_API_KEY",
    "ShrutiBotsAlSpfeG7JItQmuoxCqKd",
)

DOWNLOAD_DIR = "downloads"


def time_to_seconds(time):
    if not time:
        return 0

    try:
        stringt = str(time)
        return sum(
            int(x) * 60 ** i
            for i, x in enumerate(
                reversed(stringt.split(":"))
            )
        )
    except Exception:
        return 0


async def download_song(link: str) -> Union[str, None]:
    try:
        if not link:
            return None

        video_id = None

        if "youtube.com/watch" in link and "v=" in link:
            video_id = link.split("v=", 1)[1].split("&", 1)[0]

        elif "youtu.be/" in link:
            video_id = link.split("youtu.be/", 1)[1].split("?", 1)[0]

        elif "youtube.com/shorts/" in link:
            video_id = link.split("/shorts/", 1)[1].split("?", 1)[0]

        else:
            video_id = link

        if not video_id or len(video_id) < 3:
            return None

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        file_path = os.path.join(
            DOWNLOAD_DIR,
            f"{video_id}.mp3",
        )

        if (
            os.path.exists(file_path)
            and os.path.getsize(file_path) > 0
        ):
            return file_path

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_URL}/download",
                params={
                    "url": video_id,
                    "type": "audio",
                    "api_key": API_KEY,
                },
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:

                if resp.status != 200:
                    return None

                with open(file_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(
                        131072
                    ):
                        f.write(chunk)

        if (
            os.path.exists(file_path)
            and os.path.getsize(file_path) > 0
        ):
            return file_path

        return None

    except Exception as e:
        print(f"download_song error: {e}")

        if "file_path" in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

        return None


async def download_video(link: str) -> Union[str, None]:
    try:
        if not link:
            return None

        video_id = None

        if "youtube.com/watch" in link and "v=" in link:
            video_id = link.split("v=", 1)[1].split("&", 1)[0]

        elif "youtu.be/" in link:
            video_id = link.split("youtu.be/", 1)[1].split("?", 1)[0]

        elif "youtube.com/shorts/" in link:
            video_id = link.split("/shorts/", 1)[1].split("?", 1)[0]

        else:
            video_id = link

        if not video_id or len(video_id) < 3:
            return None

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        file_path = os.path.join(
            DOWNLOAD_DIR,
            f"{video_id}.mp4",
        )

        if (
            os.path.exists(file_path)
            and os.path.getsize(file_path) > 0
        ):
            return file_path

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_URL}/download",
                params={
                    "url": video_id,
                    "type": "video",
                    "api_key": API_KEY,
                },
                timeout=aiohttp.ClientTimeout(total=600),
            ) as resp:

                if resp.status != 200:
                    return None

                with open(file_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(
                        131072
                    ):
                        f.write(chunk)

        if (
            os.path.exists(file_path)
            and os.path.getsize(file_path) > 0
        ):
            return file_path

        return None

    except Exception as e:
        print(f"download_video error: {e}")

        if "file_path" in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

        return None


class YouTubeAPI:

    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="

        self.reg = re.compile(
            r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
        )

    # =========================================================
    # URL HELPERS
    # =========================================================

    def clean_url(self, link: str) -> str:
        if not link:
            return link

        link = str(link).strip()

        # youtu.be
        if "youtu.be/" in link:
            video_id = (
                link.split("youtu.be/", 1)[1]
                .split("?", 1)[0]
                .split("&", 1)[0]
            )

            return f"{self.base}{video_id}"

        # Shorts
        if "youtube.com/shorts/" in link:
            video_id = (
                link.split("/shorts/", 1)[1]
                .split("?", 1)[0]
                .split("&", 1)[0]
            )

            return f"{self.base}{video_id}"

        # Normal watch URL
        if "youtube.com/watch" in link and "v=" in link:
            video_id = (
                link.split("v=", 1)[1]
                .split("&", 1)[0]
            )

            return f"{self.base}{video_id}"

        return link

    def extract_video_id(self, link: str):
        if not link:
            return None

        link = str(link).strip()

        if "youtube.com/watch" in link and "v=" in link:
            return (
                link.split("v=", 1)[1]
                .split("&", 1)[0]
            )

        if "youtu.be/" in link:
            return (
                link.split("youtu.be/", 1)[1]
                .split("?", 1)[0]
                .split("&", 1)[0]
            )

        if "youtube.com/shorts/" in link:
            return (
                link.split("/shorts/", 1)[1]
                .split("?", 1)[0]
                .split("&", 1)[0]
            )

        return None

    # =========================================================
    # CHECK YOUTUBE URL
    # =========================================================

    async def exists(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        try:
            if not link:
                return False

            if videoid:
                link = self.base + str(link)

            link = str(link).strip()

            return bool(
                re.search(
                    r"(https?://)?"
                    r"(www\.)?"
                    r"(youtube\.com/watch\?v=|"
                    r"youtube\.com/shorts/|"
                    r"youtu\.be/)",
                    link,
                    re.IGNORECASE,
                )
            )

        except Exception:
            return False

    # =========================================================
    # GET URL FROM MESSAGE
    # =========================================================

    async def url(
        self,
        message_1: Message,
    ) -> Union[str, None]:

        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(
                message_1.reply_to_message
            )

        for message in messages:

            if message.entities:

                for entity in message.entities:

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

            if message.caption_entities:

                for entity in message.caption_entities:

                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url

        return None

    # =========================================================
    # YT-DLP INFO
    # =========================================================

    async def _yt_dlp_info(self, link: str):

        try:

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": True,
                "noplaylist": True,
            }

            loop = asyncio.get_event_loop()

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                info = await loop.run_in_executor(
                    None,
                    lambda: ydl.extract_info(
                        link,
                        download=False,
                    ),
                )

            return info

        except Exception as e:

            print(
                f"yt-dlp info error: {type(e).__name__}: {e}"
            )

            return None

    # =========================================================
    # DETAILS
    # =========================================================

    async def details(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        try:

            if videoid:
                link = self.base + str(link)

            link = self.clean_url(link)

            info = await self._yt_dlp_info(link)

            if info:

                title = info.get(
                    "title",
                    "Unknown Title",
                )

                duration_sec = int(
                    info.get("duration") or 0
                )

                duration_min = (
                    f"{duration_sec // 60}:"
                    f"{duration_sec % 60:02d}"
                )

                vidid = info.get(
                    "id"
                )

                thumbnail = info.get(
                    "thumbnail"
                    or f"https://i.ytimg.com/vi/"
                    f"{vidid}/hqdefault.jpg"
                )

                return (
                    title,
                    duration_min,
                    duration_sec,
                    thumbnail,
                    vidid,
                )

            # Fallback search
            results = VideosSearch(
                link,
                limit=1,
            )

            data = await results.next()

            result_list = data.get(
                "result",
                [],
            )

            if not result_list:
                raise ValueError(
                    "No YouTube result found"
                )

            result = result_list[0]

            title = result.get(
                "title",
                "Unknown Title",
            )

            duration_min = (
                result.get("duration")
                or "0:00"
            )

            thumbnail = (
                result.get("thumbnails", [{}])[0]
                .get("url", "")
                .split("?")[0]
            )

            vidid = result.get("id")

            duration_sec = time_to_seconds(
                duration_min
            )

            return (
                title,
                duration_min,
                duration_sec,
                thumbnail,
                vidid,
            )

        except Exception as e:

            print(
                f"details error: {type(e).__name__}: {e}"
            )

            raise

    # =========================================================
    # TITLE
    # =========================================================

    async def title(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        try:

            if videoid:
                link = self.base + str(link)

            link = self.clean_url(link)

            info = await self._yt_dlp_info(link)

            if info:
                return info.get(
                    "title",
                    "Unknown Title",
                )

            results = VideosSearch(
                link,
                limit=1,
            )

            data = await results.next()

            result = data.get(
                "result",
                [],
            )

            if result:
                return result[0].get(
                    "title",
                    "Unknown Title",
                )

        except Exception as e:

            print(f"title error: {e}")

        return None

    # =========================================================
    # DURATION
    # =========================================================

    async def duration(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        try:

            if videoid:
                link = self.base + str(link)

            link = self.clean_url(link)

            info = await self._yt_dlp_info(link)

            if info:

                duration_sec = int(
                    info.get("duration") or 0
                )

                return (
                    f"{duration_sec // 60}:"
                    f"{duration_sec % 60:02d}"
                )

            results = VideosSearch(
                link,
                limit=1,
            )

            data = await results.next()

            result = data.get(
                "result",
                [],
            )

            if result:
                return result[0].get(
                    "duration"
                )

        except Exception as e:

            print(f"duration error: {e}")

        return None

    # =========================================================
    # THUMBNAIL
    # =========================================================

    async def thumbnail(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        try:

            if videoid:
                link = self.base + str(link)

            link = self.clean_url(link)

            info = await self._yt_dlp_info(link)

            if info:

                vidid = info.get("id")

                return (
                    info.get("thumbnail")
                    or
                    f"https://i.ytimg.com/vi/"
                    f"{vidid}/hqdefault.jpg"
                )

            results = VideosSearch(
                link,
                limit=1,
            )

            data = await results.next()

            result = data.get(
                "result",
                [],
            )

            if result:

                return (
                    result[0]
                    .get("thumbnails", [{}])[0]
                    .get("url", "")
                    .split("?")[0]
                )

        except Exception as e:

            print(f"thumbnail error: {e}")

        return None

    # =========================================================
    # VIDEO
    # =========================================================

    async def video(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        try:

            if videoid:
                link = self.base + str(link)

            link = self.clean_url(link)

            downloaded_file = (
                await download_video(link)
            )

            if downloaded_file:
                return 1, downloaded_file

            return 0, "Video download failed"

        except Exception as e:

            return (
                0,
                f"Video download error: {e}",
            )

    # =========================================================
    # PLAYLIST
    # =========================================================

    async def playlist(
        self,
        link,
        limit,
        user_id,
        videoid: Union[bool, str] = None,
    ):

        try:

            if videoid:
                link = self.listbase + str(link)

            if "&" in link:
                link = link.split("&")[0]

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "skip_download": True,
                "playlistend": limit,
            }

            loop = asyncio.get_event_loop()

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
            )[:limit]:

                if not entry:
                    continue

                vid = entry.get("id")

                if vid:
                    ids.append(vid)

            return ids

        except Exception as e:

            print(
                f"playlist error: {type(e).__name__}: {e}"
            )

            return []

    # =========================================================
    # RELATED VIDEOS
    # =========================================================

    async def get_related_videos(
        self,
        vidid: str,
    ):

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

        # Radio / Mix
        mix_url = (
            f"https://www.youtube.com/watch?v="
            f"{vidid}&list=RD{vidid}"
        )

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "playlist_items": "2-20",
        }

        try:

            loop = asyncio.get_event_loop()

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

            related = []

            for entry in (
                info.get("entries") or []
            ):

                if not entry:
                    continue

                candidate = entry.get("id")

                if (
                    not candidate
                    or candidate == vidid
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

                if candidate not in related:
                    related.append(candidate)

            if related:
                return related

        except Exception as e:

            print(
                f"related mix error: {e}"
            )

        # Search fallback
        try:

            current_title = await self.title(
                vidid,
                True,
            )

            if current_title:

                results = VideosSearch(
                    f"{current_title} related songs",
                    limit=10,
                )

                data = await results.next()

                related = []

                for result in data.get(
                    "result",
                    [],
                ):

                    candidate = result.get(
                        "id"
                    )

                    if (
                        not candidate
                        or candidate == vidid
                    ):
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

                    if candidate not in related:
                        related.append(candidate)

                return related

        except Exception as e:

            print(
                f"related search error: {e}"
            )

        return []

    # =========================================================
    # TRACK
    # =========================================================

    async def track(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        try:

            if not link:
                raise ValueError(
                    "Empty YouTube query"
                )

            if videoid:
                link = self.base + str(link)

            link = str(link).strip()

            # -------------------------------------------------
            # DIRECT YOUTUBE URL
            # -------------------------------------------------

            if await self.exists(link):

                link = self.clean_url(link)

                print(
                    f"Processing YouTube URL: {link}"
                )

                info = await self._yt_dlp_info(
                    link
                )

                if info:

                    title = info.get(
                        "title",
                        "Unknown Title",
                    )

                    duration_sec = int(
                        info.get("duration") or 0
                    )

                    vidid = info.get("id")

                    if not vidid:
                        raise ValueError(
                            "YouTube video ID not found"
                        )

                    duration_min = (
                        f"{duration_sec // 60}:"
                        f"{duration_sec % 60:02d}"
                    )

                    yturl = (
                        f"https://www.youtube.com/"
                        f"watch?v={vidid}"
                    )

                    thumbnail = (
                        info.get("thumbnail")
                        or
                        f"https://i.ytimg.com/vi/"
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

            # -------------------------------------------------
            # SEARCH QUERY
            # -------------------------------------------------

            print(
                f"Searching YouTube: {link}"
            )

            results = VideosSearch(
                link,
                limit=1,
            )

            data = await results.next()

            result_list = data.get(
                "result",
                [],
            )

            if not result_list:

                raise ValueError(
                    "No YouTube search result found"
                )

            result = result_list[0]

            title = result.get(
                "title",
                "Unknown Title",
            )

            duration_min = (
                result.get("duration")
                or "0:00"
            )

            vidid = result.get("id")

            if not vidid:
                raise ValueError(
                    "YouTube video ID not found"
                )

            yturl = result.get(
                "link"
            ) or (
                f"https://www.youtube.com/"
                f"watch?v={vidid}"
            )

            thumbnails = (
                result.get("thumbnails")
                or []
            )

            if thumbnails:

                thumbnail = (
                    thumbnails[0]
                    .get("url", "")
                    .split("?")[0]
                )

            else:

                thumbnail = (
                    f"https://i.ytimg.com/vi/"
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

        except Exception as e:

            print(
                f"YouTube.track ERROR: "
                f"{type(e).__name__}: {e}"
            )

            raise

    # =========================================================
    # FORMATS
    # =========================================================

    async def formats(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + str(link)

        link = self.clean_url(link)

        try:

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
            }

            loop = asyncio.get_event_loop()

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

            formats_available = []

            for fmt in info.get(
                "formats",
                [],
            ):

                try:

                    if (
                        "dash"
                        in str(
                            fmt.get(
                                "format",
                                "",
                            )
                        ).lower()
                    ):
                        continue

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

        except Exception as e:

            print(
                f"formats error: {e}"
            )

            return [], link

    # =========================================================
    # SLIDER
    # =========================================================

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + str(link)

        link = self.clean_url(link)

        results = VideosSearch(
            link,
            limit=10,
        )

        data = await results.next()

        result = data.get(
            "result",
            [],
        )

        if not result:
            raise ValueError(
                "No YouTube results"
            )

        if query_type >= len(result):
            query_type = 0

        selected = result[query_type]

        title = selected.get(
            "title",
            "Unknown Title",
        )

        duration_min = (
            selected.get("duration")
            or "0:00"
        )

        vidid = selected.get(
            "id"
        )

        thumbnails = (
            selected.get("thumbnails")
            or []
        )

        thumbnail = (
            thumbnails[0].get("url", "")
            .split("?")[0]
            if thumbnails
            else
            f"https://i.ytimg.com/vi/"
            f"{vidid}/hqdefault.jpg"
        )

        return (
            title,
            duration_min,
            thumbnail,
            vidid,
        )

    # =========================================================
    # DOWNLOAD
    # =========================================================

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

            link = self.clean_url(link)

            if video:
                downloaded_file = (
                    await download_video(link)
                )

            else:
                downloaded_file = (
                    await download_song(link)
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
                f"download error: {e}"
            )

            return (
                None,
                False,
            )


# =============================================================
# GLOBAL YOUTUBE OBJECT
# =============================================================

YouTube = YouTubeAPI()
