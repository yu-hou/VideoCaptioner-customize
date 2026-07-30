"""First-run setup wizard for non-technical desktop users."""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    LineEdit,
    PrimaryPushButton,
    PushButton,
    ScrollArea,
    SubtitleLabel,
    TitleLabel,
    isDarkTheme,
    qconfig,
    themeColor,
)

from videocaptioner.ui.common.config import cfg
from videocaptioner.ui.components.DouyinCookieManager import DouyinCookieManager


class FirstRunWizard(QDialog):
    """Guide users through the minimum setup required by the desktop app."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("firstRunWizard")
        self.setWindowTitle(self.tr("欢迎使用 NovaCaption"))
        self.setMinimumSize(820, 680)
        self.setModal(True)

        self.accentBar = QFrame(self)
        self.accentBar.setObjectName("accentBar")
        self.accentBar.setFixedHeight(4)

        self.stepLabel = QLabel(self)
        self.stepLabel.setObjectName("stepLabel")
        self.stepLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore

        self.pages = QStackedWidget(self)
        self.pages.setObjectName("wizardPages")
        self.pages.addWidget(self._create_welcome_page())
        self.pages.addWidget(self._create_work_dir_page())
        self.pages.addWidget(self._create_douyin_page())
        self.pages.addWidget(self._create_finish_page())

        self.buttonSeparator = QFrame(self)
        self.buttonSeparator.setObjectName("buttonSeparator")
        self.buttonSeparator.setFrameShape(QFrame.HLine)
        self.buttonSeparator.setFixedHeight(1)

        self.skipButton = PushButton(self.tr("跳过向导"), self)
        self.backButton = PushButton(self.tr("上一步"), self)
        self.nextButton = PrimaryPushButton(self.tr("下一步"), self)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.skipButton)
        button_layout.addStretch(1)
        button_layout.addWidget(self.backButton)
        button_layout.addWidget(self.nextButton)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.setSpacing(14)
        layout.addWidget(self.accentBar)
        layout.addWidget(self.stepLabel)
        layout.addWidget(self.pages, 1)
        layout.addWidget(self.buttonSeparator)
        layout.addLayout(button_layout)

        self.skipButton.clicked.connect(self._complete)
        self.backButton.clicked.connect(self._go_back)
        self.nextButton.clicked.connect(self._go_next)
        self.pages.currentChanged.connect(self._update_buttons)
        self.cookieManager.busyChanged.connect(self._on_cookie_busy)
        qconfig.themeChanged.connect(self._apply_theme)
        qconfig.themeColorChanged.connect(self._apply_theme)
        self._apply_theme()
        self._update_buttons(0)

    def _page(self, title: str, description: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget(self)
        page.setObjectName("wizardPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)
        title_label = TitleLabel(title, page)
        title_label.setObjectName("wizardTitle")
        description_label = SubtitleLabel(description, page)
        description_label.setObjectName("wizardDescription")
        description_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        return page, layout

    def _create_welcome_page(self) -> QWidget:
        page, layout = self._page(
            self.tr("欢迎使用 NovaCaption"),
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
                "3. 登录抖音并读取 Cookie\n\n"
                "NovaCaption 是基于 VideoCaptioner 的独立定制版本，"
                "并非上游官方发行。"
            ),
            page,
        )
        tips.setObjectName("wizardBody")
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
        cookie_scroll = ScrollArea(page)
        cookie_scroll.setObjectName("cookieScrollArea")
        cookie_scroll.setWidgetResizable(True)
        cookie_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # type: ignore
        self.cookieManager = DouyinCookieManager(cookie_scroll)
        cookie_scroll.setWidget(self.cookieManager)
        layout.addWidget(cookie_scroll, 1)
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
        reminder.setObjectName("wizardBody")
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
        self.stepLabel.setText(
            self.tr("设置进度")
            + f"  {index + 1} / {self.pages.count()}"
        )
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

    def _apply_theme(self, *_):
        """Keep the native dialog surface aligned with Fluent's active theme."""
        accent = themeColor().name()
        if isDarkTheme():
            background = "#202220"
            text = "#F5F7F6"
            secondary = "#B8C0BC"
            separator = "rgba(255, 255, 255, 28)"
        else:
            background = "#F7F9F8"
            text = "#202421"
            secondary = "#59615D"
            separator = "rgba(0, 0, 0, 24)"

        self.setStyleSheet(
            f"""
            QDialog#firstRunWizard {{
                background-color: {background};
            }}
            QStackedWidget#wizardPages,
            QWidget#wizardPage,
            QScrollArea#cookieScrollArea,
            QScrollArea#cookieScrollArea > QWidget > QWidget {{
                background-color: transparent;
                border: none;
            }}
            QFrame#accentBar {{
                border: none;
                border-radius: 2px;
                background-color: {accent};
            }}
            QFrame#buttonSeparator {{
                border: none;
                background-color: {separator};
            }}
            QLabel#stepLabel {{
                color: {accent};
                background-color: transparent;
                font-size: 13px;
                font-weight: 600;
                padding-right: 4px;
            }}
            QLabel#wizardTitle {{
                color: {text};
                background-color: transparent;
                font-size: 28px;
                font-weight: 600;
            }}
            QLabel#wizardDescription {{
                color: {secondary};
                background-color: transparent;
                font-size: 15px;
            }}
            QLabel#wizardBody {{
                color: {text};
                background-color: transparent;
                font-size: 15px;
                line-height: 1.5;
            }}
            """
        )
