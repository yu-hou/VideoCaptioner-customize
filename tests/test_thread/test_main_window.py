from PyQt5.QtCore import QRect

from videocaptioner.ui.view import main_window


def test_fit_window_to_screen_clamps_oversized_geometry(monkeypatch):
    """窗口高于可用区域时应缩小并移回屏幕内，避免贴顶裁切底部。"""

    class FakeWindow:
        def __init__(self):
            self._w = 1050
            self._h = 1200
            self._x = -20
            self._y = -40
            self._min_w = 700
            self._min_h = 520

        def width(self):
            return self._w

        def height(self):
            return self._h

        def minimumWidth(self):
            return self._min_w

        def minimumHeight(self):
            return self._min_h

        def setMinimumSize(self, w, h):
            self._min_w, self._min_h = w, h

        def resize(self, w, h):
            self._w, self._h = w, h

        def move(self, x, y):
            self._x, self._y = x, y

        def frameGeometry(self):
            return QRect(self._x, self._y, self._w, self._h)

        def _available_screen_geometry(self):
            return QRect(0, 30, 1440, 800)

    host = FakeWindow()
    main_window.MainWindow._fit_window_to_screen(host)

    assert host.width() == 1050
    assert host.height() == 800
    assert host._x == 0
    assert host._y == 30


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
