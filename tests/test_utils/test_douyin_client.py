"""Tests for the signed Douyin download client."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import requests
from requests.cookies import RequestsCookieJar

from videocaptioner.core.utils.douyin_client import (
    DETAIL_URL,
    DouyinClient,
    DouyinError,
    DouyinMedia,
    extract_douyin_video_id,
    is_short_douyin_url,
    sanitize_media_filename,
)
from videocaptioner.core.utils.douyin_sign import ABogus, encode_pairs, pick_uifid, sign


class FakeResponse:
    def __init__(
        self, payload=None, chunks=None, headers=None, url="", cookies=None, status_code=200
    ):
        self.payload = payload
        self.chunks = chunks or []
        self.headers = headers or {}
        self.url = url
        self.cookies = cookies or RequestsCookieJar()
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")
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
        self.posts: list[tuple] = []
        self.gets: list[tuple] = []
        self.cookies = RequestsCookieJar()

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


def write_cookie_file(path: Path, *, include_uifid: bool = True) -> None:
    lines = ["# Netscape HTTP Cookie File"]
    if include_uifid:
        lines.append(
            "\t".join(
                [
                    ".douyin.com",
                    "TRUE",
                    "/",
                    "FALSE",
                    "2147483647",
                    "UIFID",
                    "ad6934b0ab4e32090218",
                ]
            )
        )
    lines.append(
        "\t".join(
            [
                ".douyin.com",
                "TRUE",
                "/",
                "FALSE",
                "2147483647",
                "s_v_web_id",
                "verify_ms4jvizi_abcdefg",
            ]
        )
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def cookie_path(tmp_path: Path) -> Path:
    target = tmp_path / "cookies.txt"
    write_cookie_file(target)
    return target


def detail_response(**overrides) -> dict:
    payload = {
        "status_code": 0,
        "aweme_detail": {
            "aweme_id": "7658521293041438003",
            "desc": "测试标题",
            "duration": 12500,
            "author": {"nickname": "测试作者"},
            "video": {
                "width": 1080,
                "height": 1920,
                "duration": 12500,
                "origin_cover": {"url_list": ["https://c.douyin/cover.jpg"]},
                "play_addr": {"url_list": ["https://cdn.douyin/play.mp4"]},
                "download_addr": {"url_list": ["https://cdn.douyin/download.mp4"]},
                "bit_rate": [
                    {
                        "gear_name": "normal_1080_0",
                        "bit_rate": 711716,
                        "play_addr": {"url_list": ["https://cdn.douyin/1080.mp4"]},
                    },
                    {
                        "gear_name": "normal_720_0",
                        "bit_rate": 589768,
                        "play_addr": {"url_list": ["https://cdn.douyin/720.mp4"]},
                    },
                ],
            },
        },
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# URL handling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://www.douyin.com/video/7658521293041438003",
        "https://www.douyin.com/note/7658521293041438003",
        "https://www.iesdouyin.com/share/video/7658521293041438003",
        "https://www.douyin.com/jingxuan?modal_id=7658521293041438003",
        "https://www.douyin.com/discover?modal_id=7658521293041438003",
    ],
)
def test_extract_video_id_from_supported_urls(url):
    assert extract_douyin_video_id(url) == "7658521293041438003"


def test_extract_video_id_returns_empty_for_unknown_path():
    assert extract_douyin_video_id("https://www.douyin.com/user/MS4wLjABAAAA") == ""


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://v.douyin.com/AbCdEfGhIjK/", True),
        ("https://www.douyin.com/video/7658521293041438003", False),
        ("https://www.douyin.com/jingxuan?modal_id=7658521293041438003", False),
    ],
)
def test_is_short_douyin_url(url, expected):
    assert is_short_douyin_url(url) is expected


def test_resolve_video_id_follows_short_link(cookie_path):
    session = FakeSession(
        get_responses=[FakeResponse(url="https://www.douyin.com/video/7658521293041438003")]
    )
    client = DouyinClient(cookie_path, session=session)
    assert client.resolve_video_id("https://v.douyin.com/AbCdEfGhIjK/") == (
        "7658521293041438003"
    )


def test_unrecognized_douyin_url_raises(cookie_path):
    client = DouyinClient(cookie_path, session=FakeSession())
    with pytest.raises(DouyinError):
        client.resolve_video_id("https://www.douyin.com/user/MS4wLjABAAAA")


# ---------------------------------------------------------------------------
# Cookie requirements
# ---------------------------------------------------------------------------


def test_missing_cookie_file_has_actionable_error(tmp_path):
    client = DouyinClient(tmp_path / "nope.txt", session=FakeSession())
    with pytest.raises(DouyinError) as excinfo:
        client.resolve("https://www.douyin.com/video/7658521293041438003")
    assert "抖音 Cookie" in str(excinfo.value)


def test_cookie_without_uifid_is_rejected(tmp_path):
    target = tmp_path / "cookies.txt"
    write_cookie_file(target, include_uifid=False)
    client = DouyinClient(target, session=FakeSession())
    with pytest.raises(DouyinError) as excinfo:
        client.resolve("https://www.douyin.com/video/7658521293041438003")
    assert "UIFID" in str(excinfo.value)


def test_expired_cookie_is_ignored(tmp_path):
    target = tmp_path / "cookies.txt"
    target.write_text(
        "\t".join([".douyin.com", "TRUE", "/", "FALSE", "100", "UIFID", "expired"])
        + "\n",
        encoding="utf-8",
    )
    client = DouyinClient(target, session=FakeSession())
    with pytest.raises(DouyinError):
        client.resolve("https://www.douyin.com/video/7658521293041438003")


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------


def test_resolve_sends_both_signatures(cookie_path):
    detail = detail_response()
    session = FakeSession(
        post_responses=[FakeResponse()], get_responses=[FakeResponse(detail)]
    )
    client = DouyinClient(cookie_path, session=session)
    media = client.resolve("https://www.douyin.com/video/7658521293041438003")

    detail_url, kwargs = session.gets[-1]
    assert detail_url.startswith(DETAIL_URL)
    headers = kwargs["headers"]
    assert headers["x-secsdk-web-signature"]
    assert headers["x-secsdk-web-expire"]
    assert headers["uifid"]
    query = detail_url.split("?", 1)[1]
    assert "a_bogus=" in query
    assert "msToken=" in query
    # 选清晰度最高的无水印源
    assert media.quality == "normal_1080_0"
    assert media.url.endswith("1080.mp4")
    return media


def test_resolve_metadata_mapping(cookie_path):
    session = FakeSession(
        post_responses=[FakeResponse()], get_responses=[FakeResponse(detail_response())]
    )
    media = DouyinClient(cookie_path, session=session).resolve(
        "https://www.douyin.com/video/7658521293041438003"
    )
    assert isinstance(media, DouyinMedia)
    assert media.title == "测试标题"
    assert media.author == "测试作者"
    assert media.aweme_id == "7658521293041438003"
    assert media.duration == 12.5
    assert media.thumbnail_url == "https://c.douyin/cover.jpg"
    assert (media.width, media.height) == (1080, 1920)


def test_image_post_is_rejected(cookie_path):
    payload = detail_response()
    payload["aweme_detail"]["images"] = [{"url_list": ["https://cdn/a.jpg"]}]
    session = FakeSession(
        post_responses=[FakeResponse()], get_responses=[FakeResponse(payload)]
    )
    with pytest.raises(DouyinError) as excinfo:
        DouyinClient(cookie_path, session=session).resolve(
            "https://www.douyin.com/video/7658521293041438003"
        )
    assert "图文" in str(excinfo.value)


def test_empty_detail_is_reported_clearly(cookie_path):
    session = FakeSession(
        post_responses=[FakeResponse()],
        get_responses=[FakeResponse({"status_code": 0, "aweme_detail": {}})],
    )
    with pytest.raises(DouyinError) as excinfo:
        DouyinClient(cookie_path, session=session).resolve(
            "https://www.douyin.com/video/7658521293041438003"
        )
    assert "Cookie" in str(excinfo.value) or "失效" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def test_download_writes_mp4_and_reports_progress(cookie_path, tmp_path):
    session = FakeSession(
        post_responses=[FakeResponse()],
        get_responses=[
            FakeResponse(detail_response()),
            FakeResponse(
                chunks=[b"abc", b"def"], headers={"Content-Length": "6"}
            ),
        ],
    )
    client = DouyinClient(cookie_path, session=session)
    progress: list[int] = []
    target, media = client.download(
        "https://www.douyin.com/video/7658521293041438003",
        tmp_path,
        progress=lambda percent, message: progress.append(percent),
    )
    assert Path(target).read_bytes() == b"abcdef"
    assert target.endswith(".mp4")
    assert progress[-1] == 100


def test_download_falls_back_to_next_candidate(cookie_path, tmp_path):
    session = FakeSession(
        post_responses=[FakeResponse()],
        get_responses=[
            FakeResponse(detail_response()),
            FakeResponse(chunks=[b"x"], headers={"Content-Length": "1"}),
        ],
    )
    client = DouyinClient(cookie_path, session=session)
    target, _ = client.download(
        "https://www.douyin.com/video/7658521293041438003", tmp_path
    )
    assert Path(target).exists()


def test_download_cleans_up_partial_file(cookie_path, tmp_path):
    session = FakeSession(
        post_responses=[FakeResponse()],
        get_responses=[
            FakeResponse(detail_response()),
            requests.RequestException("boom"),
            requests.RequestException("boom"),
            requests.RequestException("boom"),
        ],
    )
    client = DouyinClient(cookie_path, session=session)
    with pytest.raises(DouyinError):
        client.download("https://www.douyin.com/video/7658521293041438003", tmp_path)
    assert not list(tmp_path.glob("**/*.part"))


# ---------------------------------------------------------------------------
# Filenames
# ---------------------------------------------------------------------------


def test_filename_is_capped_by_bytes():
    long_chinese_title = "标题" * 200
    safe = sanitize_media_filename(long_chinese_title)
    assert len(safe.encode("utf-8")) <= 180
    assert safe


def test_filename_strips_forbidden_characters():
    assert sanitize_media_filename('a/b:c*d?e"f') == "a_b_c_d_e_f"


# ---------------------------------------------------------------------------
# Signature primitives
# ---------------------------------------------------------------------------


def test_pick_uifid_recognises_spellings():
    assert pick_uifid({"UIFID": "a"}) == "a"
    assert pick_uifid({"uifid_temp": "b"}) == "b"
    assert pick_uifid({}) is None


def test_websign_matches_md5_recipe():
    pairs = [("aweme_id", "123"), ("aid", "6383")]
    uifid, timestamp = "abc123", 1700000000
    _query, signature, headers = sign(pairs, uifid, timestamp=timestamp)
    covered = encode_pairs(
        [("aweme_id", "123"), ("aid", "6383"), ("uifid", uifid), ("timestamp", str(timestamp))]
    )
    salt = "A96D855A08C0A9707F8BEF0D9A527E4E"
    expected = hashlib.md5(f"{uifid}_{timestamp}_{salt}_{covered}".encode()).hexdigest()
    assert signature == expected
    assert headers["uifid"] == uifid


def test_abogus_produces_decodable_value():
    from videocaptioner.core.utils.douyin_sign.abogus import structure_error

    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )
    value = ABogus(ua).get_value(encode_pairs([("a", "1")]))
    assert value
    # 结构自检：能解出头部与版本块才算合法 a_bogus
    assert structure_error(value) is None


def test_abogus_query_is_percent_encoded_once():
    pairs = [("q", "中文 空格"), ("aweme_id", "123")]
    query = encode_pairs(pairs)
    assert "q=%E4%B8%AD%E6%96%87%20%E7%A9%BA%E6%A0%BC" in query
    assert ABogus("Chrome/130.0.0.0").get_value(query)
