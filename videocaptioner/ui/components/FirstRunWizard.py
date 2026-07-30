"""First-run setup wizard for non-technical desktop users."""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import LineEdit, PrimaryPushButton, PushButton, SubtitleLabel, TitleLabel

from videocaptioner.ui.common.config import cfg
from videocaptioner.ui.components.DouyinCookieManager import DouyinCookieManager


class FirstRunWizard(QDialog):
    """Guide users through the minimum setup required by the desktop app."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("欢迎使用 VideoCaptioner"))
        self.setMinimumSize(820, 680)
        self.setModal(True)

        self.pages = QStackedWidget(self)
        self.pages.addWidget(self._create_welcome_page())
        self.pages.addWidget(self._create_work_dir_page())
        self.pages.addWidget(self._create_douyin_page())
        self.pages.addWidget(self._create_finish_page())

        self.skipButton = PushButton(self.tr("跳过向导"), self)
        self.backButton = PushButton(self.tr("上一步"), self)
        self.nextButton = PrimaryPushButton(self.tr("下一步"), self)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.skipButton)
        button_layout.addStretch(1)
        button_layout.addWidget(self.backButton)
        button_layout.addWidget(self.nextButton)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(self.pages, 1)
        layout.addLayout(button_layout)

        self.skipButton.clicked.connect(self._complete)
        self.backButton.clicked.connect(self._go_back)
        self.nextButton.clicked.connect(self._go_next)
        self.pages.currentChanged.connect(self._update_buttons)
        self.cookieManager.busyChanged.connect(self._on_cookie_busy)
        self._update_buttons(0)

    def _page(self, title: str, description: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)
        title_label = TitleLabel(title, page)
        description_label = SubtitleLabel(description, page)
        description_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        return page, layout

    def _create_welcome_page(self) -> QWidget:
        page, layout = self._page(
            self.tr("欢迎使用 VideoCaptioner"),
            self.tr(
                "这个向导会帮助你设置文件保存位置和抖音下载环境。"
                "所有设置以后都可以在“设置”页面重新修改。"
            ),
        )
        tips = QLabel(
            self.tr(
                "你不需要安装 Python、uv 或 FFmpeg。\n\n"
                "接下来只需：\n"
                "1. 选择视频和字幕的保存位置\n"
                "2. 选择平时使用的 Chrome 用户\n"
                "3. 登录抖音并读取 Cookie"
            ),
            page,
        )
        tips.setWordWrap(True)
        tips.setAlignment(Qt.AlignTop)  # type: ignore
        layout.addWidget(tips)
        layout.addStretch(1)
        return page

    def _create_work_dir_page(self) -> QWidget:
        page, layout = self._page(
            self.tr("选择工作目录"),
            self.tr("下载的视频、字幕和合成结果都会保存在这里。"),
        )
        path_layout = QHBoxLayout()
        self.workDirEdit = LineEdit(page)
        self.workDirEdit.setText(str(cfg.get(cfg.work_dir)))
        browse_button = PushButton(self.tr("选择文件夹"), page)
        browse_button.clicked.connect(self._choose_work_dir)
        path_layout.addWidget(self.workDirEdit, 1)
        path_layout.addWidget(browse_button)
        layout.addLayout(path_layout)
        layout.addStretch(1)
        return page

    def _create_douyin_page(self) -> QWidget:
        page, layout = self._page(
            self.tr("配置抖音下载"),
            self.tr(
                "先选择 Chrome 用户，再点击“打开抖音”完成登录和验证，"
                "最后点击“读取 Cookie”。这一步也可以暂时跳过。"
            ),
        )
        self.cookieManager = DouyinCookieManager(page)
        layout.addWidget(self.cookieManager, 1)
        return page

    def _create_finish_page(self) -> QWidget:
        page, layout = self._page(
            self.tr("设置完成"),
            self.tr("现在可以粘贴视频链接，开始下载、转录、翻译和合成。"),
        )
        reminder = QLabel(
            self.tr(
                "如果以后抖音提示 Cookie 失效，请打开：\n"
                "设置 → 抖音 Cookie → 打开抖音 → 读取 Cookie → 测试 Cookie"
            ),
            page,
        )
        reminder.setWordWrap(True)
        layout.addWidget(reminder)
        layout.addStretch(1)
        return page

    def _choose_work_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            self.tr("选择工作目录"),
            self.workDirEdit.text() or str(Path.home()),
        )
        if folder:
            self.workDirEdit.setText(folder)

    def _save_work_dir(self) -> bool:
        folder_text = self.workDirEdit.text().strip()
        if not folder_text:
            return False
        folder = Path(folder_text).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
        cfg.set(cfg.work_dir, str(folder))
        return True

    def _go_back(self):
        self.pages.setCurrentIndex(max(0, self.pages.currentIndex() - 1))

    def _go_next(self):
        index = self.pages.currentIndex()
        if index == 1 and not self._save_work_dir():
            self.workDirEdit.setFocus()
            return
        if index == self.pages.count() - 1:
            self._complete()
            return
        self.pages.setCurrentIndex(index + 1)

    def _update_buttons(self, index: int):
        self.backButton.setEnabled(index > 0)
        self.nextButton.setText(
            self.tr("完成") if index == self.pages.count() - 1 else self.tr("下一步")
        )

    def _on_cookie_busy(self, busy: bool):
        self.skipButton.setEnabled(not busy)
        self.backButton.setEnabled(not busy and self.pages.currentIndex() > 0)
        self.nextButton.setEnabled(not busy)

    def _complete(self):
        if self.pages.currentIndex() >= 1:
            self._save_work_dir()
        cfg.set(cfg.first_run_completed, True)
        self.accept()
