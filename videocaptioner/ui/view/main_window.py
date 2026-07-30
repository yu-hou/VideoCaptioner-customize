import atexit
import os
import shutil
import sys

import psutil
from PyQt5.QtCore import QSize, QThread, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices, QIcon, QKeySequence
from PyQt5.QtWidgets import QAction, QApplication, QMenuBar
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import (
    FluentWindow,
    InfoBar,
    InfoBarPosition,
    MessageBox,
    NavigationItemPosition,
    SplashScreen,
)

from videocaptioner.config import (
    APP_DISPLAY_NAME,
    ASSETS_PATH,
    GITHUB_REPO_URL,
    UPSTREAM_PROJECT_URL,
)
from videocaptioner.core.constant import INFOBAR_DURATION_FOREVER
from videocaptioner.ui.common.config import cfg
from videocaptioner.ui.components.FirstRunWizard import FirstRunWizard
from videocaptioner.ui.thread.version_checker_thread import VersionChecker
from videocaptioner.ui.view.batch_process_interface import BatchProcessInterface
from videocaptioner.ui.view.home_interface import HomeInterface
from videocaptioner.ui.view.llm_logs_interface import LLMLogsInterface
from videocaptioner.ui.view.setting_interface import SettingInterface
from videocaptioner.ui.view.subtitle_style_interface import SubtitleStyleInterface
from videocaptioner.ui.view.user_guide_interface import UserGuideInterface

LOGO_PATH = ASSETS_PATH / "logo.png"


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.initWindow()
        self._init_macos_edit_menu()

        # 创建子界面
        self.homeInterface = HomeInterface(self)
        self.settingInterface = SettingInterface(self)
        self.subtitleStyleInterface = SubtitleStyleInterface(self)
        self.batchProcessInterface = BatchProcessInterface(self)
        self.llmLogsInterface = LLMLogsInterface(self)
        self.userGuideInterface = UserGuideInterface(self)
        self.userGuideInterface.restartWizardRequested.connect(
            self._show_first_run_wizard
        )
        self.userGuideInterface.openHomeRequested.connect(
            lambda: self.switchTo(self.homeInterface)
        )
        self.userGuideInterface.openSettingsRequested.connect(
            lambda: self.switchTo(self.settingInterface)
        )

        # 初始化版本检查器
        self.versionChecker = VersionChecker()
        self.versionChecker.newVersionAvailable.connect(self.onNewVersion)
        self.versionChecker.announcementAvailable.connect(self.onAnnouncement)

        self.versionThread = QThread()
        self.versionChecker.moveToThread(self.versionThread)
        self.versionThread.started.connect(self.versionChecker.perform_check)
        self.versionThread.start()

        # 初始化导航界面
        self.initNavigation()
        self.splashScreen.finish()

        # 检查系统依赖
        self._check_ffmpeg()

        if not cfg.get(cfg.first_run_completed):
            QTimer.singleShot(0, self._show_first_run_wizard)

        # 注册退出处理， 清理进程
        atexit.register(self.stop)

    def _init_macos_edit_menu(self):
        """Provide the standard native Edit menu expected by macOS users."""
        if sys.platform != "darwin":
            return

        # FluentWindow inherits QWidget rather than QMainWindow, so it has no
        # menuBar() helper. A parented native QMenuBar is enough for macOS to
        # expose the standard application Edit menu.
        self._mac_menu_bar = QMenuBar(self)
        self._mac_menu_bar.setNativeMenuBar(True)
        edit_menu = self._mac_menu_bar.addMenu(self.tr("编辑"))
        actions = (
            (self.tr("撤销"), QKeySequence.Undo, "undo"),
            (self.tr("重做"), QKeySequence.Redo, "redo"),
            (None, None, None),
            (self.tr("剪切"), QKeySequence.Cut, "cut"),
            (self.tr("复制"), QKeySequence.Copy, "copy"),
            (self.tr("粘贴"), QKeySequence.Paste, "paste"),
            (self.tr("全选"), QKeySequence.SelectAll, "selectAll"),
        )
        self._mac_edit_actions = []
        for text, shortcut, method_name in actions:
            if text is None:
                edit_menu.addSeparator()
                continue
            action = QAction(text, self)
            action.setShortcut(shortcut)
            action.setMenuRole(QAction.NoRole)
            action.triggered.connect(
                lambda checked=False, name=method_name: self._invoke_focused_edit(name)
            )
            edit_menu.addAction(action)
            self._mac_edit_actions.append(action)

    @staticmethod
    def _invoke_focused_edit(method_name):
        focused = QApplication.focusWidget()
        method = getattr(focused, method_name, None)
        if callable(method) and focused.isEnabled():
            method()

    def initNavigation(self):
        """初始化导航栏"""
        # 添加导航项
        self.addSubInterface(self.homeInterface, FIF.HOME, self.tr("主页"))
        self.addSubInterface(self.batchProcessInterface, FIF.VIDEO, self.tr("批量处理"))
        self.addSubInterface(self.subtitleStyleInterface, FIF.FONT, self.tr("字幕样式"))
        self.addSubInterface(self.llmLogsInterface, FIF.HISTORY, self.tr("请求日志"))
        self.addSubInterface(self.userGuideInterface, FIF.HELP, self.tr("使用指南"))

        self.navigationInterface.addSeparator()

        # 在底部添加自定义小部件
        self.navigationInterface.addItem(
            routeKey="avatar",
            text="GitHub",
            icon=FIF.GITHUB,
            onClick=self.onGithubDialog,
            position=NavigationItemPosition.BOTTOM,
        )
        self.addSubInterface(
            self.settingInterface,
            FIF.SETTING,
            self.tr("Settings"),
            NavigationItemPosition.BOTTOM,
        )

        # 设置默认界面
        self.switchTo(self.homeInterface)

    def switchTo(self, interface):
        if interface.windowTitle():
            self.setWindowTitle(interface.windowTitle())
        else:
            self.setWindowTitle(APP_DISPLAY_NAME)
        self.stackedWidget.setCurrentWidget(interface, popOut=False)

    def initWindow(self):
        """初始化窗口"""
        self.resize(1050, 800)
        self.setMinimumWidth(700)
        self.setWindowIcon(QIcon(str(LOGO_PATH)))
        self.setWindowTitle(APP_DISPLAY_NAME)

        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        # 创建启动画面
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(106, 106))
        self.splashScreen.raise_()

        # 设置窗口位置, 居中
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        self.show()
        QApplication.processEvents()

    def onGithubDialog(self):
        """打开GitHub"""
        w = MessageBox(
            self.tr("项目信息"),
            self.tr(
                "NovaCaption 是基于开源项目 VideoCaptioner 的独立定制版本，"
                "并非上游作者发布或认可的官方商业版本。\n\n"
                f"当前项目：{GITHUB_REPO_URL}\n"
                f"上游项目：{UPSTREAM_PROJECT_URL}"
            ),
            self,
        )
        w.yesButton.setText(self.tr("打开项目主页"))
        w.cancelButton.setText(self.tr("关闭"))
        if w.exec():
            QDesktopServices.openUrl(QUrl(GITHUB_REPO_URL))

    def onNewVersion(self, version, update_required, update_info, download_url):
        """新版本提示"""
        if update_required:
            title = "发现新版本, 需要更新"
            content = f"发现新版本 {version}\n\n" f"更新内容：\n{update_info}"
        else:
            title = "发现新版本"
            content = f"发现新版本 {version}\n\n{update_info}"

        w = MessageBox(title, content, self)
        w.yesButton.setText("立即更新")
        w.cancelButton.setText("稍后再说")

        if w.exec() or update_required:
            QDesktopServices.openUrl(QUrl(download_url))

        if update_required:
            self.homeInterface.setEnabled(False)
            self.batchProcessInterface.setEnabled(False)
            InfoBar.error(
                title="需要更新",
                content=self.tr("当前版本部分功能已被禁用。请尽快更新。"),
                isClosable=False,
                position=InfoBarPosition.BOTTOM,
                duration=-1,
                parent=self,
            )

    def onAnnouncement(self, content):
        """显示公告"""
        w = MessageBox("公告", content, self)
        w.yesButton.setText("我知道了")
        w.cancelButton.hide()
        w.exec()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "splashScreen"):
            self.splashScreen.resize(self.size())

    def closeEvent(self, event):
        # 关闭所有子界面
        # self.homeInterface.close()
        # self.batchProcessInterface.close()
        # self.subtitleStyleInterface.close()
        # self.settingInterface.close()
        super().closeEvent(event)

        # 强制退出应用程序
        QApplication.quit()

        # 确保所有线程和进程都被终止 要是一些错误退出就不会处理了。
        # import os
        # os._exit(0)

    def stop(self):
        # 找到 FFmpeg 进程并关闭
        process = psutil.Process(os.getpid())
        for child in process.children(recursive=True):
            child.kill()

    def _check_ffmpeg(self):
        """检查 FFmpeg 是否已安装"""
        if shutil.which("ffmpeg") is None:
            InfoBar.warning(
                self.tr("FFmpeg 未安装"),
                self.tr("软件处理音视频文件时需要 FFmpeg，请先安装"),
                duration=INFOBAR_DURATION_FOREVER,
                position=InfoBarPosition.BOTTOM,
                parent=self,
            )

    def _show_first_run_wizard(self):
        """Show or reactivate the setup wizard."""
        existing = getattr(self, "firstRunWizard", None)
        if existing is not None and existing.isVisible():
            existing.raise_()
            existing.activateWindow()
            return
        self.firstRunWizard = FirstRunWizard(self)
        self.firstRunWizard.exec_()
