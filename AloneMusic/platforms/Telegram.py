#
# Copyright (C) 2025-present by TheAloneTeam@Github, < https://github.com/TheAloneTeam >.
#
# This file is part of < https://github.com/TheAloneTeam/KartikMusic > project,
# and is released under the "MIT License".
# Please see < https://github.com/TheAloneTeam/KartikMusic/blob/master/LICENSE >
#
# All rights reserved.
#

import asyncio
import os
import random
import re
import time
import urllib.parse
from typing import Optional

import aiohttp
from py_yt import Playlist, Recommendations, VideosSearch

from AloneMusic import logger
from AloneMusic.helpers import Track, utils


# =========================================================
# CONFIG
# =========================================================

API_URL = os.getenv(
    "API_URL",
    "https://web.riteshyt.in",
).rstrip("/")

API_KEY = os.getenv("API_KEY", "")

REQUEST_TIMEOUT = int(os.getenv("YOUTUBE_REQUEST_TIMEOUT", "60"))
PREFETCH_COOLDOWN = int(os.getenv("YOUTUBE_PREFETCH_COOLDOWN", "15"))


# =========================================================
# DOWNLOAD ASSISTANT
# =========================================================

async def download_assistant(query: str, dl_type: str) -> str:
    """
    Build a direct stream/download URL from the configured API.
    """

    safe_query = urllib.parse.quote(str(query), safe="")

    ext = "mp3" if dl_type == "audio" else "mp4"

    if API_KEY:
        return (
            f"{API_URL}/downloads/"
            f"{API_KEY}/"
            f"{safe_query}.{ext}"
        )

    return (
        f"{API_URL}/downloads/stream"
        f"?query={safe_query}"
        f"&dl_type={urllib.parse.quote(dl_type)}"
    )


# =========================================================
# YOUTUBE
# =========================================================

class YouTube:

    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="

        self.cookies = []
        self.checked = False
        self.warned = False

        self.cookie_dir = "KartikMusic/cookies"

        # vid_id + type -> timestamp
        self._recent_prefetches = {}

        self._client: Optional[aiohttp.ClientSession] = None

        # -------------------------------------------------
        # YouTube URL regex
        # -------------------------------------------------

        self.regex = re.compile(
            r"^(?:"
            r"(?:https?://)?"
            r"(?:www\.|m\.|music\.)?"
            r"(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)"
            r"[A-Za-z0-9_-]{11}"
            r"(?:[&?][^\s]*)?"
            r"|"
            r"(?:https?://)?"
            r"(?:www\.|m\.|music\.)?"
            r"youtube\.com/playlist\?list=PL[A-Za-z0-9_-]+"
            r"(?:[&?][^\s]*)?"
            r")$",
            re.IGNORECASE,
        )

        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?"
            r"(?:youtube\.com|youtu\.be)"
            r"(?!"
            r"/watch\?v=[A-Za-z0-9_-]{11}"
            r"|/shorts/[A-Za-z0-9_-]{11}"
            r"|/playlist\?list=PL[A-Za-z0-9_-]+"
            r"|/[A-Za-z0-9_-]{11}"
            r")"
            r"\S*",
            re.IGNORECASE,
        )

    # =====================================================
    # HTTP CLIENT
    # =====================================================

    async def get_client(self) -> aiohttp.ClientSession:
        """
        Reuse one aiohttp session.
        This avoids creating a new TCP connection for every request.
        """

        if self._client is None or self._client.closed:

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

            self._client = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Linux; Android 10) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/131.0 Mobile Safari/537.36"
                    )
                },
            )

        return self._client

    # =====================================================
    # COOKIES
    # =====================================================

    def get_cookies(self):

        if not self.checked:

            self.cookies.clear()

            if os.path.isdir(self.cookie_dir):

                try:
                    for file in os.listdir(self.cookie_dir):

                        if file.endswith(".txt"):
                            self.cookies.append(
                                os.path.join(
                                    self.cookie_dir,
                                    file,
                                )
                            )

                except Exception as e:
                    logger.warning(
                        f"Unable to read cookie directory: {e}"
                    )

            self.checked = True

        if not self.cookies:

            if not self.warned:
                self.warned = True

                logger.warning(
                    "YouTube cookies are missing; "
                    "some downloads may fail."
                )

            return None

        return random.choice(self.cookies)

    # =====================================================
    # SAVE COOKIES
    # =====================================================

    async def save_cookies(self, urls: list[str]) -> None:

        logger.info("Saving cookies from URLs...")

        os.makedirs(
            self.cookie_dir,
            exist_ok=True,
        )

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60)
        ) as session:

            for url in urls:

                try:

                    name = url.rstrip("/").split("/")[-1]

                    if not name:
                        continue

                    link = (
                        "https://batbin.me/raw/"
                        + name
                    )

                    async with session.get(link) as resp:

                        resp.raise_for_status()

                        path = os.path.join(
                            self.cookie_dir,
                            f"{name}.txt",
                        )

                        with open(path, "wb") as fw:
                            fw.write(await resp.read())

                except Exception as e:

                    logger.error(
                        f"Failed to save cookie {url}: {e}"
                    )

        # Refresh cookie list
        self.checked = False
        self.cookies.clear()

        logger.info(
            f"Cookies saved in {self.cookie_dir}."
        )

    # =====================================================
    # URL VALIDATION
    # =====================================================

    def valid(self, url: str) -> bool:

        if not url:
            return False

        return bool(
            self.regex.match(
                str(url).strip()
            )
        )

    def invalid(self, url: str) -> bool:

        if not url:
            return False

        return bool(
            self.iregex.match(
                str(url).strip()
            )
        )

    # =====================================================
    # CLEAN YOUTUBE LINK
    # =====================================================

    def _clean_link(self, link: str) -> str:

        if not link:
            return ""

        link = str(link).strip()

        # Remove tracking parameters
        try:

            parsed = urllib.parse.urlparse(link)

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

                new_query = urllib.parse.urlencode(
                    allowed,
                    doseq=True,
                )

                link = urllib.parse.urlunparse(
                    (
                        parsed.scheme,
                        parsed.netloc,
                        parsed.path,
                        parsed.params,
                        new_query,
                        "",
                    )
                )

        except Exception:
            pass

        return link

    # =====================================================
    # SEARCH
    # =====================================================

    async def search(
        self,
        query: str,
        m_id: int,
        video: bool = False,
    ) -> Track | None:

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

                    result_data = await response.json(
                        content_type=None
                    )

                    result = result_data.get("result")

                    if result:

                        data = result[0]

                        thumbnails = data.get(
                            "thumbnails"
                        ) or []

                        thumbnail = ""

                        if thumbnails:

                            thumbnail = (
                                thumbnails[-1]
                                .get("url")
                                or ""
                            )

                            thumbnail = (
                                thumbnail.split("?")[0]
                            )

                        duration = data.get(
                            "duration"
                        )

                        return Track(
                            id=data.get("id"),
                            channel_name=(
                                data.get("channel", {})
                                .get("name")
                            ),
                            duration=duration,
                            duration_sec=utils.to_seconds(
                                duration
                            ),
                            message_id=m_id,
                            title=(
                                data.get("title")
                                or "Unknown"
                            )[:25],
                            thumbnail=thumbnail,
                            url=data.get("link"),
                            view_count=(
                                data.get("viewCount", {})
                                .get("short")
                            ),
                            video=video,
                        )

        except Exception as e:

            logger.warning(
                f"YouTube API search failed: {e}"
            )

        # -------------------------------------------------
        # FALLBACK SEARCH
        # -------------------------------------------------

        try:

            _search = VideosSearch(
                query,
                limit=1,
                with_live=False,
            )

            results = await _search.next()

            if results and results.get("result"):

                data = results["result"][0]

                thumbnails = (
                    data.get("thumbnails")
                    or []
                )

                thumbnail = ""

                if thumbnails:

                    thumbnail = (
                        thumbnails[-1]
                        .get("url")
                        or ""
                    ).split("?")[0]

                duration = data.get(
                    "duration"
                )

                return Track(
                    id=data.get("id"),
                    channel_name=(
                        data.get("channel", {})
                        .get("name")
                    ),
                    duration=duration,
                    duration_sec=utils.to_seconds(
                        duration
                    ),
                    message_id=m_id,
                    title=(
                        data.get("title")
                        or "Unknown"
                    )[:25],
                    thumbnail=thumbnail,
                    url=data.get("link"),
                    view_count=(
                        data.get("viewCount", {})
                        .get("short")
                    ),
                    video=video,
                )

        except Exception as e:

            logger.warning(
                f"Fallback YouTube search failed: {e}"
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

        url = self._clean_link(url)

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

                    data = await response.json(
                        content_type=None
                    )

                    videos = data.get("videos")

                    if videos:

                        tracks = []

                        for item in videos[:limit]:

                            thumbnails = (
                                item.get("thumbnails")
                                or []
                            )

                            thumbnail = ""

                            if thumbnails:

                                thumbnail = (
                                    thumbnails[-1]
                                    .get("url")
                                    or ""
                                ).split("?")[0]

                            link = (
                                item.get("link")
                                or ""
                            )

                            link = link.split(
                                "&list="
                            )[0]

                            duration = item.get(
                                "duration"
                            )

                            tracks.append(
                                Track(
                                    id=item.get("id"),
                                    channel_name=(
                                        item.get(
                                            "channel",
                                            {},
                                        ).get(
                                            "name",
                                            "",
                                        )
                                    ),
                                    duration=duration,
                                    duration_sec=(
                                        utils.to_seconds(
                                            duration
                                        )
                                    ),
                                    title=(
                                        item.get(
                                            "title"
                                        )
                                        or "Unknown"
                                    )[:25],
                                    thumbnail=thumbnail,
                                    url=link,
                                    user=user,
                                    view_count="",
                                    video=video,
                                )
                            )

                        if tracks:
                            return tracks

        except Exception as e:

            logger.warning(
                f"Playlist API failed: {e}"
            )

        # -------------------------------------------------
        # FALLBACK PLAYLIST
        # -------------------------------------------------

        tracks = []

        try:

            plist = await Playlist.get(url)

            videos = (
                plist.get("videos")
                or []
            )

            for item in videos[:limit]:

                thumbnails = (
                    item.get("thumbnails")
                    or []
                )

                thumbnail = ""

                if thumbnails:

                    thumbnail = (
                        thumbnails[-1]
                        .get("url")
                        or ""
                    ).split("?")[0]

                link = (
                    item.get("link")
                    or ""
                )

                link = link.split(
                    "&list="
                )[0]

                duration = item.get(
                    "duration"
                )

                tracks.append(
                    Track(
                        id=item.get("id"),
                        channel_name=(
                            item.get(
                                "channel",
                                {},
                            ).get(
                                "name",
                                "",
                            )
                        ),
                        duration=duration,
                        duration_sec=utils.to_seconds(
                            duration
                        ),
                        title=(
                            item.get("title")
                            or "Unknown"
                        )[:25],
                        thumbnail=thumbnail,
                        url=link,
                        user=user,
                        view_count="",
                        video=video,
                    )
                )

        except Exception as e:

            logger.warning(
                f"Fallback playlist failed: {e}"
            )

        return tracks

    # =====================================================
    # PREFETCH
    # =====================================================

    async def prefetch(
        self,
        link: str,
        video: bool = False,
    ):

        dl_type = (
            "video"
            if video
            else "audio"
        )

        link = self._clean_link(link)

        if not link:
            return False

        # -------------------------------------------------
        # Extract video ID
        # -------------------------------------------------

        video_id = None

        patterns = [
            r"(?:v=)([A-Za-z0-9_-]{11})",
            r"youtu\.be/([A-Za-z0-9_-]{11})",
            r"/shorts/([A-Za-z0-9_-]{11})",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                link,
                re.IGNORECASE,
            )

            if match:

                video_id = match.group(1)
                break

        vidid = video_id or link

        cache_key = (
            f"{vidid}_{dl_type}"
        )

        now = time.time()

        last_time = (
            self._recent_prefetches.get(
                cache_key
            )
        )

        # Avoid duplicate prefetch
        if (
            last_time is not None
            and now - last_time < PREFETCH_COOLDOWN
        ):
            return True

        self._recent_prefetches[
            cache_key
        ] = now

        # Cleanup
        if len(self._recent_prefetches) > 100:

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

            # IMPORTANT:
            # This request runs in background.
            # download() does NOT wait for it.
            async with client.get(
                f"{API_URL}/download",
                params=params,
                timeout=aiohttp.ClientTimeout(
                    total=30
                ),
            ) as response:

                # Consume response body so connection
                # can be reused by aiohttp.
                await response.read()

                if response.status >= 400:

                    logger.warning(
                        f"Prefetch returned "
                        f"{response.status}: {link}"
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
    # RELATED / AUTOPLAY
    # =====================================================

    async def get_related(
        self,
        video_id: str,
        video: bool = False,
        max_duration: int = 0,
    ) -> Track | None:

        try:

            results_data = (
                await Recommendations.getRelated(
                    video_id
                )
            )

            if not isinstance(
                results_data,
                dict,
            ):
                return None

            results = (
                results_data.get("result")
                or []
            )

            videos = [
                item
                for item in results
                if item.get("type") == "video"
            ]

            if max_duration:

                videos = [
                    item
                    for item in videos
                    if utils.to_seconds(
                        item.get(
                            "duration"
                        )
                        or "00:00"
                    )
                    <= max_duration
                ]

            if not videos:
                return None

            data = random.choice(
                videos
            )

            thumbnails = (
                data.get("thumbnails")
                or []
            )

            thumbnail = ""

            if thumbnails:

                thumbnail = (
                    thumbnails[-1]
                    .get("url")
                    or ""
                ).split("?")[0]

            duration = data.get(
                "duration"
            )

            return Track(
                id=data.get("id"),
                channel_name=(
                    data.get(
                        "channel",
                        {},
                    ).get(
                        "name"
                    )
                ),
                duration=duration,
                duration_sec=utils.to_seconds(
                    duration
                ),
                title=(
                    data.get("title")
                    or "Unknown"
                )[:25],
                thumbnail=thumbnail,
                url=data.get("link"),
                user="Autoplay",
                video=video,
            )

        except Exception as e:

            logger.warning(
                f"Error fetching related videos: {e}"
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
        FAST STREAM VERSION.

        Important:
        - Does NOT wait for 1024 bytes.
        - Does NOT make an extra readiness request.
        - Starts prefetch in background.
        - Returns stream URL immediately.
        """

        if not video_id:
            return None

        video_id = str(
            video_id
        ).strip()

        # Remove full URL if accidentally passed
        if "youtube.com" in video_id or "youtu.be" in video_id:

            match = re.search(
                r"(?:v=|youtu\.be/|shorts/)"
                r"([A-Za-z0-9_-]{11})",
                video_id,
                re.IGNORECASE,
            )

            if match:
                video_id = match.group(1)

        if not re.fullmatch(
            r"[A-Za-z0-9_-]{11}",
            video_id,
        ):
            logger.warning(
                f"Invalid YouTube video ID: {video_id}"
            )
            return None

        url = (
            self.base
            + video_id
        )

        dl_type = (
            "video"
            if video
            else "audio"
        )

        # -------------------------------------------------
        # PREFETCH IN BACKGROUND
        # -------------------------------------------------

        try:

            asyncio.create_task(
                self.prefetch(
                    url,
                    video=video,
                )
            )

        except Exception as e:

            logger.warning(
                f"Unable to start prefetch: {e}"
            )

        # -------------------------------------------------
        # DIRECT API STREAM
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

            stream_url = await download_assistant(
                url,
                dl_type,
            )

        # -------------------------------------------------
        # IMPORTANT
        # -------------------------------------------------
        #
        # DO NOT do:
        #
        # async with client.get(stream_url)
        # await response.content.read(1024)
        #
        # That was causing unnecessary startup delay.
        #
        # Return the URL immediately.
        # -------------------------------------------------

        return stream_url

    # =====================================================
    # CLOSE CLIENT
    # =====================================================

    async def close(self):

        if (
            self._client
            and not self._client.closed
        ):

            try:
                await self._client.close()
            except Exception:
                pass

            self._client = None
