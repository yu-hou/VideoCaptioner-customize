"""download command — download online video."""

from argparse import Namespace
from pathlib import Path
from typing import Any

from videocaptioner.cli import exit_codes as EXIT
from videocaptioner.cli import output
from videocaptioner.core.utils.url_parser import is_wechat_channels_url
from videocaptioner.core.utils.wechat_channels import (
    WechatChannelsClient,
    WechatChannelsError,
)


def run(args: Namespace, config: dict) -> int:
    url = args.url
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
