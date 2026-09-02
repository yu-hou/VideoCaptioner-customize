"""Background tasks for Chrome/Yuanbao cookie management."""

from PyQt5.QtCore import QThread, pyqtSignal

from videocaptioner.core.utils.douyin_cookie import ChromeProfile
from videocaptioner.core.utils.yuanbao_cookie import (
    export_yuanbao_cookies,
    test_yuanbao_cookie,
)


class YuanbaoCookieThread(QThread):
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
                count = export_yuanbao_cookies(self.profile)
                self.succeeded.emit(f"已安全保存 {count} 条腾讯元宝相关 Cookie")
                return
            if self.action == "test":
                title = test_yuanbao_cookie(self.test_url)
                self.succeeded.emit(f"Cookie 可用，已识别视频：{title}")
                return
            raise ValueError(f"未知的 Cookie 操作：{self.action}")
        except Exception as exc:
            self.failed.emit(str(exc))
