"""Resolve and download Douyin videos through the signed web API.

Why this exists
---------------
yt-dlp's Douyin extractor calls ``/aweme/v1/web/aweme/detail/`` without the two
signatures the platform now requires, so it fails even with a logged-in cookie:

    [Douyin] <id>: Fresh cookies (not necessarily logged in) are needed

Douyin sign-protects that endpoint twice over (reverse-engineered and documented
by https://github.com/Evil0ctal/Douyin_TikTok_Download_API, Apache-2.0):

* ``a_bogus``        -- from the page's ``bdms.js``; pure SM3, see ``douyin_sign``
* ``x-secsdk-web-signature`` -- ``md5(uifid_timestamp_salt_query)``, see ``douyin_sign``

Without the second one the gateway answers ``403 Blocked by ArgusSecurityPlugin
Uifid Not Found``; without the first, the payload comes back empty.

What it needs from the user
---------------------------
A visitor identity, i.e. two cookies that Chrome already has:

* ``UIFID`` (or ``UIFID_TEMP``) -- binds the request signature
* ``s_v_web_id``                 -- the browser fingerprint

``ttwid`` is minted on demand by this client and needs no login. Everything else
in cookies.txt is used if present but is not required, so a fresh Chrome profile
that has merely visited douyin.com is enough. Use 设置 → 抖音 Cookie → 读取 Cookie
to import them.
"""

from __future__ import annotations

import random
import re
import string
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

import requests

from videocaptioner.config import APPDATA_PATH
from videocaptioner.core.utils.douyin_sign import ABogus, encode_pairs, pick_uifid, sign

DEFAULT_COOKIE_PATH = APPDATA_PATH / "cookies.txt"
DETAIL_URL = "https://www.douyin.com/aweme/v1/web/aweme/detail/"
TTWID_REGISTER_URL = "https://ttwid.bytedance.com/ttwid/union/register/"
DOWNLOAD_CHUNK_SIZE = 1024 * 256
REQUEST_TIMEOUT = (8, 30)
DOWNLOAD_TIMEOUT = (8, 120)
COOKIE_DOMAIN = ".douyin.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)

# Web client identifiers. Douyin rejects requests whose version_code lags far
# behind the live web build; refresh these when it ships a major release.
AID = "6383"
CHANNEL = "channel_pc_web"
VERSION_CODE = "290100"
VERSION_NAME = "29.1.0"
UPDATE_VERSION_CODE = "170400"

PROFILE_PARAMS: tuple[tuple[str, str], ...] = (
    ("device_platform", "webapp"),
    ("aid", AID),
    ("channel", CHANNEL),
    ("pc_client_type", "1"),
    ("version_code", VERSION_CODE),
    ("version_name", VERSION_NAME),
    ("cookie_enabled", "true"),
    ("screen_width", "1920"),
    ("screen_height", "1080"),
    ("browser_language", "zh-CN"),
    ("browser_platform", "Win32"),
    ("browser_name", "Chrome"),
    ("browser_version", "130.0.0.0"),
    ("browser_online", "true"),
    ("engine_name", "Blink"),
    ("engine_version", "130.0.0.0"),
    ("os_name", "Windows"),
    ("os_version", "10"),
    ("cpu_core_num", "12"),
    ("device_memory", "8"),
    ("platform", "PC"),
    ("downlink", "10"),
    ("effective_type", "4g"),
    ("round_trip_time", "0"),
    ("update_version_code", UPDATE_VERSION_CODE),
)

_VIDEO_ID_PATTERNS = (
    re.compile(r"^/(?:video|note|slide)/(\d{6,})"),
    re.compile(r"^/share/(?:video|note|slide)/(\d{6,})"),
    re.compile(r"^/videov2/(\d{6,})"),
)

MISSING_COOKIE_HINT = (
    "尚未读取到可用的抖音 Cookie。请打开“设置 → 抖音 Cookie”，"
    "选择已访问过 douyin.com 的 Chrome 用户后点击“读取 Cookie”。"
)


class DouyinError(RuntimeError):
    """An actionable error raised by the Douyin download path."""


@dataclass(frozen=True)
class DouyinMedia:
    """Everything the download thread needs to keep behaving like yt-dlp."""

    title: str
    url: str
    aweme_id: str = ""
    thumbnail_url: str = ""
    author: str = ""
    duration: float = 0.0
    width: int = 0
    height: int = 0
    description: str = ""
    quality: str = ""
    raw_info: dict[str, Any] | None = None
    candidates: tuple[tuple[str, int, str], ...] = field(default=())


MAX_FILENAME_BYTES = 180


def sanitize_media_filename(name: str, replacement: str = "_") -> str:
    """Return a safe cross-platform filename.

    The cap is in *bytes*, not characters: most platforms cap a path component
    at 255 bytes, and a Chinese title is three bytes per character, so a
    200-character cap overflows by 3x and fails with ENAMETOOLONG.
    """
    sanitized = re.sub(r'[<>:"/\\|?*]', replacement, name)
    sanitized = re.sub(r"[\0-\31]", "", sanitized).rstrip(" .")

    encoded = sanitized.encode("utf-8")
    if len(encoded) > MAX_FILENAME_BYTES:
        truncated = encoded[:MAX_FILENAME_BYTES]
        # 避免在多字节字符中间截断
        while truncated:
            try:
                sanitized = truncated.decode("utf-8").rstrip(" .")
                break
            except UnicodeDecodeError:
                truncated = truncated[:-1]
        else:
            sanitized = ""
    return sanitized


_SHORT_LINK_PATH = re.compile(r"^/[A-Za-z0-9_-]{6,}/?$")

#: 有语义的路径段，不能被当成短链 ID
_RESERVED_PATHS = frozenset(
    {
        "video",
        "note",
        "slide",
        "share",
        "user",
        "jingxuan",
        "discover",
        "recommend",
        "explore",
        "following",
        "search",
        "searchv2",
        "live",
        "collection",
        "mix",
        "music",
        "channel",
        "hot",
        "videos",
        "download",
    }
)


def is_short_douyin_url(url: str) -> bool:
    """Whether this is a v.douyin.com short link needing a redirect hop."""
    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").lower()
    path = (parsed.path or "").rstrip("/")
    if hostname not in ("v.douyin.com", "www.douyin.com"):
        return False
    if not _SHORT_LINK_PATH.match(path or "/"):
        return False
    if (path.lstrip("/") or "").lower() in _RESERVED_PATHS:
        return False
    return True


def extract_douyin_video_id(url: str) -> str:
    """Pull the aweme id out of the URL forms Douyin hands out."""
    parsed = urlsplit(url)
    path = (parsed.path or "").rstrip("/") or "/"
    for pattern in _VIDEO_ID_PATTERNS:
        match = pattern.match(path)
        if match:
            return match.group(1)

    if re.fullmatch(r"/\d{6,}", path):
        return path.lstrip("/")

    from urllib.parse import parse_qs

    for key in ("modal_id", "aweme_id", "itemId", "item_id"):
        value = parse_qs(parsed.query).get(key, [""])[0]
        if value.isdigit():
            return value
    return ""


def _iter_netscape_cookies(cookie_path: Path):
    with cookie_path.open("r", encoding="utf-8") as cookie_file:
        for raw_line in cookie_file:
            line = raw_line.rstrip("\n")
            if line.startswith("#HttpOnly_"):
                line = line.removeprefix("#HttpOnly_")
            elif line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) >= 7:
                yield fields


class DouyinClient:
    """Talk to Douyin's web API with the two signatures it now demands."""

    def __init__(
        self,
        cookie_path: str | Path = DEFAULT_COOKIE_PATH,
        session: requests.Session | None = None,
    ) -> None:
        self.cookie_path = Path(cookie_path)
        self.session = session or requests.Session()
        self._cookies: dict[str, str] = {}
        self._ttwid_ready = False

    # ------------------------------------------------------------------
    # identity
    # ------------------------------------------------------------------
    def load_cookies(self) -> dict[str, str]:
        """Read the Douyin-scoped cookies needed to sign requests."""
        if self._cookies:
            return self._cookies
        if not self.cookie_path.is_file():
            raise DouyinError(MISSING_COOKIE_HINT)

        now = int(time.time())
        collected: dict[str, str] = {}
        try:
            for fields in _iter_netscape_cookies(self.cookie_path):
                domain, _flag, _path, _secure, expires, name, value = fields[:7]
                if "douyin" not in domain.lower() and "iesdouyin" not in domain.lower():
                    continue
                try:
                    if int(expires or 0) and int(expires) <= now:
                        continue
                except ValueError:
                    pass
                collected.setdefault(name, value)
        except (OSError, UnicodeError) as exc:
            raise DouyinError(f"无法读取 cookies.txt：{exc}") from exc

        self._cookies = collected
        if not pick_uifid(collected):
            raise DouyinError(
                MISSING_COOKIE_HINT + "（缺少 UIFID 访客标识，通常是因为尚未访问过抖音网页版）"
            )
        for name in ("UIFID", "UIFID_TEMP", "s_v_web_id", "ttwid"):
            value = collected.get(name)
            if value:
                self.session.cookies.set(name, value, domain=COOKIE_DOMAIN, path="/")
        return self._cookies

    def ensure_ttwid(self) -> None:
        """Mint a fresh ``ttwid``; it carries no login state."""
        if self._ttwid_ready:
            return
        try:
            response = self.session.post(
                TTWID_REGISTER_URL,
                json={
                    "region": "cn",
                    "aid": 6383,
                    "needFid": False,
                    "service": "www.douyin.com",
                    "migrate_info": {"ticket": "", "source": "node"},
                    "cbUrlProtocol": "https",
                    "union": True,
                },
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise DouyinError(f"注册抖音访客凭证失败：{exc}") from exc

        # The register endpoint scopes its cookie to its own host, so it has to
        # be re-planted on douyin.com -- without it the gateway refuses.
        ttwid = response.cookies.get("ttwid") or self.session.cookies.get("ttwid")
        if ttwid:
            self.session.cookies.set("ttwid", ttwid, domain=COOKIE_DOMAIN, path="/")
        self._ttwid_ready = True

    # ------------------------------------------------------------------
    # url handling
    # ------------------------------------------------------------------
    def resolve_video_id(self, url: str) -> str:
        """Return the aweme id, following short links when needed."""
        video_id = extract_douyin_video_id(url)
        if video_id:
            return video_id

        if not is_short_douyin_url(url):
            raise DouyinError(f"无法从链接中识别抖音视频 ID：{url}")

        try:
            response = self.session.get(
                url,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise DouyinError(f"解析抖音短链失败：{exc}") from exc

        resolved = extract_douyin_video_id(response.url) or extract_douyin_video_id(url)
        if not resolved:
            raise DouyinError(f"抖音短链未能解析到视频 ID：{url}")
        return resolved

    # ------------------------------------------------------------------
    # api
    # ------------------------------------------------------------------
    def _signed_detail(self, aweme_id: str) -> dict[str, Any]:
        cookies = self.load_cookies()
        self.ensure_ttwid()
        verify_fp = cookies.get("s_v_web_id", "")
        uifid = pick_uifid(cookies) or ""

        pairs: list[tuple[str, str]] = list(PROFILE_PARAMS)
        pairs.append(("aweme_id", aweme_id))
        if verify_fp:
            pairs.extend((("verifyFp", verify_fp), ("fp", verify_fp)))

        signer = ABogus(USER_AGENT)
        pairs.append(("a_bogus", signer.get_value(encode_pairs(pairs))))
        pairs.append(("msToken", self._random_ms_token()))

        query, _signature, headers = sign(pairs, uifid)
        request_headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.douyin.com/",
            "User-Agent": USER_AGENT,
            **headers,
        }

        response = None
        try:
            response = self.session.get(
                f"{DETAIL_URL}?{query}", headers=request_headers, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise DouyinError(f"抖音详情接口请求失败：{exc}") from exc
        except ValueError as exc:
            raise DouyinError("抖音详情接口返回了无效数据") from exc
        finally:
            if response is not None:
                response.close()

        if not isinstance(payload, dict):
            raise DouyinError("抖音详情接口返回了无效数据")
        status_code = payload.get("status_code", 0)
        if status_code not in (0, None) and not payload.get("aweme_detail"):
            raise DouyinError(
                f"抖音接口返回异常（status_code={status_code}）："
                f"{payload.get('status_msg') or '视频可能已被删除或无权限访问'}"
            )
        return payload

    @staticmethod
    def _random_ms_token(length: int = 116) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(random.choices(alphabet, k=length))

    @staticmethod
    def _pick_source(video: dict[str, Any]) -> tuple[str, str, tuple[tuple[str, int, str], ...]]:
        """Choose a play URL, preferring the highest-bitrate watermark-free one."""
        candidates: list[tuple[str, int, str]] = []

        for entry in video.get("bit_rate") or []:
            if not isinstance(entry, dict):
                continue
            urls = [
                url
                for url in ((entry.get("play_addr") or {}).get("url_list") or [])
                if isinstance(url, str)
            ]
            if not urls:
                continue
            bit_rate = int(entry.get("bit_rate") or 0)
            candidates.append((str(entry.get("gear_name") or ""), bit_rate, urls[0]))

        def _first(container: dict[str, Any], gear: str) -> str | None:
            urls = (container or {}).get("url_list") or []
            for url in urls:
                if isinstance(url, str) and url.startswith("http"):
                    return f"{url}"
            return None

        download_url = _first(video.get("download_addr") or {}, "download_addr")
        if download_url:
            candidates.append(("download_addr", 0, download_url))
        play_url = _first(video.get("play_addr") or {}, "play_addr")
        if play_url:
            candidates.append(("play_addr", -1, play_url))

        if not candidates:
            raise DouyinError("该抖音内容没有可下载的视频地址")
        candidates.sort(key=lambda item: item[1], reverse=True)
        best_gear, best_bitrate, best_url = candidates[0]
        return best_url, best_gear, tuple(candidates)

    def resolve(self, url: str) -> DouyinMedia:
        """Fetch the metadata for one Douyin URL."""
        aweme_id = self.resolve_video_id(url)
        payload = self._signed_detail(aweme_id)
        detail = payload.get("aweme_detail")
        if not isinstance(detail, dict) or not detail:
            raise DouyinError(
                "抖音未返回视频信息。可能是链接失效、视频已删除，"
                "或需要重新读取抖音 Cookie。"
            )

        video = detail.get("video") or {}
        if detail.get("images"):
            raise DouyinError("该抖音作品是图文内容，没有可下载的视频")

        media_url, gear, candidates = self._pick_source(video)
        title = str(detail.get("desc") or "").strip() or f"抖音视频 {aweme_id}"
        cover = detail.get("video", {}).get("origin_cover") or video.get("cover") or {}
        thumbnail = ""
        if isinstance(cover, dict):
            thumbnail = next(
                (u for u in (cover.get("url_list") or []) if isinstance(u, str)), ""
            )
        duration = float(detail.get("duration") or video.get("duration") or 0) / 1000.0

        return DouyinMedia(
            title=title,
            url=media_url,
            aweme_id=aweme_id,
            thumbnail_url=thumbnail,
            author=str((detail.get("author") or {}).get("nickname") or ""),
            duration=round(duration, 3),
            width=int(video.get("width") or 0),
            height=int(video.get("height") or 0),
            description=str(detail.get("desc") or ""),
            quality=gear,
            raw_info=detail,
            candidates=candidates,
        )

    # ------------------------------------------------------------------
    # download
    # ------------------------------------------------------------------
    def download(
        self,
        url: str,
        work_dir: str | Path,
        progress: Callable[[int, str], None] | None = None,
    ) -> tuple[str, DouyinMedia]:
        if progress:
            progress(0, "正在解析抖音视频信息...")
        media = self.resolve(url)

        safe_title = sanitize_media_filename(media.title) or f"抖音视频 {media.aweme_id}"
        target_dir = Path(work_dir) / safe_title
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{safe_title}.mp4"
        partial = target.with_suffix(target.suffix + ".part")

        attempts = list(media.candidates) or [(media.quality, 0, media.url)]
        last_error: Exception | None = None
        response = None
        downloaded = 0

        for index, (_gear, _bitrate, try_url) in enumerate(attempts[:3], start=1):
            downloaded = 0
            try:
                response = self.session.get(
                    try_url,
                    headers={"Referer": "https://www.douyin.com/", "User-Agent": USER_AGENT},
                    stream=True,
                    timeout=DOWNLOAD_TIMEOUT,
                )
                if response.status_code >= 400 and len(attempts) > 1 and index < len(attempts[:3]):
                    response.close()
                    response = None
                    continue
                response.raise_for_status()
                total = int(response.headers.get("Content-Length") or 0)
                with partial.open("wb") as output_file:
                    for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                        if not chunk:
                            continue
                        output_file.write(chunk)
                        downloaded += len(chunk)
                        percent = min(int(downloaded * 100 / total), 99) if total else 0
                        if progress:
                            progress(percent, f"下载抖音视频: {percent}%")
                if downloaded == 0:
                    raise DouyinError("抖音视频流为空")
                partial.replace(target)
                break
            except (requests.RequestException, OSError) as exc:
                last_error = exc
                partial.unlink(missing_ok=True)
                if index >= len(attempts[:3]):
                    raise DouyinError(f"抖音视频下载失败：{exc}") from exc
            except DouyinError:
                partial.unlink(missing_ok=True)
                raise
            except Exception:
                partial.unlink(missing_ok=True)
                raise
            finally:
                if response is not None:
                    response.close()
                    response = None
        else:
            if last_error is not None:
                raise DouyinError(f"抖音视频下载失败：{last_error}") from last_error
            raise DouyinError("抖音视频下载失败")

        if progress:
            progress(100, "抖音视频下载完成")
        return str(target), media
