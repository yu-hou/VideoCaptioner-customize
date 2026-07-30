"""Background tasks for Chrome/Douyin cookie management."""

from PyQt5.QtCore import QThread, pyqtSignal

from videocaptioner.core.utils.douyin_cookie import (
    ChromeProfile,
    export_douyin_cookies,
    test_douyin_cookie,
)


class DouyinCookieThread(QThread):
    """Export or validate Douyin cookies without blocking the UI."""

    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        action: str,
        profile: ChromeProfile | None = None,
        test_url: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.action = action
        self.profile = profile
        self.test_url = test_url

    def run(self):
        try:
            if self.action == "export":
                if self.profile is None:
                    raise ValueError("请先选择 Chrome Profile")
                count = export_douyin_cookies(self.profile)
                self.succeeded.emit(f"已安全保存 {count} 条抖音相关 Cookie")
                return

            if self.action == "test":
                title = test_douyin_cookie(self.test_url)
                self.succeeded.emit(f"Cookie 可用，已识别视频：{title}")
                return

            raise ValueError(f"未知的 Cookie 操作：{self.action}")
        except Exception as exc:
            self.failed.emit(str(exc))
