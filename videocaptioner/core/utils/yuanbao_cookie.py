"""Chrome/Yuanbao cookie management for WeChat Channels downloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yt_dlp

from videocaptioner.config import APPDATA_PATH
from videocaptioner.core.utils.browser_cookie import cookie_status, save_scoped_cookies
from videocaptioner.core.utils.douyin_cookie import ChromeProfile

YUANBAO_COOKIE_PATH = APPDATA_PATH / "cookies.txt"
YUANBAO_COOKIE_DOMAINS = ("tencent.com", "yuanbao.tencent.com")


@dataclass(frozen=True)
class YuanbaoCookieStatus:
    """Summary safe to display without exposing cookie values."""

    exists: bool
    cookie_count: int
    updated_at: datetime | None


def is_yuanbao_domain(domain: str) -> bool:
    """Match only Yuanbao login cookies, not every Tencent product subdomain."""
    domain = domain.lstrip(".").lower()
    return domain in YUANBAO_COOKIE_DOMAINS


def get_yuanbao_cookie_status(
    cookie_path: Path = YUANBAO_COOKIE_PATH,
) -> YuanbaoCookieStatus:
    exists, count, updated_at = cookie_status(cookie_path, is_yuanbao_domain)
    return YuanbaoCookieStatus(exists, count, updated_at)


def export_yuanbao_cookies(
    profile: ChromeProfile,
    cookie_path: Path = YUANBAO_COOKIE_PATH,
) -> int:
    """Save Yuanbao cookies and preserve cookies already stored for other sites."""
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
        is_yuanbao_domain,
        "腾讯元宝",
    )


def test_yuanbao_cookie(
    url: str,
    cookie_path: Path = YUANBAO_COOKIE_PATH,
) -> str:
    """Resolve metadata without downloading to validate the Yuanbao session."""
    from videocaptioner.core.utils.url_parser import is_wechat_channels_url
    from videocaptioner.core.utils.wechat_channels import WechatChannelsClient

    url = url.strip()
    if not is_wechat_channels_url(url):
        raise ValueError("请粘贴一个视频号分享链接")
    if get_yuanbao_cookie_status(cookie_path).cookie_count == 0:
        raise RuntimeError("尚未读取有效的腾讯元宝 Cookie")
    return WechatChannelsClient(cookie_path=cookie_path).resolve(url).title
