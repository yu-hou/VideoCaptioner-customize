"""Tests for safe Douyin cookie and Chrome profile helpers."""

import json
from http.cookiejar import Cookie, CookieJar
from pathlib import Path

from videocaptioner.core.utils.douyin_cookie import (
    ChromeProfile,
    export_douyin_cookies,
    get_chrome_user_data_dir,
    get_douyin_cookie_status,
    list_chrome_profiles,
)


def test_get_chrome_user_data_dir_for_macos(tmp_path: Path):
    assert get_chrome_user_data_dir(system="Darwin", home=tmp_path) == (
        tmp_path / "Library" / "Application Support" / "Google" / "Chrome"
    )


def test_get_chrome_user_data_dir_for_windows(tmp_path: Path):
    assert get_chrome_user_data_dir(
        system="Windows",
        home=tmp_path,
        local_app_data=str(tmp_path / "Local"),
    ) == (tmp_path / "Local" / "Google" / "Chrome" / "User Data")


def test_list_chrome_profiles_reads_display_names(tmp_path: Path):
    default = tmp_path / "Default"
    profile = tmp_path / "Profile 1"
    ignored = tmp_path / "System Profile"
    default.mkdir()
    profile.mkdir()
    ignored.mkdir()
    (default / "Preferences").write_text(
        json.dumps({"profile": {"name": "个人"}}),
        encoding="utf-8",
    )
    (profile / "Preferences").write_text(
        json.dumps({"profile": {"name": "工作"}}),
        encoding="utf-8",
    )

    profiles = list_chrome_profiles(tmp_path)

    assert [item.directory_name for item in profiles] == ["Default", "Profile 1"]
    assert [item.display_name for item in profiles] == ["个人", "工作"]


def test_cookie_status_counts_only_douyin_related_domains(tmp_path: Path):
    cookie_path = tmp_path / "cookies.txt"
    cookie_path.write_text(
        "\n".join(
            [
                "# Netscape HTTP Cookie File",
                ".douyin.com\tTRUE\t/\tFALSE\t0\tttwid\tsecret",
                "#HttpOnly_.douyin.com\tTRUE\t/\tTRUE\t0\tsessionid\tsecret",
                ".google.com\tTRUE\t/\tTRUE\t0\tSID\tsecret",
            ]
        ),
        encoding="utf-8",
    )

    status = get_douyin_cookie_status(cookie_path)

    assert status.exists
    assert status.cookie_count == 2
    assert status.updated_at is not None


def test_missing_cookie_file_has_empty_status(tmp_path: Path):
    status = get_douyin_cookie_status(tmp_path / "missing.txt")

    assert not status.exists
    assert status.cookie_count == 0


def _cookie(domain: str, name: str) -> Cookie:
    return Cookie(
        version=0,
        name=name,
        value="secret",
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


def test_export_saves_only_douyin_cookies(tmp_path: Path, monkeypatch):
    profile_path = tmp_path / "Profile 1"
    profile_path.mkdir()
    source_jar = CookieJar()
    source_jar.set_cookie(_cookie(".douyin.com", "sessionid"))
    source_jar.set_cookie(_cookie(".bytedance.com", "passport_csrf_token"))
    source_jar.set_cookie(_cookie(".google.com", "SID"))

    class FakeYoutubeDL:
        def __init__(self, options):
            self.cookiejar = source_jar

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(
        "videocaptioner.core.utils.douyin_cookie.yt_dlp.YoutubeDL",
        FakeYoutubeDL,
    )
    cookie_path = tmp_path / "cookies.txt"

    count = export_douyin_cookies(
        ChromeProfile("Profile 1", "工作", profile_path),
        cookie_path,
    )

    assert count == 2
    assert get_douyin_cookie_status(cookie_path).cookie_count == 2
    assert "google.com" not in cookie_path.read_text(encoding="utf-8")
