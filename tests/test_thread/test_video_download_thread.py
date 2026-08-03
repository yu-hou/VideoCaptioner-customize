"""Tests for video download URL normalization."""

from videocaptioner.core.utils.url_parser import normalize_video_url


def test_normalize_douyin_jingxuan_url():
    url = "https://www.douyin.com/jingxuan?modal_id=7659705531116870065"

    assert (
        normalize_video_url(url)
        == "https://www.douyin.com/video/7659705531116870065"
    )


def test_normalize_douyin_jingxuan_url_with_other_parameters():
    url = (
        "https://www.douyin.com/jingxuan?"
        "foo=bar&modal_id=7659705531116870065&from=homepage"
    )

    assert (
        normalize_video_url(url)
        == "https://www.douyin.com/video/7659705531116870065"
    )


def test_keep_standard_douyin_url_unchanged():
    url = "https://www.douyin.com/video/7659705531116870065"

    assert normalize_video_url(url) == url


def test_keep_jingxuan_url_without_valid_modal_id_unchanged():
    url = "https://www.douyin.com/jingxuan?modal_id=not-a-video-id"

    assert normalize_video_url(url) == url
