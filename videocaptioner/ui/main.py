"""GUI entry point — launchable via `videocaptioner` (no args) or `python -m videocaptioner.ui.main`."""

import os
import platform
import sys


def main():
    import traceback

    from PyQt5.QtCore import QEvent, QObject, Qt, QTimer, QTranslator
    from PyQt5.QtGui import QKeyEvent
    from PyQt5.QtWidgets import QApplication

    from videocaptioner.config import TRANSLATIONS_PATH
    from videocaptioner.core.utils.cache import disable_cache, enable_cache
    from videocaptioner.core.utils.logger import setup_logger

    # Suppress qfluentwidgets ad
    with open(os.devnull, "w") as _devnull:
        sys.stdout, _stdout = _devnull, sys.stdout
        from qfluentwidgets import FluentTranslator
        sys.stdout = _stdout

    from videocaptioner.ui.common.config import cfg
    from videocaptioner.ui.view.main_window import MainWindow

    # Qt platform plugin path
    lib_folder = "Lib" if platform.system() == "Windows" else "lib"
    plugin_path = os.path.join(
        sys.prefix, lib_folder, "site-packages", "PyQt5", "Qt5", "plugins"
    )
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path

    # Logger + global exception hook
    logger = setup_logger("NovaCaption")

    def exception_hook(exctype, value, tb):
        logger.error("".join(traceback.format_exception(exctype, value, tb)))
        sys.__excepthook__(exctype, value, tb)

    sys.excepthook = exception_hook

    # Cache
    if cfg.get(cfg.cache_enabled):
        enable_cache()
    else:
        disable_cache()

    # DPI scaling
    if cfg.get(cfg.dpiScale) == "Auto":
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough  # type: ignore
        )
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # type: ignore
    else:
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)  # type: ignore

    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)  # type: ignore

    # On macOS, Qt maps Command to ControlModifier and the physical Control
    # key to MetaModifier. Users coming from Windows commonly press Ctrl+V;
    # make that alternate shortcut paste as well instead of inserting "v".
    if platform.system() == "Darwin":
        class MacPasteCompatibilityFilter(QObject):
            def eventFilter(self, watched, event):
                if (
                    event.type() == QEvent.KeyPress
                    and event.key() == Qt.Key_V
                    and event.modifiers() == Qt.MetaModifier
                ):
                    focused = QApplication.focusWidget()
                    paste = getattr(focused, "paste", None)
                    if callable(paste) and focused.isEnabled():
                        paste()
                        return True
                return super().eventFilter(watched, event)

        app.macPasteCompatibilityFilter = MacPasteCompatibilityFilter(app)
        app.installEventFilter(app.macPasteCompatibilityFilter)

    # i18n
    locale = cfg.get(cfg.language).value
    app.installTranslator(FluentTranslator(locale))
    my_translator = QTranslator()
    my_translator.load(str(TRANSLATIONS_PATH / f"VideoCaptioner_{locale.name()}.qm"))
    app.installTranslator(my_translator)

    w = MainWindow()
    w.show()

    # Packaged GUI smoke test. This is inert during normal use and lets the
    # build pipeline verify the frozen app's real clipboard integration without
    # relying on macOS Accessibility permissions for external UI automation.
    smoke_output = os.environ.get("VIDEOCAPTIONER_GUI_SMOKE_OUTPUT")
    if smoke_output:
        def run_gui_smoke():
            import json
            from pathlib import Path

            expected_command = "https://example.com/command-v"
            expected_control = "https://example.com/control-v"
            expected_button = "https://www.douyin.com/video/7659705531116870065"
            results = {}
            try:
                interface = w.homeInterface.task_creation_interface
                field = interface.search_input
                clipboard = QApplication.clipboard()

                clipboard.setText(expected_command)
                field.clear()
                QApplication.sendEvent(
                    field,
                    QKeyEvent(
                        QEvent.KeyPress,
                        Qt.Key_V,
                        Qt.ControlModifier,
                    ),
                )
                results["command_v"] = field.text()

                clipboard.setText(expected_control)
                field.clear()
                QApplication.sendEvent(
                    field,
                    QKeyEvent(
                        QEvent.KeyPress,
                        Qt.Key_V,
                        Qt.MetaModifier,
                    ),
                )
                results["control_v"] = field.text()

                clipboard.setText(f"分享这个视频 {expected_button} 复制后打开")
                field.clear()
                interface.paste_from_clipboard()
                results["paste_button"] = field.text()
                results["ok"] = results == {
                    "command_v": expected_command,
                    "control_v": expected_control,
                    "paste_button": expected_button,
                }
            except Exception:
                results["ok"] = False
                results["error"] = traceback.format_exc()

            Path(smoke_output).write_text(
                json.dumps(results, ensure_ascii=False),
                encoding="utf-8",
            )
            app.exit(0 if results["ok"] else 1)

        QTimer.singleShot(250, run_gui_smoke)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
