"""Tests for home pipeline scope orchestration."""

from unittest.mock import MagicMock, patch

import pytest

from videocaptioner.core.entities import BatchTaskType, PipelineScope
from videocaptioner.ui.common.config import cfg


def test_pipeline_scope_continue_flags():
    assert PipelineScope.ACQUIRE_ONLY.continues_after_transcribe is False
    assert PipelineScope.ACQUIRE_ONLY.continues_after_subtitle is False

    assert PipelineScope.TO_TRANSCRIBE.continues_after_transcribe is False
    assert PipelineScope.TO_TRANSCRIBE.continues_after_subtitle is False

    assert PipelineScope.TO_SUBTITLE.continues_after_transcribe is True
    assert PipelineScope.TO_SUBTITLE.continues_after_subtitle is False

    assert PipelineScope.FULL.continues_after_transcribe is True
    assert PipelineScope.FULL.continues_after_subtitle is True


def test_batch_task_type_aligns_with_pipeline_scope_labels():
    assert BatchTaskType.TRANSCRIBE.value == PipelineScope.TO_TRANSCRIBE.value
    assert BatchTaskType.TRANS_SUB.value == PipelineScope.TO_SUBTITLE.value
    assert BatchTaskType.FULL_PROCESS.value == PipelineScope.FULL.value
    assert BatchTaskType.SUBTITLE.value == "仅字幕处理"


def test_task_creation_pipeline_scope_combo_persists(qapp):
    from videocaptioner.ui.view.task_creation_interface import TaskCreationInterface

    previous = cfg.get(cfg.pipeline_scope)
    interface = TaskCreationInterface()
    try:
        index = interface.pipeline_scope_combo.findData(PipelineScope.ACQUIRE_ONLY)
        assert index >= 0
        interface.pipeline_scope_combo.setCurrentIndex(index)

        assert cfg.get(cfg.pipeline_scope) == PipelineScope.ACQUIRE_ONLY
        assert interface.current_pipeline_scope() == PipelineScope.ACQUIRE_ONLY
        assert "不自动" in interface.scope_desc_label.text()
        assert interface.open_work_dir_button.text() == "打开工作目录"
    finally:
        cfg.set(cfg.pipeline_scope, previous)
        interface.close()


def test_acquire_only_infobar_offers_open_folder(qapp, tmp_path):
    from videocaptioner.ui.view.home_interface import HomeInterface

    previous = cfg.get(cfg.pipeline_scope)
    cfg.set(cfg.pipeline_scope, PipelineScope.ACQUIRE_ONLY)
    demo = tmp_path / "demo.mp4"
    demo.write_bytes(b"x")
    home = HomeInterface()
    try:
        with patch(
            "videocaptioner.ui.view.home_interface.reveal_in_explorer"
        ) as reveal:
            home.switch_to_transcription(str(demo))
            # 触发 InfoBar 上的打开按钮逻辑
            home._open_acquired_file_location(str(demo))
            reveal.assert_called_once_with(str(demo))
    finally:
        cfg.set(cfg.pipeline_scope, previous)
        home.close()


@pytest.mark.parametrize(
    ("scope", "expect_process", "expect_need_next"),
    [
        (PipelineScope.ACQUIRE_ONLY, False, None),
        (PipelineScope.TO_TRANSCRIBE, True, False),
        (PipelineScope.TO_SUBTITLE, True, True),
        (PipelineScope.FULL, True, True),
    ],
)
def test_home_switch_to_transcription_respects_scope(
    qapp, scope, expect_process, expect_need_next
):
    from videocaptioner.ui.view.home_interface import HomeInterface

    previous = cfg.get(cfg.pipeline_scope)
    cfg.set(cfg.pipeline_scope, scope)
    home = HomeInterface()
    try:
        home.transcription_interface.process = MagicMock()
        home.transcription_interface.set_task = MagicMock()

        with patch(
            "videocaptioner.ui.view.home_interface.TaskFactory.create_transcribe_task"
        ) as create_task:
            create_task.return_value = MagicMock()
            home.switch_to_transcription("/tmp/demo.mp4")

            if expect_process:
                create_task.assert_called_once()
                assert create_task.call_args.kwargs["need_next_task"] is expect_need_next
                home.transcription_interface.process.assert_called_once()
                assert (
                    home.stackedWidget.currentWidget()
                    is home.transcription_interface
                )
            else:
                create_task.assert_not_called()
                home.transcription_interface.process.assert_not_called()
                assert (
                    home.stackedWidget.currentWidget()
                    is home.task_creation_interface
                )
    finally:
        cfg.set(cfg.pipeline_scope, previous)
        home.close()


@pytest.mark.parametrize(
    ("scope", "expect_need_next"),
    [
        (PipelineScope.TO_SUBTITLE, False),
        (PipelineScope.FULL, True),
    ],
)
def test_home_switch_to_subtitle_sets_need_next_for_synthesis(
    qapp, scope, expect_need_next
):
    from videocaptioner.ui.view.home_interface import HomeInterface

    previous = cfg.get(cfg.pipeline_scope)
    cfg.set(cfg.pipeline_scope, scope)
    home = HomeInterface()
    try:
        home.subtitle_optimization_interface.process = MagicMock()
        home.subtitle_optimization_interface.set_task = MagicMock()

        with patch(
            "videocaptioner.ui.view.home_interface.TaskFactory.create_subtitle_task"
        ) as create_task:
            create_task.return_value = MagicMock()
            home.switch_to_subtitle_optimization(
                "/tmp/demo.srt", "/tmp/demo.mp4"
            )

            create_task.assert_called_once()
            assert create_task.call_args.kwargs["need_next_task"] is expect_need_next
            home.subtitle_optimization_interface.process.assert_called_once()
    finally:
        cfg.set(cfg.pipeline_scope, previous)
        home.close()
