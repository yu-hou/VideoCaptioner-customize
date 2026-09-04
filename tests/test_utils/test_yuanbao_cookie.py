from http.cookiejar import Cookie, CookieJar
from pathlib import Path

from videocaptioner.core.utils.douyin_cookie import ChromeProfile
from videocaptioner.core.utils.yuanbao_cookie import (
    export_yuanbao_cookies,
    get_yuanbao_cookie_status,
)


def _cookie(domain: str, name: str, value: str = "secret") -> Cookie:
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=domain.startswith("."),
        path="/",
        path_specified=True,
        secure=True,
        expires=None,
        discard=False,
        comment=None,
        comment_url=None,
        rest={},
    )


def test_export_yuanbao_cookies_preserves_existing_douyin(tmp_path: Path, monkeypatch):
    profile_path = tmp_path / "Default"
    profile_path.mkdir()
    source_jar = CookieJar()
    source_jar.set_cookie(_cookie(".tencent.com", "yb_session"))
    source_jar.set_cookie(_cookie(".google.com", "SID"))

    class FakeYoutubeDL:
        def __init__(self, options):
            self.cookiejar = source_jar

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(
        "videocaptioner.core.utils.yuanbao_cookie.yt_dlp.YoutubeDL",
        FakeYoutubeDL,
    )
    cookie_path = tmp_path / "cookies.txt"
    cookie_path.write_text(
        "\n".join(
            [
                "# Netscape HTTP Cookie File",
                ".douyin.com\tTRUE\t/\tTRUE\t0\tsessionid\tdouyin-secret",
            ]
        ),
        encoding="utf-8",
    )

    count = export_yuanbao_cookies(
        ChromeProfile("Default", "个人", profile_path), cookie_path
    )

    saved = cookie_path.read_text(encoding="utf-8")
    assert count == 1
    assert get_yuanbao_cookie_status(cookie_path).cookie_count == 1
    assert ".douyin.com" in saved
    assert ".tencent.com" in saved
    assert ".google.com" not in saved


def test_is_yuanbao_domain_only_matches_login_hosts():
    from videocaptioner.core.utils.yuanbao_cookie import is_yuanbao_domain

    assert is_yuanbao_domain(".tencent.com")
    assert is_yuanbao_domain("yuanbao.tencent.com")
    assert is_yuanbao_domain(".yuanbao.tencent.com")
    assert not is_yuanbao_domain("cloud.tencent.com")
    assert not is_yuanbao_domain(".douyin.com")
