"""Chrome profile discovery and Douyin cookie management."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass
from datetime import datetime
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Iterable

import yt_dlp

from videocaptioner.config import APPDATA_PATH

DOUYIN_COOKIE_PATH = APPDATA_PATH / "cookies.txt"
DOUYIN_COOKIE_DOMAINS = (
    "douyin.com",
    "iesdouyin.com",
    "bytedance.com",
    "snssdk.com",
)


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


def _iter_cookie_domains(cookie_path: Path) -> Iterable[str]:
    with cookie_path.open("r", encoding="utf-8") as cookie_file:
        for raw_line in cookie_file:
            line = raw_line.rstrip("\n")
            if line.startswith("#HttpOnly_"):
                line = line.removeprefix("#HttpOnly_")
            elif line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) >= 7:
                yield fields[0]


def get_douyin_cookie_status(
    cookie_path: Path = DOUYIN_COOKIE_PATH,
) -> DouyinCookieStatus:
    """Inspect a Netscape cookie file without returning secret values."""
    if not cookie_path.is_file():
        return DouyinCookieStatus(False, 0, None)

    try:
        count = sum(1 for domain in _iter_cookie_domains(cookie_path) if _is_douyin_domain(domain))
        updated_at = datetime.fromtimestamp(cookie_path.stat().st_mtime)
    except OSError:
        return DouyinCookieStatus(False, 0, None)
    return DouyinCookieStatus(True, count, updated_at)


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

    cookie_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = cookie_path.with_suffix(".tmp")
    filtered_cookie_jar = MozillaCookieJar(str(temporary_path))
    for cookie in source_cookie_jar:
        if _is_douyin_domain(cookie.domain):
            filtered_cookie_jar.set_cookie(cookie)

    cookie_count = len(filtered_cookie_jar)
    if cookie_count == 0:
        raise RuntimeError(
            "该 Chrome Profile 中没有找到抖音 Cookie。"
            "请先用这个 Profile 打开抖音、完成验证并确认视频可以播放。"
        )

    filtered_cookie_jar.save(ignore_discard=True, ignore_expires=True)
    os.replace(temporary_path, cookie_path)
    return cookie_count


def test_douyin_cookie(url: str, cookie_path: Path = DOUYIN_COOKIE_PATH) -> str:
    """Use yt-dlp to validate the saved cookie against a Douyin video URL."""
    from videocaptioner.ui.thread.video_download_thread import normalize_video_url

    normalized_url = normalize_video_url(url.strip())
    if not normalized_url:
        raise ValueError("请粘贴一个抖音视频链接或抖音精选链接")
    if get_douyin_cookie_status(cookie_path).cookie_count == 0:
        raise RuntimeError("尚未读取有效的抖音 Cookie")

    options = {
        "cookiefile": str(cookie_path),
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(normalized_url, download=False)
    return info.get("title") or info.get("id") or "抖音视频"
