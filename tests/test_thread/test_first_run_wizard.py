"""Smoke tests for first-run setup UI."""

from videocaptioner.ui.components.FirstRunWizard import FirstRunWizard


def test_first_run_wizard_builds_all_pages(qapp):
    wizard = FirstRunWizard()

    assert wizard.pages.count() == 4
    assert wizard.cookieManager.profileCard is not None
    assert wizard.workDirEdit.text()

    wizard.close()
