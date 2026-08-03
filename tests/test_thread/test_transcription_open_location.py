"""Tests for transcription page open-location resolution."""

from pathlib import Path
from unittest.mock import MagicMock

from videocaptioner.core.entities import TranscribeTask
from videocaptioner.ui.common.config import cfg


def test_resolve_prefers_existing_subtitle_output(qapp, tmp_path):
    from videocaptioner.ui.view.transcription_interface import TranscriptionInterface

    video = tmp_path / "demo.mp4"
    video.write_bytes(b"v")
    subtitle_dir = tmp_path / "subtitle"
    subtitle_dir.mkdir()
    subtitle = subtitle_dir / "【原始字幕】demo.srt"
    subtitle.write_text("1\n", encoding="utf-8")

    interface = TranscriptionInterface()
    try:
        interface.task = TranscribeTask(
            file_path=str(video),
            output_path=str(subtitle),
        )
        interface.video_info_card.task = interface.task
        interface.video_info_card.video_info = MagicMock(file_path=str(video))

        target, reveal = interface._resolve_current_location()
        assert reveal is True
        assert Path(target) == subtitle
    finally:
        interface.close()


def test_resolve_falls_back_to_current_video_when_no_output(qapp, tmp_path):
    from videocaptioner.ui.view.transcription_interface import TranscriptionInterface

    video = tmp_path / "clip.mp4"
    video.write_bytes(b"v")

    interface = TranscriptionInterface()
    try:
        interface.task = TranscribeTask(
            file_path=str(video),
            output_path=str(tmp_path / "subtitle" / "missing.srt"),
        )
        interface.video_info_card.task = interface.task
        interface.video_info_card.video_info = MagicMock(file_path=str(video))

        target, reveal = interface._resolve_current_location()
        assert reveal is True
        assert Path(target) == video
    finally:
        interface.close()


def test_resolve_ignores_stale_task_output_after_reselect(qapp, tmp_path):
    from videocaptioner.ui.view.transcription_interface import TranscriptionInterface

    old_video = tmp_path / "old.mp4"
    new_video = tmp_path / "new.mp4"
    old_video.write_bytes(b"o")
    new_video.write_bytes(b"n")
    old_subtitle = tmp_path / "old.srt"
    old_subtitle.write_text("1\n", encoding="utf-8")

    interface = TranscriptionInterface()
    try:
        # task 仍指向旧文件，但 UI 已切换到新视频
        interface.task = TranscribeTask(
            file_path=str(old_video),
            output_path=str(old_subtitle),
        )
        interface.video_info_card.task = interface.task
        interface.video_info_card.video_info = MagicMock(file_path=str(new_video))

        target, reveal = interface._resolve_current_location()
        assert reveal is True
        assert Path(target) == new_video
    finally:
        interface.close()


def test_file_dialog_starts_at_current_video_dir(qapp, tmp_path):
    from videocaptioner.ui.view.transcription_interface import TranscriptionInterface

    video = tmp_path / "inside" / "a.mp4"
    video.parent.mkdir()
    video.write_bytes(b"v")

    previous = cfg.get(cfg.work_dir)
    interface = TranscriptionInterface()
    try:
        interface.video_info_card.video_info = MagicMock(file_path=str(video))
        assert interface._start_dir_for_file_dialog() == str(video.parent)
    finally:
        cfg.set(cfg.work_dir, previous)
        interface.close()
