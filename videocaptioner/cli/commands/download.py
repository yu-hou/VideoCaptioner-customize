"""download command — download online video."""

from argparse import Namespace
from pathlib import Path
from typing import Any

from videocaptioner.cli import exit_codes as EXIT
from videocaptioner.cli import output
from videocaptioner.core.utils.douyin_client import DouyinClient, DouyinError
from videocaptioner.core.utils.url_parser import (
    is_douyin_url,
    is_wechat_channels_url,
    normalize_video_url,
)
from videocaptioner.core.utils.wechat_channels import (
    WechatChannelsClient,
    WechatChannelsError,
)


def run(args: Namespace, config: dict) -> int:
    url = normalize_video_url(args.url)
    out_dir = getattr(args, "output", None) or "."
    quiet = getattr(args, "quiet", False)

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    progress = None if quiet else output.ProgressLine(f"Downloading {url}").start()

    try:
        if is_wechat_channels_url(url):
            client = WechatChannelsClient()
            video_path, _media = client.download(
                url,
                out_dir,
                progress=None
                if progress is None
                else lambda percent, message: progress.update(percent, message),
            )
            if progress:
                progress.finish(f"Downloaded to {video_path}")
            return EXIT.SUCCESS

        # 抖音：yt-dlp 的提取器缺平台要求的双重签名，走自研客户端
        if is_douyin_url(url):
            try:
                client = DouyinClient()
                video_path, _media = client.download(
                    url,
                    out_dir,
                    progress=None
                    if progress is None
                    else lambda percent, message: progress.update(percent, message),
                )
                if progress:
                    progress.finish(f"Downloaded to {video_path}")
                return EXIT.SUCCESS
            except DouyinError as e:
                if progress:
                    progress.update(0, f"抖音自研通道失败，尝试 yt-dlp: {e}")
                else:
                    output.hint(f"抖音自研通道失败，尝试 yt-dlp: {e}")

        try:
            import yt_dlp
        except ImportError:
            if progress:
                progress.fail("yt-dlp is not available")
            else:
                output.error("yt-dlp is not available")
            output.hint("Install the official package with: pip install videocaptioner")
            return EXIT.DEPENDENCY_MISSING

        ydl_opts: dict[str, Any] = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": f"{out_dir}/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": quiet,
            "no_warnings": quiet,
        }
        # 与 GUI 保持一致：带上已导入的 Cookie，供需要登录的站点使用
        cookiefile = Path(config.get("cookie_path", "") or "") if config else Path()
        if not cookiefile.is_file():
            from videocaptioner.config import APPDATA_PATH

            cookiefile = APPDATA_PATH / "cookies.txt"
        if cookiefile.is_file():
            ydl_opts["cookiefile"] = str(cookiefile)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
            ydl.download([url])

        if progress:
            progress.finish(f"Downloaded to {out_dir}/")
        return EXIT.SUCCESS

    except WechatChannelsError as e:
        if progress:
            progress.fail(str(e))
        else:
            output.error(str(e))
        output.hint(
            "配置腾讯元宝 Cookie：打开软件“设置 → 视频号 Cookie”，"
            "或查看文档 docs/guide/wechat-channels-download.md"
        )
        return EXIT.RUNTIME_ERROR
    except Exception as e:
        if progress:
            progress.fail(str(e))
        else:
            output.error(str(e))
        return EXIT.RUNTIME_ERROR
