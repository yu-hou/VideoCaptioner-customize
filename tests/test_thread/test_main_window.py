from videocaptioner.ui.view import main_window


def test_macos_edit_menu_supports_fluent_window_widget_base(monkeypatch):
    """FluentWindow is QWidget-based and does not provide QMainWindow.menuBar()."""
    class Signal:
        def connect(self, callback):
            self.callback = callback

    class Action:
        NoRole = 0

        def __init__(self, text, parent):
            self.text = text
            self.parent = parent
            self.triggered = Signal()

        def setShortcut(self, shortcut):
            self.shortcut = shortcut

        def setMenuRole(self, role):
            self.role = role

    class Menu:
        def __init__(self, title):
            self.title = title
            self.items = []

        def addSeparator(self):
            self.items.append(None)

        def addAction(self, action):
            self.items.append(action)

    class MenuBar:
        def __init__(self, parent):
            self.parent = parent

        def setNativeMenuBar(self, native):
            self.native = native

        def addMenu(self, title):
            self.menu = Menu(title)
            return self.menu

    class FluentWidgetHost:
        def tr(self, text):
            return text

        def _invoke_focused_edit(self, method_name):
            pass

    monkeypatch.setattr(main_window.sys, "platform", "darwin")
    monkeypatch.setattr(main_window, "QMenuBar", MenuBar)
    monkeypatch.setattr(main_window, "QAction", Action)
    host = FluentWidgetHost()

    main_window.MainWindow._init_macos_edit_menu(host)

    assert host._mac_menu_bar.parent is host
    assert host._mac_menu_bar.native is True
    assert host._mac_menu_bar.menu.title == "编辑"
    assert [item.text for item in host._mac_menu_bar.menu.items if item] == [
        "撤销",
        "重做",
        "剪切",
        "复制",
        "粘贴",
        "全选",
    ]
