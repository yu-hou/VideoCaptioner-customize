"""从粘贴文本中提取并规范化视频 URL。"""

from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import parse_qs, urlparse, urlsplit

# 兼容换行/空格/中英文标点分隔，以及分享文案中的链接
URL_PATTERN = re.compile(r"https?://[^\s<>\"'，。；：！？、）】》\]|,;]+")

_TRAILING_PUNCT = ".,;:!?)]}，。；：！？、）】》"

#: 抖音信息流页面路径，这些页面用 modal_id 指向单个作品
DOUYIN_FEED_PATHS = frozenset(
    {"/", "/jingxuan", "/discover", "/recommend", "/explore", "/following"}
)


def _is_douyin_host(parsed_url) -> bool:
    hostname = (parsed_url.hostname or "").lower()
    return (
        hostname == "douyin.com"
        or hostname.endswith(".douyin.com")
        or hostname == "iesdouyin.com"
        or hostname.endswith(".iesdouyin.com")
    )


def is_wechat_channels_url(url: str) -> bool:
    """是否为微信视频号分享/预览链接。"""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False

    hostname = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/")
    if hostname == "weixin.qq.com":
        return path.startswith("/sph/")
    if hostname == "channels.weixin.qq.com":
        return path.startswith("/finder-preview/") or path.startswith("/web/pages/feed")
    return False


def is_douyin_url(url: str) -> bool:
    """是否为抖音作品链接（含短链、精选链接、分享页）。"""
    try:
        return _is_douyin_host(urlsplit(url))
    except ValueError:
        return False


def normalize_video_url(url: str) -> str:
    """将已知的视频分享页链接转换为 yt-dlp 支持的标准链接。"""
    try:
        parsed_url = urlsplit(url)
    except ValueError:
        return url

    if not _is_douyin_host(parsed_url):
        return url

    # 精选 / 推荐等信息流页面通过 modal_id 指向单个作品
    if (parsed_url.path.rstrip("/") or "/") not in DOUYIN_FEED_PATHS:
        return url

    modal_id = parse_qs(parsed_url.query).get("modal_id", [""])[0]
    if not modal_id.isdigit():
        return url

    return f"https://www.douyin.com/video/{modal_id}"


def clean_url_candidate(raw: str) -> str:
    """去掉首尾空白与常见尾随标点。"""
    return raw.strip().rstrip(_TRAILING_PUNCT)


def is_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def extract_urls(text: str) -> list[str]:
    """
    从任意粘贴文本中提取 http(s) 链接，规范化并去重（保序）。

    支持换行、空格、逗号/分号等分隔，也能从分享文案中抠出多条 URL。
    """
    if not text or not text.strip():
        return []

    found: list[str] = []
    seen: set[str] = set()
    for match in URL_PATTERN.findall(text):
        url = clean_url_candidate(match)
        if not is_http_url(url):
            continue
        url = normalize_video_url(url)
        if url in seen:
            continue
        seen.add(url)
        found.append(url)
    return found


def extract_urls_from_lines(lines: Iterable[str]) -> list[str]:
    """按行拼接后再提取（便于测试与调用方传入行列表）。"""
    return extract_urls("\n".join(lines))
