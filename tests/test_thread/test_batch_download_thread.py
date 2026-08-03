"""Tests for BatchDownloadThread queue behavior."""

from videocaptioner.ui.thread import batch_download_thread as mod
from videocaptioner.ui.thread.batch_download_thread import BatchDownloadThread


def test_batch_download_thread_emits_summary(qapp, monkeypatch, tmp_path):
    calls = {"n": 0}

    class FakeSignal:
        def connect(self, _cb):
            return None

    class FakeWorker:
        def __init__(self, url, work_dir):
            self.url = url
            self.work_dir = work_dir
            self.progress = FakeSignal()

        def download(self):
            calls["n"] += 1
            if "fail" in self.url:
                raise RuntimeError("boom")
            return (str(tmp_path / f"{calls['n']}.mp4"), None, None, {})

    monkeypatch.setattr(mod, "VideoDownloadThread", FakeWorker)

    thread = BatchDownloadThread(
        [
            "https://example.com/ok1",
            "https://example.com/fail",
            "https://example.com/ok2",
        ],
        str(tmp_path),
    )
    results = {}

    def on_done(success, fail, paths):
        results["success"] = success
        results["fail"] = fail
        results["paths"] = paths

    thread.batch_finished.connect(on_done)
    thread.run()  # 同步跑，避免等待 QThread

    assert results["success"] == 2
    assert results["fail"] == 1
    assert len(results["paths"]) == 2
