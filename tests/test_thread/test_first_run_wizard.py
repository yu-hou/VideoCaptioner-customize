"""Smoke tests for first-run setup UI."""

from qfluentwidgets import themeColor

from videocaptioner.ui.common.config import cfg
from videocaptioner.ui.components.FirstRunWizard import FirstRunWizard
from videocaptioner.ui.components.YuanbaoCookieManager import (
    DEFAULT_TEST_URL,
    YuanbaoCookieManager,
)


def test_first_run_wizard_builds_all_pages(qapp):
    wizard = FirstRunWizard()

    assert wizard.pages.count() == 5
    assert wizard.cookieManager.profileCard is not None
    assert wizard.yuanbaoCookieManager.profileCard is not None
    assert wizard.workDirEdit.text()
    assert themeColor().name() in wizard.styleSheet()
    assert wizard.accentBar.objectName() == "accentBar"
    assert wizard.stepLabel.text() == "设置进度  1 / 5"

    wizard.close()


def test_yuanbao_cookie_manager_does_not_overwrite_douyin_test_url(qapp):
    original_douyin = str(cfg.get(cfg.douyin_test_url))
    original_yuanbao = str(cfg.get(cfg.yuanbao_test_url))
    cfg.set(cfg.douyin_test_url, "https://www.douyin.com/video/keep-me")
    cfg.set(cfg.yuanbao_test_url, DEFAULT_TEST_URL)
    manager = None
    try:
        manager = YuanbaoCookieManager()
        assert str(cfg.get(cfg.douyin_test_url)) == "https://www.douyin.com/video/keep-me"
        assert manager.testUrlCard.lineEdit.text() == DEFAULT_TEST_URL
    finally:
        cfg.set(cfg.douyin_test_url, original_douyin)
        cfg.set(cfg.yuanbao_test_url, original_yuanbao)
        if manager is not None:
            manager.deleteLater()
