"""Tests for task input and clipboard handling."""

import sys

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from videocaptioner.ui.view.task_creation_interface import TaskCreationInterface


def test_normalize_user_input_extracts_url_from_share_text():
    value = (
        "复制此消息打开视频 "
        "https://www.douyin.com/jingxuan?modal_id=7659705531116870065 ，"
        "看看这个作品"
    )

    assert TaskCreationInterface.normalize_user_input(value) == (
        "https://www.douyin.com/video/7659705531116870065"
    )


def test_paste_button_reads_clipboard_and_normalizes_url(qapp):
    interface = TaskCreationInterface()
    QApplication.clipboard().setText(
        "分享链接： https://www.bilibili.com/video/BV1YPgh6TEWH/ \n"
    )

    interface.paste_button.click()

    assert interface.search_input.text() == (
        "https://www.bilibili.com/video/BV1YPgh6TEWH/"
    )
    interface.close()


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS modifier mapping")
def test_macos_command_v_pastes(qapp):
    interface = TaskCreationInterface()
    interface.show()
    interface.search_input.setFocus()
    QApplication.clipboard().setText("https://example.com/command-v")

    # Qt represents the physical Command key as ControlModifier on macOS.
    QTest.keyClick(interface.search_input, Qt.Key_V, Qt.ControlModifier)

    assert interface.search_input.text() == "https://example.com/command-v"
    interface.close()


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS modifier mapping")
def test_macos_control_v_compatibility_pastes_instead_of_typing_v(qapp):
    interface = TaskCreationInterface()
    interface.show()
    interface.search_input.setFocus()
    QApplication.clipboard().setText("https://example.com/video")

    # Qt maps the physical Control key to MetaModifier on macOS.
    QTest.keyClick(interface.search_input, Qt.Key_V, Qt.MetaModifier)

    assert interface.search_input.text() == "https://example.com/video"
    interface.close()
