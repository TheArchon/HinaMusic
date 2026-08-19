#
# Copyright (C) 2025-present by TheAloneTeam@Github.
#
# This file is part of AloneMusic project,
# and is released under the MIT License.
#
# All rights reserved.
#

import asyncio
import logging
import os
import random
import re
import time
import urllib.parse
from typing import Optional

import aiohttp
from py_yt import VideosSearch

try:
    from py_yt import Playlist
except ImportError:
    Playlist = None

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

from AloneMusic.helpers import Track, utils


# =========================================================
# LOGGER
# =========================================================

logger = logging.getLogger("AloneMusic.YouTube")


# =========================================================
# CONFIG
# =========================================================

API_URL = os.getenv(
    "API_URL",
    "https://web.riteshyt.in",
).rstrip("/")

API_KEY = os.getenv(
    "API_KEY",
    "",
)

REQUEST_TIMEOUT = int(
    os.getenv(
        "YOUTUBE_REQUEST_TIMEOUT",
        "60",
    )
)

PREFETCH_COOLDOWN = int(
    os.getenv(
        "YOUTUBE_PREFETCH_COOLDOWN",
        "15",
    )
)


# =========================================================
# DOWNLOAD ASSISTANT
# =========================================================

async def download_assistant(
    query: str,
    dl_type: str,
) -> str:

    safe_query = urllib.parse.quote(
        str(query),
        safe="",
    )

    extension = (
        "mp3"
        if dl_type == "audio"
        else "mp4"
    )

    if API_KEY:

        return (
            f"{API_URL}/downloads/"
            f"{API_KEY}/"
            f"{safe_query}.{extension}"
        )

    return (
        f"{API_URL}/downloads/stream"
        f"?query={safe_query}"
        f"&dl_type="
        f"{urllib.parse.quote(dl_type)}"
    )


# =========================================================
# YOUTUBE
# =========================================================

class YouTube:

    def __init__(self):

        self.base = (
            "https://www.youtube.com/watch?v="
        )

        self.cookies = []
        self.checked = False
        self.warned = False

        self.cookie_dir = (
            "AloneMusic/cookies"
        )

        self._client: Optional[
            aiohttp.ClientSession
        ] = None

        self._recent_prefetches = {}

        self.regex = re.compile(
            r"^(?:"
            r"(?:https?://)?"
            r"(?:www\.|m\.|music\.)?"
            r"(?:youtube\.com/"
            r"(?:watch\?v=|shorts/)"
            r"|youtu\.be/)"
            r"[A-Za-z0-9_-]{11}"
            r"(?:[&?][^\s]*)?"
            r"|"
            r"(?:https?://)?"
            r"(?:www\.|m\.|music\.)?"
            r"youtube\.com/"
            r"playlist\?list="
            r"PL[A-Za-z0-9_-]+"
            r"(?:[&?][^\s]*)?"
            r")$",
            re.IGNORECASE,
        )

        self.iregex = re.compile(
            r"https?://"
            r"(?:www\.|m\.|music\.)?"
            r"(?:youtube\.com|youtu\.be)"
            r"(?!"
            r"/watch\?v=[A-Za-z0-9_-]{11}"
            r"|/shorts/[A-Za-z0-9_-]{11}"
            r"|/playlist\?list="
            r"PL[A-Za-z0-9_-]+"
            r"|/[A-Za-z0-9_-]{11}"
            r")\S*",
            re.IGNORECASE,
        )

    # =====================================================
    # HTTP CLIENT
    # =====================================================

    async def get_client(
        self,
    ) -> aiohttp.ClientSession:

        if (
            self._client is None
            or self._client.closed
        ):

            timeout = aiohttp.ClientTimeout(
                total=REQUEST_TIMEOUT,
                connect=10,
                sock_connect=10,
                sock_read=REQUEST_TIMEOUT,
            )

            connector = aiohttp.TCPConnector(
                limit=50,
                limit_per_host=20,
                ttl_dns_cache=300,
                enable_cleanup_closed=True,
            )

            self._client = (
                aiohttp.ClientSession(
                    timeout=timeout,
                    connector=connector,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 "
                            "(Linux; Android 10) "
                            "AppleWebKit/537.36 "
                            "(KHTML, like Gecko) "
                            "Chrome/131.0 "
                            "Mobile Safari/537.36"
                        )
                    },
                )
            )

        return self._client

    # =====================================================
    # COOKIE
    # =====================================================

    def get_cookies(self):

        if not self.checked:

            self.cookies.clear()

            try:

                if os.path.isdir(
                    self.cookie_dir
                ):

                    for filename in os.listdir(
                        self.cookie_dir
                    ):

                        if filename.endswith(
                            ".txt"
                        ):

                            self.cookies.append(
                                os.path.join(
                                    self.cookie_dir,
                                    filename,
                                )
                            )

            except Exception as e:

                logger.warning(
                    f"Cookie scan failed: {e}"
                )

            self.checked = True

        if not self.cookies:

            if not self.warned:

                self.warned = True

                logger.warning(
                    "YouTube cookies are missing."
                )

            return None

        return random.choice(
            self.cookies
        )

    # =====================================================
    # SAVE COOKIES
    # =====================================================

    async def save_cookies(
        self,
        urls: list[str],
    ) -> None:

        os.makedirs(
            self.cookie_dir,
            exist_ok=True,
        )

        logger.info(
            "Saving YouTube cookies..."
        )

        timeout = aiohttp.ClientTimeout(
            total=60
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            for url in urls:

                try:

                    name = (
                        url
                        .rstrip("/")
                        .split("/")[-1]
                    )

                    if not name:
                        continue

                    raw_url = (
                        "https://batbin.me/raw/"
                        + name
                    )

                    async with session.get(
                        raw_url
                    ) as response:

                        response.raise_for_status()

                        path = os.path.join(
                            self.cookie_dir,
                            f"{name}.txt",
                        )

                        with open(
                            path,
                            "wb",
                        ) as file:

                            file.write(
                                await response.read()
                            )

                except Exception as e:

                    logger.error(
                        f"Cookie save failed: {e}"
                    )

        self.checked = False
        self.cookies.clear()

        logger.info(
            "YouTube cookies saved."
        )

    # =====================================================
    # VALIDATION
    # =====================================================

    def valid(
        self,
        url: str,
    ) -> bool:

        if not url:
            return False

        return bool(
            self.regex.match(
                str(url).strip()
            )
        )

    def invalid(
        self,
        url: str,
    ) -> bool:

        if not url:
            return False

        return bool(
            self.iregex.match(
                str(url).strip()
            )
        )

    # =====================================================
    # CLEAN LINK
    # =====================================================

    def _clean_link(
        self,
        link: str,
    ) -> str:

        if not link:
            return ""

        link = str(link).strip()

        try:

            parsed = urllib.parse.urlparse(
                link
            )

            if parsed.query:

                query = urllib.parse.parse_qs(
                    parsed.query,
                    keep_blank_values=True,
                )

                allowed = {}

                if "v" in query:
                    allowed["v"] = query["v"]

                if "list" in query:
                    allowed["list"] = query["list"]

                if "index" in query:
                    allowed["index"] = query["index"]

                new_query = (
                    urllib.parse.urlencode(
                        allowed,
                        doseq=True,
                    )
                )

                link = (
                    urllib.parse.urlunparse(
                        (
                            parsed.scheme,
                            parsed.netloc,
                            parsed.path,
                            parsed.params,
                            new_query,
                            "",
                        )
                    )
                )

        except Exception:
            pass

        return link

    # =====================================================
    # VIDEO ID
    # =====================================================

    def _get_video_id(
        self,
        link: str,
    ) -> Optional[str]:

        if not link:
            return None

        link = str(link).strip()

        patterns = [

            r"(?:v=)"
            r"([A-Za-z0-9_-]{11})",

            r"youtu\.be/"
            r"([A-Za-z0-9_-]{11})",

            r"/shorts/"
            r"([A-Za-z0-9_-]{11})",

            r"/embed/"
            r"([A-Za-z0-9_-]{11})",
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
    # BUILD TRACK
    # =====================================================

    def _build_track(
        self,
        data: dict,
        m_id: int = 0,
        user: str = "",
        video: bool = False,
    ) -> Optional[Track]:

        if not data:
            return None

        video_id = data.get("id")

        if not video_id:
            return None

        thumbnails = (
            data.get("thumbnails")
            or []
        )

        thumbnail = ""

        if thumbnails:

            try:

                thumbnail = (
                    thumbnails[-1]
                    .get("url")
                    or ""
                ).split("?")[0]

            except Exception:
                thumbnail = ""

        channel = (
            data.get("channel")
            or {}
        )

        duration = (
            data.get("duration")
            or "00:00"
        )

        title = (
            data.get("title")
            or "Unknown"
        )

        link = (
            data.get("link")
            or (
                self.base
                + video_id
            )
        )

        try:

            duration_sec = (
                utils.to_seconds(
                    duration
                )
            )

        except Exception:

            duration_sec = 0

        try:

            return Track(
                id=video_id,
                channel_name=(
                    channel.get(
                        "name",
                        "",
                    )
                ),
                duration=duration,
                duration_sec=duration_sec,
                message_id=m_id,
                title=title[:25],
                thumbnail=thumbnail,
                url=link,
                user=user,
                view_count=(
                    data.get(
                        "viewCount",
                        {},
                    ).get(
                        "short",
                        "",
                    )
                ),
                video=video,
            )

        except TypeError:

            # Some AloneMusic Track versions
            # may not accept every optional field.

            try:

                return Track(
                    id=video_id,
                    channel_name=(
                        channel.get(
                            "name",
                            "",
                        )
                    ),
                    duration=duration,
                    duration_sec=duration_sec,
                    message_id=m_id,
                    title=title[:25],
                    thumbnail=thumbnail,
                    url=link,
                    user=user,
                    video=video,
                )

            except Exception as e:

                logger.error(
                    f"Track creation failed: {e}"
                )

        return None

    # =====================================================
    # SEARCH
    # =====================================================

    async def search(
        self,
        query: str,
        m_id: int,
        video: bool = False,
    ) -> Track | None:

        if not query:
            return None

        client = await self.get_client()

        params = {
            "query": query,
            "limit": 1,
        }

        if API_KEY:
            params["api_key"] = API_KEY

        # -------------------------------------------------
        # API SEARCH
        # -------------------------------------------------

        try:

            async with client.get(
                f"{API_URL}/search",
                params=params,
            ) as response:

                if response.status == 200:

                    result_data = (
                        await response.json(
                            content_type=None
                        )
                    )

                    results = (
                        result_data.get(
                            "result"
                        )
                        or []
                    )

                    if results:

                        track = (
                            self._build_track(
                                results[0],
                                m_id=m_id,
                                video=video,
                            )
                        )

                        if track:
                            return track

        except Exception as e:

            logger.warning(
                f"API search failed: {e}"
            )

        # -------------------------------------------------
        # PY_YT SEARCH
        # -------------------------------------------------

        try:

            search = VideosSearch(
                query,
                limit=1,
                with_live=False,
            )

            result = await search.next()

            results = (
                result.get("result")
                if result
                else []
            )

            if results:

                track = (
                    self._build_track(
                        results[0],
                        m_id=m_id,
                        video=video,
                    )
                )

                if track:
                    return track

        except Exception as e:

            logger.warning(
                f"py_yt search failed: {e}"
            )

        # -------------------------------------------------
        # YT-DLP FALLBACK
        # -------------------------------------------------

        if yt_dlp:

            try:

                loop = asyncio.get_running_loop()

                def do_search():

                    options = {
                        "quiet": True,
                        "no_warnings": True,
                        "skip_download": True,
                        "extract_flat": True,
                    }

                    with yt_dlp.YoutubeDL(
                        options
                    ) as ydl:

                        return ydl.extract_info(
                            f"ytsearch1:{query}",
                            download=False,
                        )

                data = await loop.run_in_executor(
                    None,
                    do_search,
                )

                entries = (
                    data.get("entries")
                    if data
                    else []
                )

                if entries:

                    item = entries[0]

                    item["id"] = item.get(
                        "id"
                    )

                    item["link"] = (
                        item.get("webpage_url")
                        or (
                            self.base
                            + item["id"]
                        )
                    )

                    track = (
                        self._build_track(
                            item,
                            m_id=m_id,
                            video=video,
                        )
                    )

                    if track:
                        return track

            except Exception as e:

                logger.warning(
                    f"yt-dlp search failed: {e}"
                )

        return None

    # =====================================================
    # PLAYLIST
    # =====================================================

    async def playlist(
        self,
        limit: int,
        user: str,
        url: str,
        video: bool,
    ) -> list[Track | None]:

        url = self._clean_link(
            url
        )

        if not url:
            return []

        client = await self.get_client()

        params = {
            "link": url,
            "limit": limit,
        }

        if API_KEY:
            params["api_key"] = API_KEY

        # -------------------------------------------------
        # API PLAYLIST
        # -------------------------------------------------

        try:

            async with client.get(
                f"{API_URL}/playlist",
                params=params,
            ) as response:

                if response.status == 200:

                    data = (
                        await response.json(
                            content_type=None
                        )
                    )

                    videos = (
                        data.get("videos")
                        or []
                    )

                    tracks = []

                    for item in videos[:limit]:

                        track = (
                            self._build_track(
                                item,
                                user=user,
                                video=video,
                            )
                        )

                        if track:
                            tracks.append(
                                track
                            )

                    if tracks:
                        return tracks

        except Exception as e:

            logger.warning(
                f"API playlist failed: {e}"
            )

        # -------------------------------------------------
        # PY_YT PLAYLIST
        # -------------------------------------------------

        if Playlist:

            try:

                data = await Playlist.get(
                    url
                )

                videos = (
                    data.get("videos")
                    or []
                )

                tracks = []

                for item in videos[:limit]:

                    track = (
                        self._build_track(
                            item,
                            user=user,
                            video=video,
                        )
                    )

                    if track:
                        tracks.append(
                            track
                        )

                if tracks:
                    return tracks

            except Exception as e:

                logger.warning(
                    f"py_yt playlist failed: {e}"
                )

        # -------------------------------------------------
        # YT-DLP PLAYLIST FALLBACK
        # -------------------------------------------------

        if yt_dlp:

            try:

                loop = asyncio.get_running_loop()

                def load_playlist():

                    options = {
                        "quiet": True,
                        "no_warnings": True,
                        "skip_download": True,
                        "extract_flat": True,
                        "playlistend": limit,
                    }

                    with yt_dlp.YoutubeDL(
                        options
                    ) as ydl:

                        return ydl.extract_info(
                            url,
                            download=False,
                        )

                data = await loop.run_in_executor(
                    None,
                    load_playlist,
                )

                entries = (
                    data.get("entries")
                    if data
                    else []
                )

                tracks = []

                for item in entries or []:

                    if not item:
                        continue

                    video_id = item.get(
                        "id"
                    )

                    if not video_id:
                        continue

                    item["link"] = (
                        item.get(
                            "webpage_url"
                        )
                        or (
                            self.base
                            + video_id
                        )
                    )

                    track = (
                        self._build_track(
                            item,
                            user=user,
                            video=video,
                        )
                    )

                    if track:
                        tracks.append(
                            track
                        )

                    if len(tracks) >= limit:
                        break

                return tracks

            except Exception as e:

                logger.warning(
                    f"yt-dlp playlist failed: {e}"
                )

        return []

    # =====================================================
    # PREFETCH
    # =====================================================

    async def prefetch(
        self,
        link: str,
        video: bool = False,
    ):

        link = self._clean_link(
            link
        )

        if not link:
            return False

        dl_type = (
            "video"
            if video
            else "audio"
        )

        video_id = (
            self._get_video_id(
                link
            )
        )

        cache_id = (
            video_id
            or link
        )

        cache_key = (
            f"{cache_id}_{dl_type}"
        )

        now = time.time()

        previous = (
            self._recent_prefetches.get(
                cache_key
            )
        )

        if (
            previous is not None
            and (
                now - previous
                < PREFETCH_COOLDOWN
            )
        ):
            return True

        self._recent_prefetches[
            cache_key
        ] = now

        # -------------------------------------------------
        # Cleanup
        # -------------------------------------------------

        if len(
            self._recent_prefetches
        ) > 100:

            self._recent_prefetches = {
                key: value
                for key, value
                in self._recent_prefetches.items()
                if now - value < 300
            }

        client = await self.get_client()

        params = {
            "query": link,
            "dl_type": dl_type,
            "prefetch": "true",
        }

        if API_KEY:
            params["api_key"] = API_KEY

        try:

            async with client.get(
                f"{API_URL}/download",
                params=params,
                timeout=aiohttp.ClientTimeout(
                    total=30
                ),
            ) as response:

                await response.read()

                if response.status >= 400:

                    logger.warning(
                        f"Prefetch returned "
                        f"HTTP {response.status}"
                    )

                    return False

                return True

        except asyncio.CancelledError:

            raise

        except Exception as e:

            logger.warning(
                f"Prefetch failed: {e}"
            )

            return False

    # =====================================================
    # AUTOPLAY / RELATED
    # =====================================================

    async def get_related(
        self,
        video_id: str,
        video: bool = False,
        max_duration: int = 0,
    ) -> Track | None:

        """
        Recommendations has intentionally been removed.

        Some py_yt versions do not provide:
            Recommendations

        Therefore autoplay uses YouTube search
        instead of importing Recommendations.
        """

        try:

            if not video_id:
                return None

            # Search by the current video's ID.
            # If that fails, simply return None.
            search = VideosSearch(
                video_id,
                limit=5,
                with_live=False,
            )

            result = await search.next()

            results = (
                result.get("result")
                if result
                else []
            )

            if not results:
                return None

            candidates = []

            for item in results:

                item_id = item.get(
                    "id"
                )

                if not item_id:
                    continue

                if item_id == video_id:
                    continue

                if max_duration:

                    duration = utils.to_seconds(
                        item.get(
                            "duration"
                        )
                        or "00:00"
                    )

                    if (
                        duration
                        > max_duration
                    ):
                        continue

                candidates.append(
                    item
                )

            if not candidates:
                return None

            selected = random.choice(
                candidates
            )

            return self._build_track(
                selected,
                user="Autoplay",
                video=video,
            )

        except Exception as e:

            logger.warning(
                f"Autoplay failed: {e}"
            )

        return None

    # =====================================================
    # FAST DOWNLOAD
    # =====================================================

    async def download(
        self,
        video_id: str,
        video: bool = False,
    ) -> str | None:

        """
        FAST START STREAM.

        No:
            - 1024 byte test
            - extra stream request
            - waiting for stream readiness

        The URL is returned immediately.
        """

        if not video_id:
            return None

        video_id = str(
            video_id
        ).strip()

        # -------------------------------------------------
        # Extract ID if full URL was passed
        # -------------------------------------------------

        extracted = (
            self._get_video_id(
                video_id
            )
        )

        if extracted:

            video_id = extracted

        # -------------------------------------------------
        # Validate
        # -------------------------------------------------

        if not re.fullmatch(
            r"[A-Za-z0-9_-]{11}",
            video_id,
        ):

            logger.warning(
                f"Invalid YouTube video ID: "
                f"{video_id}"
            )

            return None

        youtube_url = (
            self.base
            + video_id
        )

        dl_type = (
            "video"
            if video
            else "audio"
        )

        # -------------------------------------------------
        # BACKGROUND PREFETCH
        # -------------------------------------------------

        try:

            asyncio.create_task(
                self.prefetch(
                    youtube_url,
                    video=video,
                )
            )

        except Exception as e:

            logger.warning(
                f"Prefetch task failed: {e}"
            )

        # -------------------------------------------------
        # STREAM URL
        # -------------------------------------------------

        if API_KEY:

            extension = (
                "mp4"
                if video
                else "mp3"
            )

            stream_url = (
                f"{API_URL}/downloads/"
                f"{API_KEY}/youtube.com/"
                f"{video_id}.{extension}"
            )

        else:

            stream_url = (
                await download_assistant(
                    youtube_url,
                    dl_type,
                )
            )

        # -------------------------------------------------
        # DO NOT CHECK THE STREAM HERE
        #
        # Old code was doing:
        #
        # client.get(stream_url)
        # response.content.read(1024)
        #
        # That adds startup delay.
        # -------------------------------------------------

        return stream_url

    # =====================================================
    # CLOSE
    # =====================================================

    async def close(self):

        if (
            self._client
            and not self._client.closed
        ):

            try:

                await self._client.close()

            except Exception as e:

                logger.warning(
                    f"HTTP client close failed: {e}"
                )

            self._client = None
