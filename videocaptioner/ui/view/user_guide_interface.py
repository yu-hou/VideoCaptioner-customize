"""Persistent in-app guide for non-technical users."""

from typing import Callable

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    PrimaryPushButton,
    PushButton,
    ScrollArea,
    StrongBodyLabel,
    SubtitleLabel,
    TitleLabel,
    isDarkTheme,
    qconfig,
    themeColor,
)


class UserGuideInterface(ScrollArea):
    """Explain setup and common workflows in plain language."""

    restartWizardRequested = pyqtSignal()
    openHomeRequested = pyqtSignal()
    openSettingsRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("userGuideInterface")
        self.setWindowTitle(self.tr("使用指南"))
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # type: ignore

        self.scrollWidget = QWidget(self)
        self.scrollWidget.setObjectName("guideScrollWidget")
        self.mainLayout = QVBoxLayout(self.scrollWidget)
        self.mainLayout.setContentsMargins(36, 30, 36, 42)
        self.mainLayout.setSpacing(18)

        self._build_header()
        self._build_setup_card()
        self._build_first_task_steps()
        self._build_workflow_cards()
        self._build_api_explanation()
        self._build_troubleshooting()
        self.mainLayout.addStretch(1)

        self.setWidget(self.scrollWidget)
        qconfig.themeChanged.connect(self._apply_theme)
        qconfig.themeColorChanged.connect(self._apply_theme)
        self._apply_theme()

    def _apply_theme(self, *_) -> None:
        accent = themeColor().name()
        if isDarkTheme():
            background = "#202220"
            text = "#F5F7F6"
            secondary = "#B8C0BC"
        else:
            background = "#F7F9F8"
            text = "#202421"
            secondary = "#59615D"

        self.setStyleSheet(
            f"""
            UserGuideInterface, QWidget#guideScrollWidget {{
                background-color: {background};
            }}
            QScrollArea {{
                border: none;
                background-color: {background};
            }}
            QLabel#guideTitle,
            QLabel#guideSectionTitle,
            QLabel#guideCardTitle {{
                color: {text};
                background-color: transparent;
            }}
            QLabel#guideSubtitle {{
                color: {secondary};
                background-color: transparent;
            }}
            QLabel#guideSectionTitle {{
                font-size: 18px;
                font-weight: 600;
                margin-top: 10px;
            }}
            QLabel#guideNumber {{
                color: white;
                background-color: {accent};
                border-radius: 15px;
                font-size: 15px;
                font-weight: 700;
            }}
            QLabel#guideBody {{
                color: {text};
                background-color: transparent;
                font-size: 14px;
                line-height: 1.5;
            }}
            QLabel#guideHint {{
                color: {secondary};
                background-color: transparent;
            }}
            """
        )

    def _build_header(self) -> None:
        title = TitleLabel(self.tr("使用指南"), self.scrollWidget)
        title.setObjectName("guideTitle")
        subtitle = SubtitleLabel(
            self.tr("不需要懂 Python 或命令行，按照下面的步骤操作即可。"),
            self.scrollWidget,
        )
        subtitle.setObjectName("guideSubtitle")
        subtitle.setWordWrap(True)
        self.mainLayout.addWidget(title)
        self.mainLayout.addWidget(subtitle)

    def _section_title(self, text: str) -> None:
        label = StrongBodyLabel(text, self.scrollWidget)
        label.setObjectName("guideSectionTitle")
        self.mainLayout.addWidget(label)

    def _build_setup_card(self) -> None:
        self._section_title(self.tr("第一次使用"))
        card = CardWidget(self.scrollWidget)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        title = StrongBodyLabel(self.tr("先完成一次基础设置"), card)
        title.setObjectName("guideCardTitle")
        description = BodyLabel(
            self.tr(
                "设置向导会帮你选择结果保存位置，并配置抖音下载所需的 "
                "Chrome 用户和 Cookie。关闭后也可以随时从这里重新打开。"
            ),
            card,
        )
        description.setObjectName("guideBody")
        description.setWordWrap(True)

        button_layout = QHBoxLayout()
        self.restartWizardButton = PrimaryPushButton(
            self.tr("重新打开设置向导"), card
        )
        self.openSettingsButton = PushButton(self.tr("打开设置"), card)
        self.restartWizardButton.clicked.connect(self.restartWizardRequested.emit)
        self.openSettingsButton.clicked.connect(self.openSettingsRequested.emit)
        button_layout.addWidget(self.restartWizardButton)
        button_layout.addWidget(self.openSettingsButton)
        button_layout.addStretch(1)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(button_layout)
        self.mainLayout.addWidget(card)

    def _build_first_task_steps(self) -> None:
        self._section_title(self.tr("4 步完成第一个视频"))
        steps = [
            (
                self.tr("准备视频"),
                self.tr(
                    "可以选择电脑里的音视频文件，也可以复制 B站、小红书、"
                    "抖音等平台的视频链接。"
                ),
            ),
            (
                self.tr("进入“主页 → 任务创建”"),
                self.tr("粘贴链接或选择本地文件，然后点击开始。"),
            ),
            (
                self.tr("按页面顺序处理"),
                self.tr(
                    "软件会依次进入“语音转录 → 字幕优化与翻译 → "
                    "字幕视频合成”。不需要的步骤可在设置中关闭。"
                ),
            ),
            (
                self.tr("查找结果"),
                self.tr(
                    "下载的视频、字幕和合成视频都会保存在设置向导中选择的"
                    "工作目录。主页底部的“查看日志”可用于排查失败原因。"
                ),
            ),
        ]
        for index, (title, content) in enumerate(steps, start=1):
            self.mainLayout.addWidget(self._step_card(index, title, content))

        self.goHomeButton = PrimaryPushButton(self.tr("前往主页开始处理"), self.scrollWidget)
        self.goHomeButton.clicked.connect(self.openHomeRequested.emit)
        self.mainLayout.addWidget(self.goHomeButton, alignment=Qt.AlignLeft)  # type: ignore

    def _step_card(self, number: int, title: str, content: str) -> CardWidget:
        card = CardWidget(self.scrollWidget)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        number_label = QLabel(str(number), card)
        number_label.setObjectName("guideNumber")
        number_label.setFixedSize(30, 30)
        number_label.setAlignment(Qt.AlignCenter)  # type: ignore

        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        title_label = StrongBodyLabel(title, card)
        title_label.setObjectName("guideCardTitle")
        content_label = BodyLabel(content, card)
        content_label.setObjectName("guideBody")
        content_label.setWordWrap(True)
        text_layout.addWidget(title_label)
        text_layout.addWidget(content_label)

        layout.addWidget(number_label, alignment=Qt.AlignTop)  # type: ignore
        layout.addLayout(text_layout, 1)
        return card

    def _build_workflow_cards(self) -> None:
        self._section_title(self.tr("常用操作怎么选"))
        workflows = [
            (
                self.tr("下载链接并自动生成字幕"),
                self.tr(
                    "主页 → 任务创建：粘贴链接后开始。若是抖音链接，请先完成"
                    "向导中的 Cookie 配置。"
                ),
            ),
            (
                self.tr("只把本地音视频转成字幕"),
                self.tr(
                    "主页 → 语音转录：选择文件和转录模型，完成后保存为 "
                    "SRT、VTT 或其他字幕格式。"
                ),
            ),
            (
                self.tr("只优化或翻译现有字幕"),
                self.tr(
                    "主页 → 字幕优化与翻译：导入已有字幕。使用 LLM 优化或"
                    "大模型翻译时，才需要配置对应模型服务。"
                ),
            ),
            (
                self.tr("只把字幕合成到视频"),
                self.tr(
                    "主页 → 字幕视频合成：分别选择视频和字幕。硬字幕会直接"
                    "显示在画面中；软字幕可在播放器中开关。"
                ),
            ),
            (
                self.tr("一次处理多个文件"),
                self.tr("左侧进入“批量处理”，添加多个本地文件后统一开始。"),
            ),
        ]
        for title, content in workflows:
            self.mainLayout.addWidget(self._text_card(title, content))

    def _text_card(
        self,
        title: str,
        content: str,
        button_text: str | None = None,
        callback: Callable[[], None] | None = None,
    ) -> CardWidget:
        card = CardWidget(self.scrollWidget)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)
        title_label = StrongBodyLabel(title, card)
        title_label.setObjectName("guideCardTitle")
        content_label = BodyLabel(content, card)
        content_label.setObjectName("guideBody")
        content_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(content_label)
        if button_text and callback:
            button = PushButton(button_text, card)
            button.clicked.connect(callback)
            layout.addWidget(button, alignment=Qt.AlignLeft)  # type: ignore
        return card

    def _build_api_explanation(self) -> None:
        self._section_title(self.tr("什么时候需要 API Key"))
        content = BodyLabel(
            self.tr(
                "通常不需要：视频下载、字幕视频合成，以及当前可直接使用的"
                "免费转录或翻译服务。\n\n"
                "需要配置：选择 Whisper API 转录、LLM 字幕优化，或选择"
                "大模型进行翻译时。API Key 由你选择的模型服务商提供，"
                "填写位置在“设置 → LLM配置 / 转录配置”。\n\n"
                "不确定时可以先不填；遇到明确提示“API Key 为空”或"
                "“连接失败”时，再打开设置配置并点击连接测试。"
            ),
            self.scrollWidget,
        )
        content.setObjectName("guideBody")
        content.setWordWrap(True)
        card = CardWidget(self.scrollWidget)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.addWidget(content)
        self.mainLayout.addWidget(card)

    def _build_troubleshooting(self) -> None:
        self._section_title(self.tr("遇到问题时"))
        hints = [
            self.tr("抖音下载失败：重新打开设置向导，读取并测试 Cookie。"),
            self.tr("模型连接失败：检查 API 地址、API Key 和模型名称。"),
            self.tr("找不到输出文件：检查“设置 → 工作目录路径”。"),
            self.tr("处理卡住或失败：点击主页底部“查看日志”读取具体原因。"),
        ]
        card = CardWidget(self.scrollWidget)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        for hint in hints:
            label = CaptionLabel(f"• {hint}", card)
            label.setObjectName("guideHint")
            label.setWordWrap(True)
            layout.addWidget(label)
        self.mainLayout.addWidget(card)
