# -*- coding: utf-8 -*-
import os
import sys
from urllib.parse import urlparse

from PyQt5.QtCore import QStandardPaths, Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    FluentIcon,
    HyperlinkButton,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    ProgressBar,
    PushButton,
    ToolButton,
)

from videocaptioner.config import APP_NAME, APPDATA_PATH, ASSETS_PATH, VERSION
from videocaptioner.core.constant import (
    INFOBAR_DURATION_ERROR,
    INFOBAR_DURATION_INFO,
    INFOBAR_DURATION_SUCCESS,
    INFOBAR_DURATION_WARNING,
)
from videocaptioner.core.entities import (
    PipelineScope,
    SupportedAudioFormats,
    SupportedVideoFormats,
)
from videocaptioner.core.utils.platform_utils import open_folder
from videocaptioner.core.utils.url_parser import extract_urls
from videocaptioner.ui.common.config import cfg
from videocaptioner.ui.components.BatchUrlDialog import BatchUrlDialog
from videocaptioner.ui.thread.video_download_thread import VideoDownloadThread
from videocaptioner.ui.view.log_window import LogWindow

LOGO_PATH = ASSETS_PATH / "logo.png"


class UrlLineEdit(LineEdit):
    """URL input with a Windows-style Ctrl+V fallback on macOS."""

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Paste):
            self.paste()
            event.accept()
            return
        if (
            sys.platform == "darwin"
            and event.key() == Qt.Key_V
            and event.modifiers() == Qt.MetaModifier
        ):
            self.paste()
            event.accept()
            return
        super().keyPressEvent(event)


class TaskCreationInterface(QWidget):
    """
    任务创建界面类，用于创建和配置任务。
    """

    finished = pyqtSignal(str)  # 该信号用于在任务创建完成后通知主窗口

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task = None
        self.log_window = None

        self.setObjectName("TaskCreationInterface")
        self.setAttribute(Qt.WA_StyledBackground, True)  # type: ignore
        self.setAcceptDrops(True)

        self.setup_ui()
        self.setup_values()
        self.setup_signals()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setObjectName("main_layout")
        # 间距过大时 minimumSizeHint 会超过笔记本可用高度，导致窗口贴顶、底部按钮点不到
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(0, 8, 0, 8)
        self.main_layout.addStretch(1)
        self.setup_logo()
        self.setup_search_layout()
        self.setup_pipeline_scope_layout()
        self.setup_status_layout()
        self.setup_info_label()

    def setup_logo(self):
        self.logo_label = QLabel(self)
        self.logo_pixmap = QPixmap(str(LOGO_PATH))
        self.logo_pixmap = self.logo_pixmap.scaled(
            110,
            110,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.SmoothTransformation,  # type: ignore
        )

        self.logo_label.setPixmap(self.logo_pixmap)
        self.logo_label.setAlignment(Qt.AlignCenter)  # type: ignore
        self.main_layout.addWidget(self.logo_label)
        self.main_layout.addSpacing(4)

    def setup_search_layout(self):
        self.search_layout = QHBoxLayout()
        self.search_layout.setContentsMargins(80, 0, 80, 0)
        self.search_input = UrlLineEdit(self)
        self.search_input.setPlaceholderText(self.tr("请拖拽文件或输入视频URL"))
        self.search_input.setFixedHeight(40)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(
            self.search_input.styleSheet()
            + """
            QLineEdit {
                border-radius: 18px;
                padding: 0 20px;
                background-color: transparent;
                border: 1px solid rgba(255,255, 255, 0.08);
            }
            QLineEdit:focus[transparent=true] {
                border: 1px solid rgba(47,141, 99, 0.48);
            }

        """
        )
        self.paste_button = ToolButton(FluentIcon.PASTE, self)
        self.paste_button.setFixedSize(40, 40)
        self.paste_button.setToolTip(self.tr("粘贴链接"))
        self.start_button = ToolButton(FluentIcon.FOLDER, self)
        self.start_button.setFixedSize(40, 40)
        self.start_button.setStyleSheet(
            self.start_button.styleSheet()
            + """
            QToolButton {
                border-radius: 20px;
                background-color: #2F8D63;
            }
            QToolButton:hover {
                background-color: #2E805C;
            }
            QToolButton:pressed {
                background-color: #2E905C;
            }
        """
        )
        self.search_layout.addWidget(self.search_input)
        self.search_layout.addWidget(self.paste_button)
        self.search_layout.addWidget(self.start_button)
        self.search_layout.setSpacing(10)
        self.main_layout.addLayout(self.search_layout)

        # 批量链接入口
        batch_row = QHBoxLayout()
        batch_row.setContentsMargins(80, 0, 80, 0)
        batch_row.addStretch()
        self.batch_url_button = PushButton(self.tr("批量链接下载"), self)
        self.batch_url_button.setIcon(FluentIcon.CLOUD_DOWNLOAD)
        self.batch_url_button.setToolTip(
            self.tr("一次粘贴多条视频链接，串行下载到工作目录")
        )
        batch_row.addWidget(self.batch_url_button)
        batch_row.addStretch()
        self.main_layout.addLayout(batch_row)

    def setup_pipeline_scope_layout(self):
        """处理范围：控制主页自动流水线执行到哪一步。"""
        self.pipeline_scope_descriptions = {
            PipelineScope.ACQUIRE_ONLY: self.tr(
                "仅下载或导入视频，不自动进入后续处理；完成后可打开文件所在位置"
            ),
            PipelineScope.TO_TRANSCRIBE: self.tr(
                "自动执行到语音转录，生成原始字幕后停止"
            ),
            PipelineScope.TO_SUBTITLE: self.tr(
                "自动执行到字幕优化与翻译，不合成视频"
            ),
            PipelineScope.FULL: self.tr("转录 → 字幕处理 → 合成视频（全流程）"),
        }

        self.scope_layout = QVBoxLayout()
        self.scope_layout.setContentsMargins(80, 0, 80, 0)
        self.scope_layout.setSpacing(8)

        scope_row = QHBoxLayout()
        scope_row.setSpacing(12)
        self.scope_label = BodyLabel(self.tr("处理范围"), self)
        self.scope_label.setStyleSheet("font-size: 14px; color: #888888;")
        self.pipeline_scope_combo = ComboBox(self)
        self.pipeline_scope_combo.setMinimumWidth(180)
        for scope in PipelineScope:
            self.pipeline_scope_combo.addItem(str(scope), userData=scope)

        scope_row.addStretch()
        scope_row.addWidget(self.scope_label)
        scope_row.addWidget(self.pipeline_scope_combo)
        scope_row.addStretch()

        self.scope_desc_label = BodyLabel("", self)
        self.scope_desc_label.setAlignment(Qt.AlignCenter)  # type: ignore
        self.scope_desc_label.setStyleSheet("font-size: 12px; color: #888888;")
        self.scope_desc_label.setWordWrap(True)

        self.scope_layout.addLayout(scope_row)
        self.scope_layout.addWidget(self.scope_desc_label)
        self.main_layout.addLayout(self.scope_layout)
        self.main_layout.addSpacing(8)

    def setup_status_layout(self):
        self.status_layout = QVBoxLayout()
        self.status_layout.setContentsMargins(50, 0, 30, 5)
        self.status_layout.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)  # type: ignore
        self.status_label = BodyLabel(self.tr("准备就绪"), self)
        self.status_label.setStyleSheet("font-size: 14px; color: #888888;")
        self.status_layout.addWidget(self.status_label, 0, Qt.AlignCenter)  # type: ignore
        self.progress_bar = ProgressBar(self)
        self.status_label.hide()
        self.progress_bar.hide()
        self.progress_bar.setFixedWidth(300)
        self.status_layout.addWidget(self.progress_bar, 0, Qt.AlignCenter)  # type: ignore

        self.main_layout.addStretch(2)
        self.main_layout.addLayout(self.status_layout)

    def setup_info_label(self):
        # 创建底部容器
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        link_style = """
            QPushButton {
                font-size: 12px;
                color: #2F8D63;
                text-decoration: underline;
            }
        """

        # 打开工作目录：下载/产物默认保存在此
        self.open_work_dir_button = HyperlinkButton(
            url="", text=self.tr("打开工作目录"), parent=self
        )
        self.open_work_dir_button.setStyleSheet(
            self.open_work_dir_button.styleSheet() + link_style
        )
        self.open_work_dir_button.setToolTip(
            self.tr("打开下载与处理产物所在的工作目录（可在设置中修改）")
        )

        # 创建日志按钮
        self.log_button = HyperlinkButton(url="", text=self.tr("查看日志"), parent=self)
        self.log_button.setStyleSheet(self.log_button.styleSheet() + link_style)

        # 添加版权信息标签
        self.info_label = BodyLabel(f"{APP_NAME} {VERSION} · GPL-3.0", self)
        self.info_label.setAlignment(Qt.AlignCenter)  # type: ignore
        self.info_label.setStyleSheet("font-size: 12px; color: #888888;")

        # 将组件添加到底部布局
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.info_label)
        bottom_layout.addWidget(self.open_work_dir_button)
        bottom_layout.addWidget(self.log_button)
        bottom_layout.addStretch()

        # 底部操作区紧贴窗口下沿，避免再被 stretch 顶出可视区域
        self.main_layout.addSpacing(8)
        self.main_layout.addWidget(bottom_container)

    def setup_signals(self):
        self.start_button.clicked.connect(self.on_start_clicked)
        self.paste_button.clicked.connect(self.paste_from_clipboard)
        self.search_input.textChanged.connect(self.on_search_input_changed)
        self.batch_url_button.clicked.connect(self.open_batch_url_dialog)
        self.open_work_dir_button.clicked.connect(self.open_work_directory)
        self.log_button.clicked.connect(self.show_log_window)
        self.pipeline_scope_combo.currentIndexChanged.connect(
            self.on_pipeline_scope_changed
        )

    def setup_values(self):
        self.search_input.setText("")
        current_scope = cfg.get(cfg.pipeline_scope)
        index = self.pipeline_scope_combo.findData(current_scope)
        if index < 0:
            index = self.pipeline_scope_combo.findData(PipelineScope.FULL)
        self.pipeline_scope_combo.setCurrentIndex(max(index, 0))
        self._update_scope_description()

    def on_pipeline_scope_changed(self, _index: int = 0):
        scope = self.pipeline_scope_combo.currentData()
        if isinstance(scope, PipelineScope):
            cfg.set(cfg.pipeline_scope, scope)
        self._update_scope_description()

    def _update_scope_description(self):
        scope = self.pipeline_scope_combo.currentData()
        if not isinstance(scope, PipelineScope):
            scope = PipelineScope.FULL
        self.scope_desc_label.setText(
            self.pipeline_scope_descriptions.get(scope, "")
        )

    def current_pipeline_scope(self) -> PipelineScope:
        scope = self.pipeline_scope_combo.currentData()
        if isinstance(scope, PipelineScope):
            return scope
        return cfg.get(cfg.pipeline_scope)

    @staticmethod
    def normalize_user_input(value: str) -> str:
        """Trim copied text and extract the first URL from share messages."""
        urls = extract_urls(value)
        if urls:
            return urls[0]
        return value.strip()

    def open_batch_url_dialog(self):
        """打开批量链接下载对话框（仅下载，不进入后续流水线）。"""
        cookiefile_path = APPDATA_PATH / "cookies.txt"
        if not cookiefile_path.exists():
            InfoBar.warning(
                self.tr("警告"),
                self.tr("建议根据文档配置 cookies.txt，以便下载高清视频"),
                duration=INFOBAR_DURATION_WARNING,
                parent=self,
            )

        dialog = BatchUrlDialog(str(cfg.get(cfg.work_dir)), self.window())
        # 预填：若单行输入已是链接，带入对话框方便追加
        current = self.search_input.text().strip()
        if current and extract_urls(current):
            dialog.url_edit.setPlainText(current)
        dialog.batch_completed.connect(self._on_batch_download_completed)
        dialog.exec_()

    def _on_batch_download_completed(self, success: int, fail: int, paths: list):
        if success <= 0:
            return
        self.status_label.show()
        self.status_label.setText(
            self.tr("批量下载完成：成功 {ok}，失败 {fail}").format(
                ok=success, fail=fail
            )
        )
        InfoBar.success(
            self.tr("批量下载完成"),
            self.tr("成功 {ok} 个，可点击「打开工作目录」查看").format(ok=success),
            duration=INFOBAR_DURATION_SUCCESS,
            position=InfoBarPosition.BOTTOM,
            parent=self.window(),
        )

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        value = self.normalize_user_input(clipboard.text())
        if value:
            self.search_input.setText(value)
            self.search_input.setFocus()

    def on_start_clicked(self):
        if self.start_button._icon == FluentIcon.FOLDER:
            desktop_path = QStandardPaths.writableLocation(
                QStandardPaths.DesktopLocation
            )
            file_dialog = QFileDialog()

            # 构建文件过滤器
            video_formats = " ".join(f"*.{fmt.value}" for fmt in SupportedVideoFormats)
            audio_formats = " ".join(f"*.{fmt.value}" for fmt in SupportedAudioFormats)
            filter_str = f"{self.tr('媒体文件')} ({video_formats} {audio_formats});;{self.tr('视频文件')} ({video_formats});;{self.tr('音频文件')} ({audio_formats})"

            file_path, _ = file_dialog.getOpenFileName(
                self, self.tr("选择媒体文件"), desktop_path, filter_str
            )
            if file_path:
                self.search_input.setText(file_path)
            return

        self.process()

    def on_search_input_changed(self):
        if self.search_input.text():
            self.start_button.setIcon(FluentIcon.PLAY)
        else:
            self.start_button.setIcon(FluentIcon.FOLDER)

    def dragEnterEvent(self, event):
        event.accept() if event.mimeData().hasUrls() else event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file_path in files:
            if not os.path.isfile(file_path):
                continue

            file_ext = os.path.splitext(file_path)[1][1:].lower()

            # 检查文件格式是否支持
            supported_formats = {fmt.value for fmt in SupportedVideoFormats} | {
                fmt.value for fmt in SupportedAudioFormats
            }
            is_supported = file_ext in supported_formats

            if is_supported:
                self.search_input.setText(file_path)
                self.status_label.setText(self.tr("导入成功"))
                InfoBar.success(
                    self.tr("导入成功"),
                    self.tr("导入媒体文件成功"),
                    duration=INFOBAR_DURATION_SUCCESS,
                    parent=self,
                )
                break
            else:
                InfoBar.error(
                    self.tr("格式错误") + file_ext,
                    self.tr("不支持该文件格式"),
                    duration=INFOBAR_DURATION_ERROR,
                    parent=self,
                )

    def create_task(self):
        search_input = self.normalize_user_input(self.search_input.text())
        self.search_input.setText(search_input)
        if os.path.isfile(search_input):
            self._process_file(search_input)
        elif self._is_valid_url(search_input):
            self._process_url(search_input)
        else:
            InfoBar.error(
                self.tr("错误"),
                self.tr("请输入有效的文件路径或视频URL"),
                duration=INFOBAR_DURATION_ERROR,
                parent=self,
            )

    def _is_valid_url(self, url):
        try:
            result = urlparse(url)
            return result.scheme in ("http", "https") and bool(result.netloc)
        except ValueError:
            return False

    def _process_file(self, file_path):
        self.finished.emit(file_path)

    def _process_url(self, url):
        # 检测 cookies.txt 文件
        cookiefile_path = APPDATA_PATH / "cookies.txt"
        if not cookiefile_path.exists():
            InfoBar.warning(
                self.tr("警告"),
                self.tr("建议根据文档配置cookies.txt文件，以可以下载高清视频"),
                duration=INFOBAR_DURATION_WARNING,
                parent=self,
            )

        # 创建视频下载线程
        self.video_download_thread = VideoDownloadThread(url, str(cfg.work_dir.value))
        self.video_download_thread.finished.connect(self.on_video_download_finished)
        self.video_download_thread.progress.connect(self.on_create_task_progress)
        self.video_download_thread.error.connect(self.on_create_task_error)
        self.video_download_thread.start()

        InfoBar.info(
            self.tr("开始下载"),
            self.tr("开始下载视频..."),
            duration=INFOBAR_DURATION_INFO,
            parent=self,
        )

    def on_video_download_finished(self, video_file_path):
        """视频下载完成的回调函数"""
        if video_file_path:
            self.finished.emit(video_file_path)
            # 仅获取视频时由 HomeInterface 统一提示“到站即停”
            if self.current_pipeline_scope() != PipelineScope.ACQUIRE_ONLY:
                InfoBar.success(
                    self.tr("下载成功"),
                    self.tr("视频下载完成，开始自动处理..."),
                    duration=INFOBAR_DURATION_SUCCESS,
                    position=InfoBarPosition.BOTTOM,
                    parent=self.parent(),
                )
        else:
            InfoBar.error(
                self.tr("错误"),
                self.tr("视频下载失败"),
                duration=INFOBAR_DURATION_ERROR,
                parent=self,
            )

    def on_create_task_progress(self, value, status):
        self.progress_bar.show()
        self.status_label.show()
        self.progress_bar.setValue(value)
        self.status_label.setText(status)

    def on_create_task_error(self, error):
        InfoBar.error(
            self.tr("错误"),
            self.tr(error),
            duration=INFOBAR_DURATION_ERROR,
            parent=self,
        )

    def set_task(self, task):
        self.task = task
        self.update_info()

    def update_info(self):
        if self.task:
            self.search_input.setText(self.task.file_path)

    def process(self):
        search_input = self.normalize_user_input(self.search_input.text())
        self.search_input.setText(search_input)

        if os.path.isfile(search_input):
            self._process_file(search_input)
        elif self._is_valid_url(search_input):
            self._process_url(search_input)
        else:
            InfoBar.error(
                self.tr("错误"),
                self.tr("请输入音视频文件路径或URL"),
                duration=INFOBAR_DURATION_ERROR,
                parent=self,
            )

    def open_work_directory(self):
        """打开工作目录（下载与处理产物默认保存位置）。"""
        work_dir = str(cfg.get(cfg.work_dir))
        if os.path.isdir(work_dir):
            open_folder(work_dir)
            return
        InfoBar.warning(
            self.tr("工作目录不存在"),
            self.tr("请先在设置中配置有效的工作目录"),
            duration=INFOBAR_DURATION_WARNING,
            parent=self,
        )

    def show_log_window(self):
        """显示日志窗口"""
        if self.log_window is None:
            self.log_window = LogWindow()
        if self.log_window.isHidden():
            self.log_window.show()
        else:
            self.log_window.activateWindow()

if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)  # type: ignore
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)  # type: ignore

    app = QApplication(sys.argv)
    window = TaskCreationInterface()
    window.show()
    sys.exit(app.exec_())
