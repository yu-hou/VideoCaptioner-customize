"""批量链接下载对话框：粘贴多条 URL，串行下载到工作目录。"""

from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout
from qfluentwidgets import (
    BodyLabel,
    InfoBar,
    InfoBarPosition,
    MessageBoxBase,
    PlainTextEdit,
    ProgressBar,
    PushButton,
    SubtitleLabel,
)

from videocaptioner.core.constant import (
    INFOBAR_DURATION_SUCCESS,
    INFOBAR_DURATION_WARNING,
)
from videocaptioner.core.utils.platform_utils import open_folder
from videocaptioner.core.utils.url_parser import extract_urls
from videocaptioner.ui.thread.batch_download_thread import BatchDownloadThread


class BatchUrlDialog(MessageBoxBase):
    """多链接批量下载（一期：仅下载，不进入转录流水线）。"""

    batch_completed = pyqtSignal(int, int, list)  # success, fail, paths

    def __init__(self, work_dir: str, parent=None):
        super().__init__(parent)
        self.work_dir = work_dir
        self._thread: Optional[BatchDownloadThread] = None
        self._downloaded_paths: List[str] = []
        self._is_downloading = False
        self._total = 0

        self.widget.setMinimumWidth(560)
        self._setup_ui()
        self._connect_signals()
        self._update_count_label()

    def _setup_ui(self) -> None:
        self.titleLabel = SubtitleLabel(self.tr("批量链接下载"), self)
        self.hint_label = BodyLabel(
            self.tr(
                "粘贴多条视频链接，支持换行 / 空格 / 逗号 / 分号分隔，"
                "也可直接粘贴分享文案。将串行下载到工作目录。"
            ),
            self,
        )
        self.hint_label.setWordWrap(True)

        self.url_edit = PlainTextEdit(self)
        self.url_edit.setPlaceholderText(
            self.tr(
                "例如：\n"
                "https://www.bilibili.com/video/BVxxxx\n"
                "https://www.youtube.com/watch?v=xxxx\n"
                "或用逗号、分号分隔多条链接"
            )
        )
        self.url_edit.setMinimumHeight(180)

        self.count_label = BodyLabel(self.tr("已识别 0 条链接"), self)
        self.status_label = BodyLabel("", self)
        self.status_label.setWordWrap(True)
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.status_label.hide()

        self.open_folder_btn = PushButton(self.tr("打开工作目录"), self)
        self.open_folder_btn.hide()

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.hint_label)
        layout.addWidget(self.url_edit)
        layout.addWidget(self.count_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)

        folder_row = QHBoxLayout()
        folder_row.addWidget(self.open_folder_btn)
        folder_row.addStretch(1)
        layout.addLayout(folder_row)

        self.viewLayout.addLayout(layout)

        self.yesButton.setText(self.tr("开始下载"))
        self.cancelButton.setText(self.tr("关闭"))
        self.setWindowTitle(self.tr("批量链接下载"))

    def _connect_signals(self) -> None:
        self.url_edit.textChanged.connect(self._update_count_label)
        try:
            self.yesButton.clicked.disconnect()
        except TypeError:
            pass
        try:
            self.cancelButton.clicked.disconnect()
        except TypeError:
            pass
        self.yesButton.clicked.connect(self._on_primary_clicked)
        self.cancelButton.clicked.connect(self._on_close_clicked)
        self.open_folder_btn.clicked.connect(self._open_work_dir)

    def current_urls(self) -> list[str]:
        return extract_urls(self.url_edit.toPlainText())

    def _update_count_label(self) -> None:
        count = len(self.current_urls())
        self.count_label.setText(self.tr("已识别 {n} 条链接").format(n=count))
        self.yesButton.setEnabled(count > 0 and not self._is_downloading)

    def _on_primary_clicked(self) -> None:
        if self._is_downloading:
            self._cancel_download()
            return
        self._start_download()

    def _start_download(self) -> None:
        urls = self.current_urls()
        if not urls:
            InfoBar.warning(
                self.tr("未识别到链接"),
                self.tr("请粘贴至少一个有效的 http(s) 视频链接"),
                duration=INFOBAR_DURATION_WARNING,
                position=InfoBarPosition.TOP,
                parent=self.window(),
            )
            return

        self._is_downloading = True
        self._total = len(urls)
        self._downloaded_paths = []
        self.url_edit.setReadOnly(True)
        self.progress_bar.show()
        self.status_label.show()
        self.open_folder_btn.hide()
        self.progress_bar.setValue(0)
        self.status_label.setText(self.tr("准备下载…"))
        self.yesButton.setText(self.tr("取消下载"))
        self.yesButton.setEnabled(True)
        self.cancelButton.setEnabled(False)

        self._thread = BatchDownloadThread(urls, self.work_dir, self)
        self._thread.item_started.connect(self._on_item_started)
        self._thread.item_progress.connect(self._on_item_progress)
        self._thread.item_finished.connect(self._on_item_finished)
        self._thread.item_error.connect(self._on_item_error)
        self._thread.batch_finished.connect(self._on_batch_finished)
        self._thread.start()

    def _cancel_download(self) -> None:
        if self._thread and self._thread.isRunning():
            self._thread.cancel()
            self.status_label.setText(self.tr("正在取消，当前条目结束后停止…"))
            self.yesButton.setEnabled(False)

    def _on_item_started(self, index: int, total: int, url: str) -> None:
        short = url if len(url) <= 64 else url[:61] + "..."
        self.status_label.setText(
            self.tr("正在下载 {i}/{total}\n{url}").format(
                i=index + 1, total=total, url=short
            )
        )
        base = int(index / total * 100) if total else 0
        self.progress_bar.setValue(base)

    def _on_item_progress(self, index: int, percent: int, message: str) -> None:
        total = self._total or 1
        overall = int((index + percent / 100.0) / total * 100)
        self.progress_bar.setValue(min(overall, 99))
        self.status_label.setText(
            self.tr("正在下载 {i}/{total} · {msg}").format(
                i=index + 1, total=total, msg=message
            )
        )

    def _on_item_finished(self, index: int, url: str, path: str) -> None:
        self._downloaded_paths.append(path)

    def _on_item_error(self, index: int, url: str, error: str) -> None:
        short = url if len(url) <= 48 else url[:45] + "..."
        self.status_label.setText(
            self.tr("第 {i} 条失败：{url}\n{error}").format(
                i=index + 1, url=short, error=error
            )
        )

    def _on_batch_finished(self, success: int, fail: int, paths: list) -> None:
        self._is_downloading = False
        self._downloaded_paths = list(paths)
        self.url_edit.setReadOnly(False)
        if success and not fail:
            self.progress_bar.setValue(100)
        self.yesButton.setText(self.tr("开始下载"))
        self.yesButton.setEnabled(True)
        self.cancelButton.setEnabled(True)
        self.cancelButton.setText(self.tr("关闭"))
        self.open_folder_btn.show()
        self._update_count_label()

        summary = self.tr("完成：成功 {ok}，失败 {fail}").format(ok=success, fail=fail)
        self.status_label.setText(summary)
        self.status_label.show()

        InfoBar.success(
            self.tr("批量下载结束"),
            summary + self.tr("。文件已保存到工作目录"),
            duration=INFOBAR_DURATION_SUCCESS,
            position=InfoBarPosition.TOP,
            parent=self.window(),
        )
        self.batch_completed.emit(success, fail, list(paths))
        self._thread = None

    def _open_work_dir(self) -> None:
        open_folder(self.work_dir)

    def _on_close_clicked(self) -> None:
        if self._is_downloading:
            return
        self.reject()

    def reject(self) -> None:
        if self._is_downloading and self._thread and self._thread.isRunning():
            self._thread.cancel()
            return
        super().reject()
