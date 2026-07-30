"""Tests for task input and clipboard handling."""

from PyQt5.QtWidgets import QApplication

from videocaptioner.ui.view.task_creation_interface import TaskCreationInterface


def test_normalize_user_input_extracts_url_from_share_text():
    value = (
        "复制此消息打开视频 "
        "https://www.douyin.com/jingxuan?modal_id=7659705531116870065 ，"
        "看看这个作品"
    )

    assert TaskCreationInterface.normalize_user_input(value) == (
        "https://www.douyin.com/jingxuan?modal_id=7659705531116870065"
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
