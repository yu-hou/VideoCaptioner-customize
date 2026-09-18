"""Chrome profile discovery and Douyin cookie management."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yt_dlp

from videocaptioner.config import APPDATA_PATH
from videocaptioner.core.utils.browser_cookie import cookie_status, save_scoped_cookies

DOUYIN_COOKIE_PATH = APPDATA_PATH / "cookies.txt"
DOUYIN_COOKIE_DOMAINS = (
    "douyin.com",
    "iesdouyin.com",
    "bytedance.com",
    "snssdk.com",
)

#: 下载抖音视频真正依赖的 Cookie：访客标识 + 浏览器指纹。
#: 两者都是 Chrome 访问过 douyin.com 就会产生，不需要登录。
VISITOR_ID_COOKIES = ("UIFID", "UIFID_TEMP")
FINGERPRINT_COOKIES = ("s_v_web_id",)


@dataclass(frozen=True)
class ChromeProfile:
    """A Chrome profile available on the current computer."""

    directory_name: str
    display_name: str
    path: Path


@dataclass(frozen=True)
class DouyinCookieStatus:
    """Summary safe to display without exposing cookie values."""

    exists: bool
    cookie_count: int
    updated_at: datetime | None


def get_chrome_user_data_dir(
    system: str | None = None,
    home: Path | None = None,
    local_app_data: str | None = None,
) -> Path | None:
    """Return Chrome's user-data directory for a supported desktop platform."""
    system = system or platform.system()
    home = home or Path.home()

    if system == "Darwin":
        return home / "Library" / "Application Support" / "Google" / "Chrome"
    if system == "Windows":
        base = local_app_data or os.environ.get("LOCALAPPDATA")
        return Path(base) / "Google" / "Chrome" / "User Data" if base else None
    if system == "Linux":
        return home / ".config" / "google-chrome"
    return None


def _profile_display_name(profile_path: Path) -> str:
    preferences_path = profile_path / "Preferences"
    try:
        preferences = json.loads(preferences_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return profile_path.name

    profile_name = preferences.get("profile", {}).get("name")
    if isinstance(profile_name, str) and profile_name.strip():
        return profile_name.strip()

    account_info = preferences.get("account_info", [])
    if account_info and isinstance(account_info[0], dict):
        account_name = account_info[0].get("full_name") or account_info[0].get("email")
        if isinstance(account_name, str) and account_name.strip():
            return account_name.strip()
    return profile_path.name


def list_chrome_profiles(user_data_dir: Path | None = None) -> list[ChromeProfile]:
    """Discover regular Chrome profiles, ordered with Default first."""
    root = user_data_dir or get_chrome_user_data_dir()
    if root is None or not root.is_dir():
        return []

    candidates = [
        path
        for path in root.iterdir()
        if path.is_dir() and (path.name == "Default" or path.name.startswith("Profile "))
    ]
    candidates.sort(key=lambda path: (path.name != "Default", path.name.lower()))
    return [
        ChromeProfile(
            directory_name=path.name,
            display_name=_profile_display_name(path),
            path=path,
        )
        for path in candidates
    ]


def _is_douyin_domain(domain: str) -> bool:
    domain = domain.lstrip(".").lower()
    return any(domain == suffix or domain.endswith(f".{suffix}") for suffix in DOUYIN_COOKIE_DOMAINS)


def get_douyin_cookie_status(
    cookie_path: Path = DOUYIN_COOKIE_PATH,
) -> DouyinCookieStatus:
    """Inspect a Netscape cookie file without returning secret values."""
    exists, count, updated_at = cookie_status(cookie_path, _is_douyin_domain)
    return DouyinCookieStatus(exists, count, updated_at)


def missing_essential_cookies(cookie_path: Path = DOUYIN_COOKIE_PATH) -> list[str]:
    """Return the essential cookie names absent from the saved cookie file."""
    if not cookie_path.is_file():
        return list(VISITOR_ID_COOKIES + FINGERPRINT_COOKIES)

    present: set[str] = set()
    try:
        with cookie_path.open("r", encoding="utf-8") as cookie_file:
            for raw_line in cookie_file:
                line = raw_line.rstrip("\n")
                if line.startswith("#HttpOnly_"):
                    line = line.removeprefix("#HttpOnly_")
                elif line.startswith("#"):
                    continue
                fields = line.split("\t")
                if len(fields) >= 7 and _is_douyin_domain(fields[0]):
                    present.add(fields[5])
    except (OSError, UnicodeError):
        return list(VISITOR_ID_COOKIES + FINGERPRINT_COOKIES)

    missing: list[str] = []
    if not present.intersection(VISITOR_ID_COOKIES):
        missing.append("UIFID")
    if not present.intersection(FINGERPRINT_COOKIES):
        missing.append("s_v_web_id")
    return missing


def export_douyin_cookies(
    profile: ChromeProfile,
    cookie_path: Path = DOUYIN_COOKIE_PATH,
) -> int:
    """Read Chrome cookies and save only Douyin-related entries."""
    if not profile.path.is_dir():
        raise FileNotFoundError(f"Chrome Profile 不存在：{profile.path}")

    options = {
        "cookiesfrombrowser": ("chrome", str(profile.path), None, None),
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        source_cookie_jar = ydl.cookiejar

    return save_scoped_cookies(
        source_cookie_jar,
        cookie_path,
        _is_douyin_domain,
        "抖音",
    )


def test_douyin_cookie(url: str, cookie_path: Path = DOUYIN_COOKIE_PATH) -> str:
    """Validate the saved cookie against a Douyin video URL.

    Uses our own signed client rather than yt-dlp: yt-dlp's Douyin extractor is
    currently broken independently of whether the cookies are good, so it would
    report failure for a setup that downloads perfectly well.
    """
    from videocaptioner.core.utils.douyin_client import DouyinClient
    from videocaptioner.core.utils.url_parser import normalize_video_url

    normalized_url = normalize_video_url(url.strip())
    if not normalized_url:
        raise ValueError("请粘贴一个抖音视频链接或抖音精选链接")
    if get_douyin_cookie_status(cookie_path).cookie_count == 0:
        raise RuntimeError("尚未读取有效的抖音 Cookie")

    media = DouyinClient(cookie_path).resolve(normalized_url)
    return media.title
