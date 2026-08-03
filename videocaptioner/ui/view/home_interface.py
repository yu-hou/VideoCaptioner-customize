import os
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import QSizePolicy, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition, PushButton, SegmentedWidget

from videocaptioner.core.constant import INFOBAR_DURATION_ERROR
from videocaptioner.core.entities import PipelineScope
from videocaptioner.core.llm.context import generate_task_id
from videocaptioner.core.utils.platform_utils import open_folder, reveal_in_explorer
from videocaptioner.ui.common.config import cfg
from videocaptioner.ui.task_factory import TaskFactory
from videocaptioner.ui.view.subtitle_interface import SubtitleInterface
from videocaptioner.ui.view.task_creation_interface import TaskCreationInterface
from videocaptioner.ui.view.transcription_interface import TranscriptionInterface
from videocaptioner.ui.view.video_synthesis_interface import VideoSynthesisInterface


class HomeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_task_id: Optional[str] = None  # 当前流程的任务 ID

        # 设置对象名称和样式
        self.setObjectName("HomeInterface")
        self.setStyleSheet(
            """
            HomeInterface{background: white}
        """
        )

        # 创建分段控件和堆叠控件
        self.pivot = SegmentedWidget(self)
        self.pivot.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)

        # 添加子界面
        self.task_creation_interface = TaskCreationInterface(self)
        self.transcription_interface = TranscriptionInterface(self)
        self.subtitle_optimization_interface = SubtitleInterface(self)
        self.video_synthesis_interface = VideoSynthesisInterface(self)

        self.addSubInterface(
            self.task_creation_interface, "TaskCreationInterface", self.tr("任务创建")
        )
        self.addSubInterface(
            self.transcription_interface, "TranscriptionInterface", self.tr("语音转录")
        )
        self.addSubInterface(
            self.subtitle_optimization_interface,
            "SubtitleInterface",
            self.tr("字幕优化与翻译"),
        )
        self.addSubInterface(
            self.video_synthesis_interface,
            "VideoSynthesisInterface",
            self.tr("字幕视频合成"),
        )

        self.vBoxLayout.addWidget(self.pivot)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setContentsMargins(30, 10, 30, 30)

        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)
        self.stackedWidget.setCurrentWidget(self.task_creation_interface)
        self.pivot.setCurrentItem("TaskCreationInterface")

        self.task_creation_interface.finished.connect(self.switch_to_transcription)
        self.transcription_interface.finished.connect(
            self.switch_to_subtitle_optimization
        )
        self.subtitle_optimization_interface.finished.connect(
            self.switch_to_video_synthesis
        )

    def _current_pipeline_scope(self) -> PipelineScope:
        scope = cfg.get(cfg.pipeline_scope)
        if isinstance(scope, PipelineScope):
            return scope
        return PipelineScope.FULL

    def _open_acquired_file_location(self, file_path: str) -> None:
        """在文件管理器中打开已获取文件所在位置。"""
        path = Path(file_path)
        if path.is_file():
            reveal_in_explorer(str(path))
            return
        if path.is_dir():
            open_folder(str(path))
            return
        parent = path.parent
        if parent.is_dir():
            open_folder(str(parent))
            return
        work_dir = str(cfg.get(cfg.work_dir))
        if os.path.isdir(work_dir):
            open_folder(work_dir)

    def _show_acquire_only_ready(self, file_path: str) -> None:
        """仅获取视频：提示保存位置，并提供打开所在文件夹入口。"""
        display_path = str(file_path)
        bar = InfoBar.success(
            self.tr("已获取视频"),
            self.tr("文件已就绪（未开始转录）\n保存位置：{path}").format(
                path=display_path
            ),
            duration=INFOBAR_DURATION_ERROR,  # 留足时间点击「打开所在文件夹」
            position=InfoBarPosition.BOTTOM,
            parent=self.window(),
        )
        open_btn = PushButton(self.tr("打开所在文件夹"), bar)
        open_btn.clicked.connect(
            lambda: self._open_acquired_file_location(file_path)
        )
        bar.addWidget(open_btn)

    def switch_to_transcription(self, file_path):
        scope = self._current_pipeline_scope()
        if scope == PipelineScope.ACQUIRE_ONLY:
            self._current_task_id = None
            self._show_acquire_only_ready(file_path)
            return

        # 流程开始，生成新的 task_id
        self._current_task_id = generate_task_id()

        transcribe_task = TaskFactory.create_transcribe_task(
            file_path,
            need_next_task=scope.continues_after_transcribe,
            task_id=self._current_task_id,
        )
        self.transcription_interface.set_task(transcribe_task)
        self.transcription_interface.process()
        self.stackedWidget.setCurrentWidget(self.transcription_interface)
        self.pivot.setCurrentItem("TranscriptionInterface")

    def switch_to_subtitle_optimization(self, file_path, video_path):
        scope = self._current_pipeline_scope()
        # 继续使用同一个 task_id
        subtitle_task = TaskFactory.create_subtitle_task(
            file_path,
            video_path,
            need_next_task=scope.continues_after_subtitle,
            task_id=self._current_task_id,
        )
        self.subtitle_optimization_interface.set_task(subtitle_task)
        self.subtitle_optimization_interface.process()
        self.stackedWidget.setCurrentWidget(self.subtitle_optimization_interface)
        self.pivot.setCurrentItem("SubtitleInterface")

    def switch_to_video_synthesis(self, video_path, subtitle_path):
        # 继续使用同一个 task_id，流程结束后清空
        synthesis_task = TaskFactory.create_synthesis_task(
            video_path, subtitle_path, need_next_task=True, task_id=self._current_task_id
        )
        self._current_task_id = None  # 流程结束
        self.video_synthesis_interface.set_task(synthesis_task)
        self.video_synthesis_interface.process()
        self.stackedWidget.setCurrentWidget(self.video_synthesis_interface)
        self.pivot.setCurrentItem("VideoSynthesisInterface")

    def addSubInterface(self, widget, objectName, text):
        # 添加子界面到堆叠控件和分段控件
        widget.setObjectName(objectName)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(
            routeKey=objectName,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget),
        )

    def onCurrentIndexChanged(self, index):
        # 当堆叠控件的当前索引改变时，更新分段控件的当前项
        widget = self.stackedWidget.widget(index)
        if widget:
            self.pivot.setCurrentItem(widget.objectName())

    def closeEvent(self, event):
        # 关闭事件，关闭所有子界面
        self.task_creation_interface.close()
        self.transcription_interface.close()
        self.subtitle_optimization_interface.close()
        self.video_synthesis_interface.close()
        super().closeEvent(event)
