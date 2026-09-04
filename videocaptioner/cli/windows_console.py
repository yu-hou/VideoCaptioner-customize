"""Windows console helpers for a windowed (no-terminal) desktop EXE.

PyInstaller windowed apps use the Windows GUI subsystem, so double-clicking
NovaCaption.exe does not open a console. CLI commands still need stdout when
the same executable is launched from cmd.exe or CI, so they attach to the
parent console at runtime.
"""

from __future__ import annotations

import sys
from typing import Sequence, TextIO


def cli_needs_console(argv: Sequence[str] | None = None) -> bool:
    """Return True when this process should print to a console.

    Desktop GUI launches (no args, or the ``gui`` command) stay windowed.
    ``--version`` / ``--help`` and every other subcommand need a console.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return False
    if any(flag in args for flag in ("--version", "-h", "--help")):
        return True
    command = next((arg for arg in args if not arg.startswith("-")), None)
    return command is not None and command != "gui"


def _stream_writable(stream: TextIO | None) -> bool:
    if stream is None:
        return False
    try:
        stream.write("")
        stream.flush()
        return True
    except Exception:
        return False


def ensure_windows_stdio() -> bool:
    """Attach a windowed Windows process to the parent console when needed."""
    if sys.platform != "win32":
        return False
    if _stream_writable(sys.stdout) and _stream_writable(sys.stderr):
        return False

    try:
        import ctypes
    except ImportError:
        return False

    kernel32 = ctypes.windll.kernel32
    # ATTACH_PARENT_PROCESS = 0xFFFFFFFF
    if not kernel32.AttachConsole(0xFFFFFFFF):
        return False

    try:
        if not _stream_writable(sys.stdout):
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
        if not _stream_writable(sys.stderr):
            sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
        if sys.stdin is None:
            sys.stdin = open("CONIN$", "r", encoding="utf-8", errors="replace")
    except OSError:
        return False
    return True
