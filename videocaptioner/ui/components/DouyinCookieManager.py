"""Reusable Douyin cookie management cards."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

from PyQt5.QtCore import QCoreApplication, QProcess, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from qfluentwidgets import (
    ComboBox,
    LineEdit,
    PrimaryPushSettingCard,
    PushButton,
    PushSettingCard,
    SettingCard,
    SettingCardGroup,
)
from qfluentwidgets import FluentIcon as FIF

from videocaptioner.core.utils.douyin_cookie import (
    ChromeProfile,
    get_douyin_cookie_status,
    list_chrome_profiles,
)
from videocaptioner.ui.common.config import cfg
from videocaptioner.ui.thread.douyin_cookie_thread import DouyinCookieThread

DOUYIN_LOGIN_URL = "https://www.douyin.com/"


def _tr(text: str) -> str:
    return QCoreApplication.translate("DouyinCookieManager", text)


def _process_started(result) -> bool:
    return bool(result[0]) if isinstance(result, tuple) else bool(result)


class ChromeProfileCard(SettingCard):
    """Chrome profile selector with refresh action."""

    refreshClicked = pyqtSignal()
    profileChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(
            FIF.PEOPLE,
            _tr("Chrome 用户"),
            _tr("选择已经登录并能正常播放抖音视频的 Chrome Profile"),
            parent,
        )
        self.comboBox = ComboBox(self)
        self.comboBox.setMinimumWidth(180)
        self.refreshButton = PushButton(_tr("刷新"), self)
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignRight)  # type: ignore
        self.hBoxLayout.addSpacing(8)
        self.hBoxLayout.addWidget(self.refreshButton, 0, Qt.AlignRight)  # type: ignore
        self.hBoxLayout.addSpacing(16)

        self.refreshButton.clicked.connect(self.refreshClicked)
        self.comboBox.currentIndexChanged.connect(self.profileChanged)


class CookieTestUrlCard(SettingCard):
    """Input card for the Douyin URL used by the cookie check."""

    def __init__(self, parent=None):
        super().__init__(
            FIF.LINK,
            _tr("测试视频"),
            _tr("支持普通抖音链接和带 modal_id 的抖音精选链接"),
            parent,
        )
        self.lineEdit = LineEdit(self)
        self.lineEdit.setMinimumWidth(330)
        self.lineEdit.setPlaceholderText(
            "https://www.douyin.com/video/... 或 /jingxuan?modal_id=..."
        )
        self.lineEdit.setText(str(cfg.get(cfg.douyin_test_url)))
        self.hBoxLayout.addWidget(self.lineEdit, 1, Qt.AlignRight)  # type: ignore
        self.hBoxLayout.addSpacing(16)
        self.lineEdit.textChanged.connect(
            lambda value: cfg.set(cfg.douyin_test_url, value)
        )


class DouyinCookieManager(SettingCardGroup):
    """Profile discovery, cookie import, and validation UI."""

    busyChanged = pyqtSignal(bool)
    operationFinished = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(_tr("抖音 Cookie"), parent)
        self.profiles: list[ChromeProfile] = []
        self.worker: DouyinCookieThread | None = None

        self.profileCard = ChromeProfileCard(self)
        self.loginCard = PushSettingCard(
            self.tr("打开抖音"),
            FIF.GLOBE,
            self.tr("登录并完成验证"),
            self.tr("请使用上方所选 Profile 登录抖音，并确认视频可以正常播放"),
            self,
        )
        self.importCard = PrimaryPushSettingCard(
            self.tr("读取 Cookie"),
            FIF.DOWNLOAD,
            self.tr("从 Chrome 读取抖音 Cookie"),
            self.tr("只保存抖音相关 Cookie，不会导出其他网站的登录信息"),
            self,
        )
        self.testUrlCard = CookieTestUrlCard(self)
        self.testCard = PushSettingCard(
            self.tr("测试 Cookie"),
            FIF.CONNECT,
            self.tr("验证抖音下载"),
            self.tr("读取视频信息但不下载，用于确认 Cookie 和链接是否可用"),
            self,
        )
        self.statusCard = SettingCard(
            FIF.INFO,
            self.tr("当前状态"),
            "",
            self,
        )

        for card in (
            self.profileCard,
            self.loginCard,
            self.importCard,
            self.testUrlCard,
            self.testCard,
            self.statusCard,
        ):
            self.addSettingCard(card)

        self.profileCard.refreshClicked.connect(self.refresh_profiles)
        self.profileCard.profileChanged.connect(self._save_selected_profile)
        self.loginCard.clicked.connect(self.open_douyin_login)
        self.importCard.clicked.connect(self.import_cookies)
        self.testCard.clicked.connect(self.test_cookies)

        self.refresh_profiles()
        self.refresh_status()

    def refresh_profiles(self):
        selected_name = str(cfg.get(cfg.douyin_chrome_profile))
        self.profiles = list_chrome_profiles()
        self.profileCard.comboBox.blockSignals(True)
        self.profileCard.comboBox.clear()
        for profile in self.profiles:
            label = f"{profile.display_name} ({profile.directory_name})"
            self.profileCard.comboBox.addItem(label)

        selected_index = 0
        for index, profile in enumerate(self.profiles):
            if profile.directory_name == selected_name:
                selected_index = index
                break
        if self.profiles:
            self.profileCard.comboBox.setCurrentIndex(selected_index)
            cfg.set(
                cfg.douyin_chrome_profile,
                self.profiles[selected_index].directory_name,
            )
            self.profileCard.setContent(
                self.tr("已发现")
                + f" {len(self.profiles)} "
                + self.tr("个 Chrome Profile")
            )
        else:
            self.profileCard.comboBox.addItem(self.tr("未发现 Chrome Profile"))
            self.profileCard.setContent(
                self.tr("请先安装并至少启动一次 Google Chrome")
            )
        self.profileCard.comboBox.blockSignals(False)

    def _save_selected_profile(self, index: int):
        if 0 <= index < len(self.profiles):
            cfg.set(cfg.douyin_chrome_profile, self.profiles[index].directory_name)

    def selected_profile(self) -> ChromeProfile | None:
        index = self.profileCard.comboBox.currentIndex()
        return self.profiles[index] if 0 <= index < len(self.profiles) else None

    def open_douyin_login(self):
        profile = self.selected_profile()
        opened = self._open_chrome(profile)
        if not opened:
            QDesktopServices.openUrl(QUrl(DOUYIN_LOGIN_URL))
        self.statusCard.setContent(
            self.tr("请在 Chrome 中完成登录或人机验证，确认视频可以播放后再读取 Cookie")
        )

    def _open_chrome(self, profile: ChromeProfile | None) -> bool:
        profile_argument = (
            f"--profile-directory={profile.directory_name}" if profile else ""
        )
        system = platform.system()
        if system == "Darwin":
            chrome_candidates = [
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path.home()
                / "Applications"
                / "Google Chrome.app"
                / "Contents"
                / "MacOS"
                / "Google Chrome",
            ]
            executable = next(
                (str(path) for path in chrome_candidates if path.is_file()),
                "",
            )
            if executable:
                arguments = [profile_argument] if profile_argument else []
                arguments.append(DOUYIN_LOGIN_URL)
                return _process_started(QProcess.startDetached(executable, arguments))

            arguments = ["-a", "Google Chrome", "--args"]
            if profile_argument:
                arguments.append(profile_argument)
            arguments.append(DOUYIN_LOGIN_URL)
            return _process_started(QProcess.startDetached("open", arguments))

        if system == "Windows":
            candidates = [
                Path(os.environ.get("LOCALAPPDATA", ""))
                / "Google"
                / "Chrome"
                / "Application"
                / "chrome.exe",
                Path(os.environ.get("PROGRAMFILES", ""))
                / "Google"
                / "Chrome"
                / "Application"
                / "chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", ""))
                / "Google"
                / "Chrome"
                / "Application"
                / "chrome.exe",
            ]
            executable = next((str(path) for path in candidates if path.is_file()), "")
        else:
            executable = (
                shutil.which("google-chrome")
                or shutil.which("google-chrome-stable")
                or shutil.which("chromium")
                or ""
            )

        if not executable:
            return False
        arguments = [profile_argument] if profile_argument else []
        arguments.append(DOUYIN_LOGIN_URL)
        return _process_started(QProcess.startDetached(executable, arguments))

    def refresh_status(self):
        status = get_douyin_cookie_status()
        if not status.exists or status.cookie_count == 0:
            self.statusCard.setContent(self.tr("尚未配置有效的抖音 Cookie"))
            return
        updated_at = (
            status.updated_at.strftime("%Y-%m-%d %H:%M")
            if status.updated_at
            else self.tr("未知")
        )
        self.statusCard.setContent(
            self.tr("已保存")
            + f" {status.cookie_count} "
            + self.tr("条抖音 Cookie，更新时间：")
            + updated_at
        )

    def import_cookies(self):
        profile = self.selected_profile()
        if profile is None:
            self._finish_operation(False, self.tr("没有可用的 Chrome Profile"))
            return
        self._start_worker("export", profile=profile)

    def test_cookies(self):
        test_url = self.testUrlCard.lineEdit.text().strip()
        if not test_url:
            self._finish_operation(False, self.tr("请先粘贴一个抖音视频链接"))
            return
        self._start_worker("test", test_url=test_url)

    def _start_worker(
        self,
        action: str,
        profile: ChromeProfile | None = None,
        test_url: str = "",
    ):
        if self.worker is not None and self.worker.isRunning():
            return

        self._set_busy(True)
        self.statusCard.setContent(
            self.tr("正在读取 Chrome Cookie...")
            if action == "export"
            else self.tr("正在验证抖音链接和 Cookie...")
        )
        self.worker = DouyinCookieThread(
            action,
            profile=profile,
            test_url=test_url,
            parent=self,
        )
        self.worker.succeeded.connect(lambda message: self._finish_operation(True, message))
        self.worker.failed.connect(lambda message: self._finish_operation(False, message))
        self.worker.finished.connect(self._worker_stopped)
        self.worker.start()

    def _set_busy(self, busy: bool):
        for button in (
            self.profileCard.refreshButton,
            self.loginCard.button,
            self.importCard.button,
            self.testCard.button,
        ):
            button.setEnabled(not busy)
        self.busyChanged.emit(busy)

    def _finish_operation(self, success: bool, message: str):
        self.statusCard.setContent(message)
        if success and self.worker is not None and self.worker.action == "export":
            self.refresh_status()
        self.operationFinished.emit(success, message)

    def _worker_stopped(self):
        worker = self.worker
        self.worker = None
        self._set_busy(False)
        if worker is not None:
            worker.deleteLater()
