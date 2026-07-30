"""Smoke tests for the persistent non-technical user guide."""

from qfluentwidgets import themeColor

from videocaptioner.ui.view.user_guide_interface import UserGuideInterface


def test_user_guide_builds_actions_and_content(qapp):
    guide = UserGuideInterface()

    assert guide.windowTitle() == "使用指南"
    assert guide.restartWizardButton.text() == "重新打开设置向导"
    assert guide.openSettingsButton.text() == "打开设置"
    assert guide.goHomeButton.text() == "前往主页开始处理"
    assert guide.widget() is guide.scrollWidget
    assert guide.mainLayout.count() >= 15
    assert themeColor().name() in guide.styleSheet()

    guide.close()


def test_user_guide_action_signals(qapp):
    guide = UserGuideInterface()
    emitted = {"wizard": 0, "home": 0, "settings": 0}
    guide.restartWizardRequested.connect(
        lambda: emitted.__setitem__("wizard", emitted["wizard"] + 1)
    )
    guide.openHomeRequested.connect(
        lambda: emitted.__setitem__("home", emitted["home"] + 1)
    )
    guide.openSettingsRequested.connect(
        lambda: emitted.__setitem__("settings", emitted["settings"] + 1)
    )

    guide.restartWizardButton.click()
    guide.goHomeButton.click()
    guide.openSettingsButton.click()

    assert emitted == {"wizard": 1, "home": 1, "settings": 1}
    guide.close()
