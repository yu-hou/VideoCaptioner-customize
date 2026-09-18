"""Download thread routing for Douyin URLs."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from videocaptioner.core.utils.douyin_client import DouyinError, DouyinMedia
from videocaptioner.ui.thread.video_download_thread import VideoDownloadThread


@dataclass
class FakeResult:
    path: str
    media: DouyinMedia


class FakeDouyinClient:
    """Stands in for the real client so routing can be asserted offline."""

    calls: list[tuple[str, str]] = []

    def __init__(self, *args, **kwargs):
        self.progress = None

    def download(self, url, work_dir, progress=None):
        FakeDouyinClient.calls.append((url, work_dir))
        if progress:
            progress(50, "下载抖音视频: 50%")
            progress(100, "抖音视频下载完成")
        media = DouyinMedia(
            title="标题",
            url="https://cdn/x.mp4",
            aweme_id="1234567890",
            thumbnail_url="https://cdn/cover.jpg",
            author="作者",
            duration=12.5,
            width=1080,
            height=1920,
            description="正文",
            raw_info={"aweme_id": "1234567890"},
        )
        return "video.mp4", media


@pytest.fixture(autouse=True)
def reset_calls():
    FakeDouyinClient.calls = []
    yield


@pytest.fixture
def client_patch(monkeypatch):
    monkeypatch.setattr(
        "videocaptioner.ui.thread.video_download_thread.DouyinClient",
        FakeDouyinClient,
    )


def test_douyin_url_uses_douyin_client(tmp_path, client_patch):
    worker = VideoDownloadThread(
        "https://www.douyin.com/video/7658521293041438003", str(tmp_path)
    )
    path, _subtitle, _thumb, info = worker.download(need_subtitle=False)

    assert path == "video.mp4"
    assert FakeDouyinClient.calls == [
        ("https://www.douyin.com/video/7658521293041438003", str(tmp_path))
    ]
    assert info["title"] == "标题"
    assert info["id"] == "1234567890"
    assert info["uploader"] == "作者"


def test_douyin_short_link_is_handled_by_client(tmp_path, client_patch):
    """短链原样交给客户端跟随跳转，URL 归一化不会破坏它。"""
    VideoDownloadThread("https://v.douyin.com/AbCdEfGhIjK/", str(tmp_path)).download(
        need_subtitle=False
    )
    assert FakeDouyinClient.calls[0][0] == "https://v.douyin.com/AbCdEfGhIjK/"


def test_douyin_failure_falls_back_to_ytdlp(tmp_path, monkeypatch):
    class Boom(FakeDouyinClient):
        def download(self, url, work_dir, progress=None):
            raise DouyinError("签名失败")

    monkeypatch.setattr(
        "videocaptioner.ui.thread.video_download_thread.DouyinClient", Boom
    )
    monkeypatch.setattr(
        VideoDownloadThread,
        "_download_with_ytdlp",
        lambda self, *args: ("yt-dlp.mp4", None, None, {"title": "fallback"}),
    )

    worker = VideoDownloadThread(
        "https://www.douyin.com/video/7658521293041438003", str(tmp_path)
    )
    path, _subtitle, _thumb, info = worker.download(need_subtitle=False)
    assert path == "yt-dlp.mp4"
    assert info["title"] == "fallback"


def test_non_douyin_url_still_uses_ytdlp(tmp_path, client_patch):
    monkeypatch_flag = {}

    def fake_ytdlp(self, *args):
        monkeypatch_flag["called"] = True
        return ("youtube.mp4", None, None, {"title": "yt"})

    worker = VideoDownloadThread("https://www.youtube.com/watch?v=dQw4w9WgXcQ", str(tmp_path))
    worker.__class__._download_with_ytdlp = fake_ytdlp
    path, _subtitle, _thumb, _info = worker.download(need_subtitle=False)

    assert path == "youtube.mp4"
    assert monkeypatch_flag["called"]
    assert FakeDouyinClient.calls == []
