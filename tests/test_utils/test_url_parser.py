"""Tests for multi-URL extraction used by batch download."""

from videocaptioner.core.utils.url_parser import (
    extract_urls,
    is_wechat_channels_url,
    normalize_video_url,
)


def test_extract_urls_from_newlines():
    text = """
    https://www.bilibili.com/video/BV1YPgh6TEWH/
    https://www.youtube.com/watch?v=dQw4w9WgXcQ
    """
    urls = extract_urls(text)
    assert len(urls) == 2
    assert urls[0].startswith("https://www.bilibili.com/")
    assert "youtube.com" in urls[1]


def test_extract_urls_from_comma_and_semicolon():
    text = (
        "https://example.com/a，https://example.com/b; "
        "https://example.com/c"
    )
    urls = extract_urls(text)
    assert urls == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
    ]


def test_extract_urls_dedupes_and_keeps_order():
    text = "https://example.com/a https://example.com/b https://example.com/a"
    assert extract_urls(text) == [
        "https://example.com/a",
        "https://example.com/b",
    ]


def test_extract_urls_from_share_text_and_normalize_douyin():
    text = (
        "复制此消息打开视频 "
        "https://www.douyin.com/jingxuan?modal_id=7659705531116870065 ，"
        "再看这个 https://www.bilibili.com/video/BV1xxx"
    )
    urls = extract_urls(text)
    assert urls[0] == "https://www.douyin.com/video/7659705531116870065"
    assert "bilibili.com" in urls[1]


def test_normalize_video_url_passthrough():
    url = "https://www.youtube.com/watch?v=abc"
    assert normalize_video_url(url) == url


def test_detect_wechat_channels_share_urls():
    assert is_wechat_channels_url("https://weixin.qq.com/sph/AtBrYj8dQb")
    assert is_wechat_channels_url(
        "https://channels.weixin.qq.com/finder-preview/pages/sph?id=AtBrYj8dQb"
    )
    assert is_wechat_channels_url(
        "https://channels.weixin.qq.com/web/pages/feed?eid=export-1"
    )
    assert not is_wechat_channels_url("https://weixin.qq.com/")
    assert not is_wechat_channels_url("https://example.com/sph/AtBrYj8dQb")


def test_extract_urls_from_wechat_channels_share_text():
    text = (
        "发现一个视频，一起来看 "
        "https://weixin.qq.com/sph/AtBrYj8dQb ，"
        "再看这个 https://www.bilibili.com/video/BV1xxx"
    )
    urls = extract_urls(text)
    assert urls[0] == "https://weixin.qq.com/sph/AtBrYj8dQb"
    assert "bilibili.com" in urls[1]
