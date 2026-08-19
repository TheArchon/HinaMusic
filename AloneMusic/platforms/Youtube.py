#
# Copyright (C) 2025-present by TheAloneTeam@Github.
#
# This file is part of AloneMusic project,
# and is released under the MIT License.
#

import asyncio
import os
import random
import re
import time
import urllib.parse
from typing import Optional
import yt_dlp
import aiohttp
from py_yt import VideosSearch

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

REQUEST_TIMEOUT = int(
    os.getenv("YOUTUBE_REQUEST_TIMEOUT", "60")
)

PREFETCH_COOLDOWN = int(
    os.getenv("YOUTUBE_PREFETCH_COOLDOWN", "15")
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

    ext = (
        "mp3"
        if dl_type == "audio"
        else "mp4"
    )

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

        # -------------------------------------------------
        # YouTube URL regex
        # -------------------------------------------------

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
    # COOKIES
    # =====================================================

    def get_cookies(self):

        if not self.checked:

            self.cookies.clear()

            try:

                if os.path.isdir(
                    self.cookie_dir
                ):

                    for file in os.listdir(
                        self.cookie_dir
                    ):

                        if file.endswith(
                            ".txt"
                        ):

                            self.cookies.append(
                                os.path.join(
                                    self.cookie_dir,
                                    file,
                                )
                            )

            except Exception as e:

                logger.warning(
                    f"Cookie directory error: {e}"
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

        logger.info(
            "Saving YouTube cookies..."
        )

        os.makedirs(
            self.cookie_dir,
            exist_ok=True,
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

                    link = (
                        "https://batbin.me/raw/"
                        + name
                    )

                    async with session.get(
                        link
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
    # VALIDATE
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

                        data = results[0]

                        thumbnails = (
                            data.get(
                                "thumbnails"
                            )
                            or []
                        )

                        thumbnail = ""

                        if thumbnails:

                            thumbnail = (
                                thumbnails[-1]
                                .get("url")
                                or ""
                            ).split("?")[0]

                        duration = (
                            data.get("duration")
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
                            duration_sec=(
                                utils.to_seconds(
                                    duration
                                )
                            ),
                            message_id=m_id,
                            title=(
                                data.get("title")
                                or "Unknown"
                            )[:25],
                            thumbnail=thumbnail,
                            url=data.get("link"),
                            view_count=(
                                data.get(
                                    "viewCount",
                                    {},
                                ).get(
                                    "short"
                                )
                            ),
                            video=video,
                        )

        except Exception as e:

            logger.warning(
                f"YouTube API search failed: {e}"
            )

        # -------------------------------------------------
        # PY_YT FALLBACK
        # -------------------------------------------------

        try:

            search = VideosSearch(
                query,
                limit=1,
                with_live=False,
            )

            results = await search.next()

            if (
                results
                and results.get("result")
            ):

                data = results[
                    "result"
                ][0]

                thumbnails = (
                    data.get(
                        "thumbnails"
                    )
                    or []
                )

                thumbnail = ""

                if thumbnails:

                    thumbnail = (
                        thumbnails[-1]
                        .get("url")
                        or ""
                    ).split("?")[0]

                duration = (
                    data.get("duration")
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
                    duration_sec=(
                        utils.to_seconds(
                            duration
                        )
                    ),
                    message_id=m_id,
                    title=(
                        data.get("title")
                        or "Unknown"
                    )[:25],
                    thumbnail=thumbnail,
                    url=data.get("link"),
                    view_count=(
                        data.get(
                            "viewCount",
                            {},
                        ).get(
                            "short"
                        )
                    ),
                    video=video,
                )

        except Exception as e:

            logger.warning(
                f"py_yt search failed: {e}"
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

                    data = await response.json(
                        content_type=None
                    )

                    videos = (
                        data.get("videos")
                        or []
                    )

                    if videos:

                        tracks = []

                        for item in videos[:limit]:

                            thumbnails = (
                                item.get(
                                    "thumbnails"
                                )
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

                            duration = (
                                item.get(
                                    "duration"
                                )
                            )

                            tracks.append(
                                Track(
                                    id=item.get(
                                        "id"
                                    ),
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
        # PY_YT FALLBACK
        # -------------------------------------------------

        tracks = []

        try:

            playlist = await Playlist.get(
                url
            )

            videos = (
                playlist.get("videos")
                or []
            )

            for item in videos[:limit]:

                thumbnails = (
                    item.get(
                        "thumbnails"
                    )
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

                duration = (
                    item.get("duration")
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

        except Exception as e:

            logger.warning(
                f"py_yt playlist failed: {e}"
            )

        return tracks

    # =====================================================
    # GET VIDEO ID
    # =====================================================

    def _get_video_id(
        self,
        link: str,
    ) -> Optional[str]:

        if not link:
            return None

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
            and now - previous
            < PREFETCH_COOLDOWN
        ):
            return True

        self._recent_prefetches[
            cache_key
        ] = now

        # Keep cache small
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
                        f"Prefetch HTTP "
                        f"{response.status}"
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

        """
        Recommendations is NOT imported because
        current py_yt versions may not provide it.

        Instead we use YouTube search as an autoplay
        fallback.
        """

        try:

            if not video_id:
                return None

            # Search using video ID first
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

            # Remove original video
            candidates = [
                item
                for item in results
                if item.get("id")
                and item.get("id")
                != video_id
            ]

            if max_duration:

                candidates = [
                    item
                    for item in candidates
                    if utils.to_seconds(
                        item.get(
                            "duration"
                        )
                        or "00:00"
                    )
                    <= max_duration
                ]

            if not candidates:
                return None

            data = random.choice(
                candidates
            )

            thumbnails = (
                data.get(
                    "thumbnails"
                )
                or []
            )

            thumbnail = ""

            if thumbnails:

                thumbnail = (
                    thumbnails[-1]
                    .get("url")
                    or ""
                ).split("?")[0]

            duration = (
                data.get("duration")
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
                duration_sec=(
                    utils.to_seconds(
                        duration
                    )
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
                f"Autoplay search failed: {e}"
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
        FAST START DOWNLOAD.

        No stream readiness request.
        No 1024-byte wait.
        URL returned immediately.
        """

        if not video_id:
            return None

        video_id = str(
            video_id
        ).strip()

        # -------------------------------------------------
        # Extract ID from URL if needed
        # -------------------------------------------------

        extracted = self._get_video_id(
            video_id
        )

        if extracted:
            video_id = extracted

        # -------------------------------------------------
        # Validate ID
        # -------------------------------------------------

        if not re.fullmatch(
            r"[A-Za-z0-9_-]{11}",
            video_id,
        ):
            logger.warning(
                f"Invalid YouTube ID: "
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
                f"Prefetch task error: {e}"
            )

        # -------------------------------------------------
        # DIRECT STREAM URL
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
        # IMPORTANT:
        #
        # DO NOT make another GET request here.
        # DO NOT read 1024 bytes here.
        #
        # Returning immediately makes playback
        # start faster.
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

            except Exception:
                pass

            self._client = None
