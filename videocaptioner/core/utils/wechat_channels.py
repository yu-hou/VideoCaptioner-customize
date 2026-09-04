"""Resolve WeChat Channels share links through a local Yuanbao login cookie."""

from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, quote, urlsplit

import requests

from videocaptioner.config import APPDATA_PATH
from videocaptioner.core.utils.yuanbao_cookie import is_yuanbao_domain

YUANBAO_PARSE_URL = "https://yuanbao.tencent.com/api/weixin/get_parse_result"
CHANNELS_FEED_URL = "https://channels.weixin.qq.com/finder-preview/api/feed/get_feed_info"
DEFAULT_COOKIE_PATH = APPDATA_PATH / "cookies.txt"
DOWNLOAD_CHUNK_SIZE = 1024 * 256
REQUEST_TIMEOUT = (8, 30)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class WechatChannelsError(RuntimeError):
    """An actionable error raised by the WeChat Channels download path."""


@dataclass(frozen=True)
class WechatChannelsMedia:
    title: str
    url: str
    thumbnail_url: str = ""
    author: str = ""
    raw_info: dict[str, Any] | None = None


def sanitize_media_filename(name: str, replacement: str = "_") -> str:
    """Return a safe cross-platform filename."""
    sanitized = re.sub(r'[<>:"/\\|?*]', replacement, name)
    sanitized = re.sub(r"[\0-\31]", "", sanitized).rstrip(" .")
    return (sanitized or "视频号视频")[:200]


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


def get_yuanbao_cookie_header(cookie_path: Path = DEFAULT_COOKIE_PATH) -> str:
    """Build a Cookie header containing only cookies valid for Yuanbao."""
    if not cookie_path.is_file():
        raise WechatChannelsError(
            "尚未配置腾讯元宝 Cookie。请打开“设置 → 视频号 Cookie”，"
            "登录腾讯元宝后点击“读取 Cookie”。命令行使用同一份 AppData/cookies.txt。"
        )

    now = int(time.time())
    cookies: list[str] = []
    try:
        for fields in _iter_netscape_cookies(cookie_path):
            domain, _flag, _path, _secure, expires, name, value = fields[:7]
            if not is_yuanbao_domain(domain):
                continue
            try:
                if int(expires or 0) not in (0,) and int(expires) <= now:
                    continue
            except ValueError:
                pass
            cookies.append(f"{name}={value}")
    except (OSError, UnicodeError) as exc:
        raise WechatChannelsError(f"无法读取 cookies.txt：{exc}") from exc

    if not cookies:
        raise WechatChannelsError(
            "cookies.txt 中没有有效的腾讯元宝 Cookie。请打开“设置 → 视频号 Cookie”，"
            "登录腾讯元宝后重新读取 Cookie。"
        )
    return "; ".join(cookies)


def _plain_text(value: Any) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return " ".join(html.unescape(text).split())


class WechatChannelsClient:
    """Resolve and download a share link without a proxy or companion service."""

    def __init__(
        self,
        cookie_path: str | Path = DEFAULT_COOKIE_PATH,
        session: requests.Session | None = None,
    ) -> None:
        self.cookie_path = Path(cookie_path)
        self.session = session or requests.Session()

    def _post_json(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = None
        try:
            response = self.session.post(
                url,
                json=json,
                headers=headers,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise WechatChannelsError(f"视频号解析请求失败：{exc}") from exc
        except ValueError as exc:
            raise WechatChannelsError("视频号解析接口返回了无效数据") from exc
        finally:
            if response is not None:
                response.close()
        if not isinstance(payload, dict):
            raise WechatChannelsError("视频号解析接口返回了无效数据")
        return payload

    def _parse_share_url(self, share_url: str) -> dict[str, Any]:
        cookie = get_yuanbao_cookie_header(self.cookie_path)
        payload = self._post_json(
            YUANBAO_PARSE_URL,
            json={"type": "video_channel_url", "url": share_url, "scene": 1},
            headers={
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Cookie": cookie,
                "Origin": "https://yuanbao.tencent.com",
                "Referer": "https://yuanbao.tencent.com/",
                "User-Agent": USER_AGENT,
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        code = payload.get("code", 0)
        data = payload.get("data")
        if code != 0 or not isinstance(data, dict):
            message = _plain_text(payload.get("msg")) or "登录状态可能已失效"
            raise WechatChannelsError(
                f"腾讯元宝无法解析该链接：{message}。请重新读取元宝 Cookie 后重试。"
            )
        return data

    def _fetch_feed(self, token: str, export_id: str) -> dict[str, Any]:
        page_url = "https://channels.weixin.qq.com/finder-preview/pages/feed"
        referer = (
            f"{page_url}?entry_card_type=48&comment_scene=39&appid=0"
            f"&token={quote(token)}&entry_scene=0&eid={quote(export_id)}"
        )
        payload = self._post_json(
            CHANNELS_FEED_URL,
            json={"baseReq": {"generalToken": token}, "exportId": export_id},
            params={"_pageUrl": page_url},
            headers={
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": "https://channels.weixin.qq.com",
                "Referer": referer,
                "User-Agent": USER_AGENT,
            },
        )
        err_code = payload.get("errCode", payload.get("errcode", 0))
        data = payload.get("data")
        if err_code != 0 or not isinstance(data, dict):
            message = _plain_text(payload.get("errMsg") or payload.get("errmsg"))
            raise WechatChannelsError(
                f"视频号详情解析失败：{message or f'错误码 {err_code}'}"
            )
        error = data.get("errMsg")
        if isinstance(error, dict) and error.get("type"):
            message = _plain_text(error.get("title") or error.get("content"))
            raise WechatChannelsError(message or "该视频暂时无法播放或已失效")
        return data

    def resolve(self, share_url: str) -> WechatChannelsMedia:
        parse_data = self._parse_share_url(share_url)
        playable_url = str(parse_data.get("playable_url") or "")
        query = parse_qs(urlsplit(playable_url).query)
        token = query.get("token", [""])[0]
        export_id = query.get("eid", [""])[0] or str(
            parse_data.get("wx_export_id") or ""
        )
        if not token or not export_id:
            raise WechatChannelsError(
                "腾讯元宝返回的播放凭据不完整，请刷新元宝登录状态后重试。"
            )

        data = self._fetch_feed(token, export_id)
        feed = data.get("feedInfo")
        if not isinstance(feed, dict):
            raise WechatChannelsError("视频号详情中缺少视频信息")
        media_url = ""
        for key in ("h264VideoInfo", "h265VideoInfo"):
            info = feed.get(key)
            if isinstance(info, dict) and info.get("videoUrl"):
                media_url = str(info["videoUrl"])
                break
        media_url = media_url or str(feed.get("videoUrl") or "")
        if not media_url:
            raise WechatChannelsError("该内容没有可下载的视频流（可能是图集或已失效）")

        author_info = data.get("authorInfo")
        author = (
            str(author_info.get("nickname") or "")
            if isinstance(author_info, dict)
            else str(parse_data.get("author") or "")
        )
        return WechatChannelsMedia(
            title=str(
                feed.get("description")
                or parse_data.get("desc")
                or export_id
                or "视频号视频"
            ),
            url=media_url,
            thumbnail_url=str(feed.get("coverUrl") or parse_data.get("cover_url") or ""),
            author=author,
            raw_info=data,
        )

    def download(
        self,
        share_url: str,
        work_dir: str | Path,
        progress: Callable[[int, str], None] | None = None,
    ) -> tuple[str, WechatChannelsMedia]:
        if progress:
            progress(0, "正在通过腾讯元宝解析视频号链接...")
        media = self.resolve(share_url)
        safe_title = sanitize_media_filename(media.title)
        target_dir = Path(work_dir) / safe_title
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{safe_title}.mp4"
        partial = target.with_suffix(target.suffix + ".part")

        response = None
        try:
            response = self.session.get(
                media.url,
                headers={
                    "Referer": "https://channels.weixin.qq.com/",
                    "User-Agent": USER_AGENT,
                },
                stream=True,
                timeout=(8, 60),
            )
            response.raise_for_status()
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            with partial.open("wb") as output_file:
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if not chunk:
                        continue
                    output_file.write(chunk)
                    downloaded += len(chunk)
                    percent = min(int(downloaded * 100 / total), 99) if total else 0
                    if progress:
                        progress(percent, f"下载视频号视频: {percent}%")
            if downloaded == 0:
                raise WechatChannelsError("视频号媒体流为空")
            partial.replace(target)
        except (requests.RequestException, OSError) as exc:
            partial.unlink(missing_ok=True)
            raise WechatChannelsError(f"视频号媒体下载失败：{exc}") from exc
        except Exception:
            partial.unlink(missing_ok=True)
            raise
        finally:
            if response is not None:
                response.close()

        if progress:
            progress(100, "视频号视频下载完成")
        return str(target), media
