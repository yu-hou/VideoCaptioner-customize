"""Cookie setup cards for the Yuanbao-based WeChat Channels resolver."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

from PyQt5.QtCore import QCoreApplication, QProcess, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import (
    PrimaryPushSettingCard,
    PushSettingCard,
    SettingCard,
    SettingCardGroup,
)

from videocaptioner.core.utils.douyin_cookie import (
    ChromeProfile,
    list_chrome_profiles,
)
from videocaptioner.core.utils.yuanbao_cookie import get_yuanbao_cookie_status
from videocaptioner.ui.common.config import cfg
from videocaptioner.ui.components.DouyinCookieManager import (
    ChromeProfileCard,
    CookieTestUrlCard,
    _process_started,
)
from videocaptioner.ui.thread.yuanbao_cookie_thread import YuanbaoCookieThread

YUANBAO_LOGIN_URL = "https://yuanbao.tencent.com/"
DEFAULT_TEST_URL = "https://weixin.qq.com/sph/AtBrYj8dQb"


def _tr(text: str) -> str:
    return QCoreApplication.translate("YuanbaoCookieManager", text)


class YuanbaoCookieManager(SettingCardGroup):
    """Profile discovery, cookie import, and validation UI for Yuanbao."""

    busyChanged = pyqtSignal(bool)
    operationFinished = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(_tr("视频号 Cookie（腾讯元宝）"), parent)
        self.profiles: list[ChromeProfile] = []
        self.worker: YuanbaoCookieThread | None = None

        self.profileCard = ChromeProfileCard(
            self,
            content=self.tr("选择已经登录腾讯元宝的 Chrome Profile"),
        )
        self.loginCard = PushSettingCard(
            self.tr("打开腾讯元宝"),
            FIF.GLOBE,
            self.tr("登录腾讯元宝"),
            self.tr("请使用上方所选 Profile 登录腾讯元宝，并确认首页可以正常打开"),
            self,
        )
        self.importCard = PrimaryPushSettingCard(
            self.tr("读取 Cookie"),
            FIF.DOWNLOAD,
            self.tr("从 Chrome 读取腾讯元宝 Cookie"),
            self.tr("只保存腾讯元宝相关 Cookie，不会导出其他网站的登录信息"),
            self,
        )
        self.testUrlCard = CookieTestUrlCard(
            self,
            title=self.tr("测试视频号链接"),
            content=self.tr("支持 https://weixin.qq.com/sph/... 分享链接"),
            placeholder=DEFAULT_TEST_URL,
            config_item=cfg.yuanbao_test_url,
        )
        self.testCard = PushSettingCard(
            self.tr("测试 Cookie"),
            FIF.CONNECT,
            self.tr("验证视频号解析"),
            self.tr("用于确认腾讯元宝登录状态和视频号链接是否可用"),
            self,
        )
        self.statusCard = SettingCard(FIF.INFO, self.tr("当前状态"), "", self)

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
        self.loginCard.clicked.connect(self.open_yuanbao_login)
        self.importCard.clicked.connect(self.import_cookies)
        self.testCard.clicked.connect(self.test_cookies)
        self.refresh_profiles()
        self.refresh_status()

    def refresh_profiles(self):
        selected_name = str(cfg.get(cfg.yuanbao_chrome_profile))
        self.profiles = list_chrome_profiles()
        combo = self.profileCard.comboBox
        combo.blockSignals(True)
        combo.clear()
        for profile in self.profiles:
            combo.addItem(f"{profile.display_name} ({profile.directory_name})")
        selected_index = next(
            (
                index
                for index, profile in enumerate(self.profiles)
                if profile.directory_name == selected_name
            ),
            0,
        )
        if self.profiles:
            combo.setCurrentIndex(selected_index)
            cfg.set(
                cfg.yuanbao_chrome_profile,
                self.profiles[selected_index].directory_name,
            )
            self.profileCard.setContent(
                self.tr("已发现") + f" {len(self.profiles)} " + self.tr("个 Chrome Profile")
            )
        else:
            combo.addItem(self.tr("未发现 Chrome Profile"))
            self.profileCard.setContent(self.tr("请先安装并至少启动一次 Google Chrome"))
        combo.blockSignals(False)

    def _save_selected_profile(self, index: int):
        if 0 <= index < len(self.profiles):
            cfg.set(cfg.yuanbao_chrome_profile, self.profiles[index].directory_name)

    def selected_profile(self) -> ChromeProfile | None:
        index = self.profileCard.comboBox.currentIndex()
        return self.profiles[index] if 0 <= index < len(self.profiles) else None

    def open_yuanbao_login(self):
        profile = self.selected_profile()
        if not self._open_chrome(profile):
            QDesktopServices.openUrl(QUrl(YUANBAO_LOGIN_URL))
        self.statusCard.setContent(
            self.tr("请在 Chrome 中登录腾讯元宝，确认首页正常后再读取 Cookie")
        )

    def _open_chrome(self, profile: ChromeProfile | None) -> bool:
        profile_argument = (
            f"--profile-directory={profile.directory_name}" if profile else ""
        )
        system = platform.system()
        if system == "Darwin":
            candidates = [
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ]
            executable = next((str(path) for path in candidates if path.is_file()), "")
            if executable:
                args = [profile_argument] if profile_argument else []
                return _process_started(
                    QProcess.startDetached(executable, [*args, YUANBAO_LOGIN_URL])
                )
            args = ["-a", "Google Chrome", "--args"]
            if profile_argument:
                args.append(profile_argument)
            args.append(YUANBAO_LOGIN_URL)
            return _process_started(QProcess.startDetached("open", args))
        if system == "Windows":
            candidates = [
                Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
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
        args = [profile_argument] if profile_argument else []
        return _process_started(QProcess.startDetached(executable, [*args, YUANBAO_LOGIN_URL]))

    def refresh_status(self):
        status = get_yuanbao_cookie_status()
        if not status.exists or status.cookie_count == 0:
            self.statusCard.setContent(self.tr("尚未配置有效的腾讯元宝 Cookie"))
            return
        updated_at = (
            status.updated_at.strftime("%Y-%m-%d %H:%M")
            if status.updated_at
            else self.tr("未知")
        )
        self.statusCard.setContent(
            self.tr("已保存")
            + f" {status.cookie_count} "
            + self.tr("条腾讯元宝 Cookie，更新时间：")
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
            self._finish_operation(False, self.tr("请先粘贴一个视频号分享链接"))
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
            else self.tr("正在验证视频号链接和 Cookie...")
        )
        self.worker = YuanbaoCookieThread(
            action, profile=profile, test_url=test_url, parent=self
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
