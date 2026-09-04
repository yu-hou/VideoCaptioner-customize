from videocaptioner.cli.windows_console import cli_needs_console, ensure_windows_stdio


def test_gui_launch_does_not_need_console():
    assert cli_needs_console([]) is False
    assert cli_needs_console(["gui"]) is False
    assert cli_needs_console(["--verbose"]) is False


def test_help_and_version_need_console():
    assert cli_needs_console(["--version"]) is True
    assert cli_needs_console(["-h"]) is True
    assert cli_needs_console(["--help"]) is True
    assert cli_needs_console(["gui", "--help"]) is True


def test_cli_subcommands_need_console():
    assert cli_needs_console(["doctor", "--json"]) is True
    assert cli_needs_console(["style"]) is True
    assert cli_needs_console(["transcribe", "video.mp4"]) is True
    assert cli_needs_console(["download", "https://example.com/video"]) is True


def test_ensure_windows_stdio_is_noop_off_windows():
    assert ensure_windows_stdio() is False
