from __future__ import annotations

from pathlib import Path

import requests

from videocaptioner.core.utils.wechat_channels import (
    CHANNELS_FEED_URL,
    YUANBAO_PARSE_URL,
    WechatChannelsClient,
    WechatChannelsError,
    get_yuanbao_cookie_header,
)


class FakeResponse:
    def __init__(self, payload=None, chunks=None, headers=None):
        self.payload = payload
        self.chunks = chunks or []
        self.headers = headers or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload

    def iter_content(self, chunk_size):
        assert chunk_size > 0
        yield from self.chunks

    def close(self):
        return None


class FakeSession:
    def __init__(self, post_responses=(), get_responses=()):
        self.post_responses = list(post_responses)
        self.get_responses = list(get_responses)
        self.posts = []
        self.gets = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        response = self.post_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        response = self.get_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def write_cookie_file(path: Path):
    path.write_text(
        "\n".join(
            [
                "# Netscape HTTP Cookie File",
                ".tencent.com\tTRUE\t/\tTRUE\t0\tyb_session\tsecret-token",
                ".douyin.com\tTRUE\t/\tTRUE\t0\tsessionid\tdouyin-secret",
            ]
        ),
        encoding="utf-8",
    )


def parse_payload():
    return {
        "code": 0,
        "data": {
            "desc": "元宝标题",
            "cover_url": "https://example.com/parse-cover.jpg",
            "playable_url": "https://channels.weixin.qq.com/feed?token=abc&eid=export-1",
        },
    }


def feed_payload():
    return {
        "errCode": 0,
        "data": {
            "authorInfo": {"nickname": "测试作者"},
            "feedInfo": {
                "description": "农村说闲话",
                "coverUrl": "https://example.com/cover.jpg",
                "h264VideoInfo": {
                    "videoUrl": "https://finder.video.qq.com/video.mp4?token=media"
                },
            },
            "errMsg": {"type": 0},
        },
    }


def test_cookie_header_only_contains_yuanbao_domains(tmp_path):
    cookie_path = tmp_path / "cookies.txt"
    write_cookie_file(cookie_path)

    header = get_yuanbao_cookie_header(cookie_path)

    assert header == "yb_session=secret-token"
    assert "douyin-secret" not in header


def test_resolve_media_through_yuanbao(tmp_path):
    cookie_path = tmp_path / "cookies.txt"
    write_cookie_file(cookie_path)
    session = FakeSession(
        post_responses=[FakeResponse(parse_payload()), FakeResponse(feed_payload())]
    )
    client = WechatChannelsClient(cookie_path, session=session)

    media = client.resolve("https://weixin.qq.com/sph/AtBrYj8dQb")

    assert media.title == "农村说闲话"
    assert media.author == "测试作者"
    assert media.url.startswith("https://finder.video.qq.com/video.mp4")
    assert [call[0] for call in session.posts] == [YUANBAO_PARSE_URL, CHANNELS_FEED_URL]
    assert session.posts[0][1]["json"]["url"].endswith("AtBrYj8dQb")
    assert session.posts[1][1]["json"] == {
        "baseReq": {"generalToken": "abc"},
        "exportId": "export-1",
    }
    assert session.posts[0][1]["headers"]["Cookie"] == "yb_session=secret-token"
    assert "Cookie" not in session.posts[1][1]["headers"]


def test_download_direct_media_and_reports_progress(tmp_path):
    cookie_path = tmp_path / "cookies.txt"
    write_cookie_file(cookie_path)
    video_bytes = b"plain-mp4-data"
    session = FakeSession(
        post_responses=[FakeResponse(parse_payload()), FakeResponse(feed_payload())],
        get_responses=[
            FakeResponse(
                chunks=[video_bytes],
                headers={"Content-Length": str(len(video_bytes))},
            )
        ],
    )
    progress = []
    client = WechatChannelsClient(cookie_path, session=session)

    path, _media = client.download(
        "https://weixin.qq.com/sph/AtBrYj8dQb",
        tmp_path,
        progress=lambda percent, message: progress.append((percent, message)),
    )

    assert path.endswith("农村说闲话/农村说闲话.mp4")
    assert Path(path).read_bytes() == video_bytes
    assert session.gets[0][0].startswith("https://finder.video.qq.com/")
    assert "Cookie" not in session.gets[0][1]["headers"]
    assert progress[-1][0] == 100


def test_missing_cookie_has_actionable_error(tmp_path):
    client = WechatChannelsClient(tmp_path / "missing.txt", session=FakeSession())

    try:
        client.resolve("https://weixin.qq.com/sph/AtBrYj8dQb")
    except WechatChannelsError as exc:
        assert "设置 → 视频号 Cookie" in str(exc)
    else:
        raise AssertionError("expected WechatChannelsError")


def test_yuanbao_connection_error_does_not_expose_cookie(tmp_path):
    cookie_path = tmp_path / "cookies.txt"
    write_cookie_file(cookie_path)
    session = FakeSession(post_responses=[requests.ConnectionError("offline")])

    try:
        WechatChannelsClient(cookie_path, session=session).resolve(
            "https://weixin.qq.com/sph/AtBrYj8dQb"
        )
    except WechatChannelsError as exc:
        assert "offline" in str(exc)
        assert "secret-token" not in str(exc)
    else:
        raise AssertionError("expected WechatChannelsError")
