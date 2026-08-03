"""串行批量下载多个视频链接。"""

from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import QThread, pyqtSignal

from videocaptioner.core.utils.logger import setup_logger
from videocaptioner.ui.thread.video_download_thread import VideoDownloadThread

logger = setup_logger("batch_download_thread")


class BatchDownloadThread(QThread):
    """按顺序下载多个 URL，单条失败不中断整队。"""

    item_started = pyqtSignal(int, int, str)  # index, total, url
    item_progress = pyqtSignal(int, int, str)  # index, percent, message
    item_finished = pyqtSignal(int, str, str)  # index, url, path
    item_error = pyqtSignal(int, str, str)  # index, url, error
    batch_finished = pyqtSignal(int, int, list)  # success, fail, paths

    def __init__(self, urls: List[str], work_dir: str, parent=None):
        super().__init__(parent)
        self.urls = list(urls)
        self.work_dir = work_dir
        self._cancelled = False
        self._current_worker: Optional[VideoDownloadThread] = None

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        success = 0
        fail = 0
        paths: list[str] = []
        total = len(self.urls)

        for index, url in enumerate(self.urls):
            if self._cancelled:
                logger.info("批量下载已取消，剩余 %s 条未处理", total - index)
                break

            self.item_started.emit(index, total, url)
            worker = VideoDownloadThread(url, self.work_dir)
            self._current_worker = worker

            def _on_progress(percent: int, message: str, i=index):
                self.item_progress.emit(i, percent, message)

            worker.progress.connect(_on_progress)

            try:
                # 在当前线程直接调用，避免再嵌套 QThread
                video_path, *_rest = worker.download()
                if video_path:
                    success += 1
                    paths.append(video_path)
                    self.item_finished.emit(index, url, video_path)
                else:
                    fail += 1
                    self.item_error.emit(index, url, "下载结果为空")
            except Exception as exc:
                fail += 1
                logger.exception("批量下载失败 [%s/%s] %s", index + 1, total, url)
                self.item_error.emit(index, url, str(exc))
            finally:
                self._current_worker = None

        self.batch_finished.emit(success, fail, paths)
