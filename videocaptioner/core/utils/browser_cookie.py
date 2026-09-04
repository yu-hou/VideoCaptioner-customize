"""Shared helpers for safely merging site-scoped browser cookies."""

from __future__ import annotations

import os
from datetime import datetime
from http.cookiejar import CookieJar, LoadError, MozillaCookieJar
from pathlib import Path
from typing import Callable, Iterable


def iter_cookie_domains(cookie_path: Path) -> Iterable[str]:
    with cookie_path.open("r", encoding="utf-8") as cookie_file:
        for raw_line in cookie_file:
            line = raw_line.rstrip("\n")
            if line.startswith("#HttpOnly_"):
                line = line.removeprefix("#HttpOnly_")
            elif line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) >= 7:
                yield fields[0]


def cookie_status(
    cookie_path: Path,
    domain_matches: Callable[[str], bool],
) -> tuple[bool, int, datetime | None]:
    if not cookie_path.is_file():
        return False, 0, None
    try:
        count = sum(1 for domain in iter_cookie_domains(cookie_path) if domain_matches(domain))
        updated_at = datetime.fromtimestamp(cookie_path.stat().st_mtime)
    except (OSError, UnicodeError):
        return False, 0, None
    return True, count, updated_at


def save_scoped_cookies(
    source_cookie_jar: CookieJar,
    cookie_path: Path,
    domain_matches: Callable[[str], bool],
    site_name: str,
) -> int:
    """Replace one site's cookies while preserving every other saved site."""
    selected = [cookie for cookie in source_cookie_jar if domain_matches(cookie.domain)]
    if not selected:
        raise RuntimeError(
            f"该 Chrome Profile 中没有找到{site_name} Cookie。"
            f"请先用这个 Profile 打开{site_name}、完成登录并确认页面可正常访问。"
        )

    merged = MozillaCookieJar()
    if cookie_path.is_file():
        existing = MozillaCookieJar(str(cookie_path))
        try:
            existing.load(ignore_discard=True, ignore_expires=True)
        except (OSError, LoadError) as exc:
            raise RuntimeError(f"现有 cookies.txt 无法读取：{exc}") from exc
        for cookie in existing:
            if not domain_matches(cookie.domain):
                merged.set_cookie(cookie)
    for cookie in selected:
        merged.set_cookie(cookie)

    cookie_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = cookie_path.with_suffix(".tmp")
    merged.filename = str(temporary_path)
    merged.save(ignore_discard=True, ignore_expires=True)
    os.replace(temporary_path, cookie_path)
    return len(selected)
