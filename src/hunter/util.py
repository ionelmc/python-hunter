import ast
import builtins
import re
import types
import weakref
from collections import Counter
from collections import OrderedDict
from collections import defaultdict
from collections import deque
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from inspect import CO_VARARGS
from inspect import CO_VARKEYWORDS
from inspect import getattr_static
from re import RegexFlag
from threading import main_thread

from PyQt5.QtCore import Qt, QRect, QEvent, QSize
from PyQt5.QtGui import QFontMetrics, QColor
from PyQt5.QtGui import QTextOption
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTreeWidget, QTreeWidgetItem, \
    QSplitter, QStyle, QStyledItemDelegate, \
    QTextEdit, QAbstractItemView
from tqdm import tqdm

from .vendor.colorama import Back
from .vendor.colorama import Fore
from .vendor.colorama import Style

InstanceType = type(object())

try:
    from re import Pattern
except ImportError:
    Pattern = type(re.compile(''))

OTHER_COLORS = {
    'COLON': Style.BRIGHT + Fore.BLACK,
    'LINENO': Style.RESET_ALL,
    'KIND': Fore.CYAN,
    'CONT': Style.BRIGHT + Fore.BLACK,
    'VARS': Style.BRIGHT + Fore.MAGENTA,
    'VARS-NAME': Style.NORMAL + Fore.MAGENTA,
    'INTERNAL-FAILURE': Style.BRIGHT + Back.RED + Fore.RED,
    'INTERNAL-DETAIL': Fore.WHITE,
    'SOURCE-FAILURE': Style.BRIGHT + Back.YELLOW + Fore.YELLOW,
    'SOURCE-DETAIL': Fore.WHITE,
    'BUILTIN': Style.NORMAL + Fore.MAGENTA,
    'RESET': Style.RESET_ALL,
}
for name, group in [
    ('', Style),
    ('fore', Fore),
    ('back', Back),
]:
    for key in dir(group):
        OTHER_COLORS[f'{name}({key})' if name else key] = getattr(group, key)
CALL_COLORS = {
    'call': Style.BRIGHT + Fore.BLUE,
    'line': Fore.RESET,
    'return': Style.BRIGHT + Fore.GREEN,
    'exception': Style.BRIGHT + Fore.RED,
}
CODE_COLORS = {
    'call': Fore.RESET + Style.BRIGHT,
    'line': Fore.RESET,
    'return': Fore.YELLOW,
    'exception': Fore.RED,
}
MISSING = type('MISSING', (), {'__repr__': lambda _: '?'})()
BUILTIN_SYMBOLS = set(vars(builtins))
CYTHON_SUFFIX_RE = re.compile(r'([.].+)?[.](so|pyd)$', re.IGNORECASE)
LEADING_WHITESPACE_RE = re.compile('(^[ \t]*)(?:[^ \t\n])', re.MULTILINE)

get_main_thread = weakref.ref(main_thread())


def get_arguments(code):
    co_varnames = code.co_varnames
    co_argcount = code.co_argcount
    co_kwonlyargcount = code.co_kwonlyargcount
    kwonlyargs = co_varnames[co_argcount : co_argcount + co_kwonlyargcount]
    for arg in co_varnames[:co_argcount]:
        yield '', arg, arg
    co_argcount += co_kwonlyargcount
    if code.co_flags & CO_VARARGS:
        arg = co_varnames[co_argcount]
        yield '*', arg, arg
        co_argcount = co_argcount + 1
    for arg in kwonlyargs:
        yield '', arg, arg
    if code.co_flags & CO_VARKEYWORDS:
        arg = co_varnames[co_argcount]
        yield '**', arg, arg


def flatten(something):
    if isinstance(something, (list, tuple)):
        for element in something:
            yield from flatten(element)
    else:
        yield something


class cached_property:
    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


def get_func_in_mro(obj, code):
    """Attempt to find a function in a side-effect free way.

    This looks in obj's mro manually and does not invoke any descriptors.
    """
    val = getattr_static(obj, code.co_name, None)
    if val is None:
        return None
    if isinstance(val, (classmethod, staticmethod)):
        candidate = val.__func__
    elif isinstance(val, property) and (val.fset is None) and (val.fdel is None):
        candidate = val.fget
    else:
        candidate = val
    return if_same_code(candidate, code)


def if_same_code(func, code):
    while func is not None:
        func_code = getattr(func, '__code__', None)
        if func_code is code:
            return func
        # Attempt to find the decorated function
        func = getattr(func, '__wrapped__', None)
    return None


def iter_symbols(code):
    """
    Iterate all the variable names in the given expression.

    Example:

    * ``self.foobar`` yields ``self``
    * ``self[foobar]`` yields `self`` and ``foobar``
    """
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.Name):
            yield node.id


def safe_repr(obj, maxdepth=5):
    if not maxdepth:
        return '...'
    obj_type = type(obj)
    obj_type_type = type(obj_type)
    newdepth = maxdepth - 1

    # only represent exact builtins
    # (subclasses can have side effects due to __class__ as a property, __instancecheck__, __subclasscheck__ etc.)
    if obj_type is dict:
        return f'{{{", ".join(f"{safe_repr(k, maxdepth)}: {safe_repr(v, newdepth)}" for k, v in obj.items())}}}'
    elif obj_type is list:
        return f'[{", ".join(safe_repr(i, newdepth) for i in obj)}]'
    elif obj_type is tuple:
        return f'({", ".join(safe_repr(i, newdepth) for i in obj)}{"," if len(obj) == 1 else ""})'
    elif obj_type is set:
        return f'{{{", ".join(safe_repr(i, newdepth) for i in obj)}}}'
    elif obj_type is frozenset:
        return f'{obj_type.__name__}({{{", ".join(safe_repr(i, newdepth) for i in obj)}}})'
    elif obj_type is deque:
        return f'{obj_type.__name__}([{", ".join(safe_repr(i, newdepth) for i in obj)}])'
    elif obj_type in (Counter, OrderedDict, defaultdict):
        return f'{obj_type.__name__}({{{", ".join(f"{safe_repr(k, maxdepth)}: {safe_repr(v, newdepth)}" for k, v in obj.items())}}})'
    elif obj_type is Pattern:
        if obj.flags:
            return f're.compile({safe_repr(obj.pattern)}, flags={RegexFlag(obj.flags)})'
        else:
            return f're.compile({safe_repr(obj.pattern)})'
    elif obj_type in (date, timedelta):
        return repr(obj)
    elif obj_type is datetime:
        return (
            f'{obj_type.__name__}('
            f'{obj.year:d}, '
            f'{obj.month:d}, '
            f'{obj.day:d}, '
            f'{obj.hour:d}, '
            f'{obj.minute:d}, '
            f'{obj.second:d}, '
            f'{obj.microsecond:d}, '
            f'tzinfo={safe_repr(obj.tzinfo)}{f", fold={safe_repr(obj.fold)}" if hasattr(obj, "fold") else ""})'
        )
    elif obj_type is time:
        return (
            f'{obj_type.__name__}('
            f'{obj.hour:d}, '
            f'{obj.minute:d}, '
            f'{obj.second:d}, '
            f'{obj.microsecond:d}, '
            f'tzinfo={safe_repr(obj.tzinfo)}{f", fold={safe_repr(obj.fold)}" if hasattr(obj, "fold") else ""})'
        )
    elif obj_type is types.MethodType:
        self = obj.__self__
        name = getattr(obj, '__qualname__', None)
        if name is None:
            name = obj.__name__
        return f'<{"un" if self is None else ""}bound method {name} of {safe_repr(self, newdepth)}>'
    elif obj_type_type is type and BaseException in obj_type.__mro__:
        return f'{obj_type.__name__}({", ".join(safe_repr(i, newdepth) for i in obj.args)})'
    elif (
        obj_type_type is type
        and obj_type is not InstanceType
        and obj_type.__module__ in (builtins.__name__, 'io', 'socket', '_socket', 'zoneinfo', 'decimal')
    ):
        # hardcoded list of safe things. note that isinstance ain't used
        # (we don't trust subclasses to do the right thing in __repr__)
        return repr(obj)
    else:
        # if the object has a __dict__ then it's probably an instance of a pure python class, assume bad things
        #  with side effects will be going on in __repr__ - use the default instead (object.__repr__)
        return object.__repr__(obj)


def frame_iterator(frame):
    """
    Yields frames till there are no more.
    """
    while frame:
        yield frame
        frame = frame.f_back


class ResizableWidget(QWidget):
    """custom window to provide resizing and keep minimalistic style for tooltip
    showing full argument hidden under dots <...> """
    def __init__(self, text, cursor_pos, parent=None):
        super(ResizableWidget, self).__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: white; border: 1px solid black;")
        self.oldGeometry = None

        layout = QVBoxLayout(self)
        self.textEdit = QTextEdit(self)
        self.textEdit.setPlainText(text)
        self.textEdit.setReadOnly(True)
        self.textEdit.setWordWrapMode(QTextOption.WordWrap)
        layout.addWidget(self.textEdit)

        self.resizeGripSize = 20
        self.setMouseTracking(True)
        self.isResizing = False
        self.resizeDirection = None
        self.oldMousePos = None
        self.setMinimumSize(150, 70)
        self.adjustSize()

        QApplication.instance().installEventFilter(self)
        self.calculateInitialSize(text)
        self.move(cursor_pos.x() - self.width(), cursor_pos.y())

    def calculateInitialSize(self, text):
        fontMetrics = QFontMetrics(self.textEdit.font())
        textSize = fontMetrics.size(0, text)
        textSize += QSize(30, 40)  # Добавляем отступы для краев и прокрутки
        self.resize(textSize)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.isInResizeArea(event.pos()):
                self.isResizing = True
                self.oldMousePos = event.globalPos()
                self.oldGeometry = self.geometry()
                self.resizeDirection = self.getResizeDirection(event.pos())
            else:
                super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isResizing:
            delta = event.globalPos() - self.oldMousePos
            newRect = QRect(self.oldGeometry)
            if self.resizeDirection == "bottom-right":
                newRect.setBottomRight(self.oldGeometry.bottomRight() + delta)
            elif self.resizeDirection == "bottom-left":
                newRect.setBottomLeft(self.oldGeometry.bottomLeft() + delta)
            elif self.resizeDirection == "top-right":
                newRect.setTopRight(self.oldGeometry.topRight() + delta)
            elif self.resizeDirection == "top-left":
                newRect.setTopLeft(self.oldGeometry.topLeft() + delta)
            elif self.resizeDirection == "bottom":
                newRect.setBottom(self.oldGeometry.bottom() + delta.y())
            elif self.resizeDirection == "right":
                newRect.setRight(self.oldGeometry.right() + delta.x())
            elif self.resizeDirection == "top":
                newRect.setTop(self.oldGeometry.top() + delta.y())
            elif self.resizeDirection == "left":
                newRect.setLeft(self.oldGeometry.left() + delta.x())
            self.setGeometry(newRect)
        elif self.isInResizeArea(event.pos()):
            self.setCursor(self.getCursorShape(event.pos()))
        else:
            self.setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.isResizing = False
        super().mouseReleaseEvent(event)

    def isInResizeArea(self, pos):
        rect = self.rect()
        return (
                abs(pos.x() - rect.left()) <= self.resizeGripSize or
                abs(pos.x() - rect.right()) <= self.resizeGripSize or
                abs(pos.y() - rect.top()) <= self.resizeGripSize or
                abs(pos.y() - rect.bottom()) <= self.resizeGripSize
        )

    def getResizeDirection(self, pos):
        rect = self.rect()
        if abs(pos.y() - rect.bottom()) <= self.resizeGripSize and abs(pos.x() - rect.right()) <= self.resizeGripSize:
            return "bottom-right"
        elif abs(pos.y() - rect.bottom()) <= self.resizeGripSize and abs(pos.x() - rect.left()) <= self.resizeGripSize:
            return "bottom-left"
        elif abs(pos.y() - rect.top()) <= self.resizeGripSize and abs(pos.x() - rect.right()) <= self.resizeGripSize:
            return "top-right"
        elif abs(pos.y() - rect.top()) <= self.resizeGripSize and abs(pos.x() - rect.left()) <= self.resizeGripSize:
            return "top-left"
        elif abs(pos.x() - rect.right()) <= self.resizeGripSize:
            return "right"
        elif abs(pos.x() - rect.left()) <= self.resizeGripSize:
            return "left"
        elif abs(pos.y() - rect.top()) <= self.resizeGripSize:
            return "top"
        elif abs(pos.y() - rect.bottom()) <= self.resizeGripSize:
            return "bottom"

    def getCursorShape(self, pos):
        direction = self.getResizeDirection(pos)
        if direction in ["top-right", "bottom-left"]:
            return Qt.SizeBDiagCursor
        elif direction in ["top-left", "bottom-right"]:
            return Qt.SizeFDiagCursor
        elif direction in ["left", "right"]:
            return Qt.SizeHorCursor
        elif direction in ["top", "bottom"]:
            return Qt.SizeVerCursor
        return Qt.ArrowCursor

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if not self.rect().contains(self.mapFromGlobal(event.globalPos())):
                self.close()
                return True
        return super(ResizableWidget, self).eventFilter(obj, event)

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        super(ResizableWidget, self).closeEvent(event)


class ElidedItemDelegate(QStyledItemDelegate):
    """custom eliding delegate"""
    def __init__(self, parent=None):
        super(ElidedItemDelegate, self).__init__(parent)
        self.elideMode = Qt.ElideNone
        self.tooltip = None
        self.highlight_color = QColor(200, 200, 255)

    def elideText(self, text, fontMetrics, available_width):
        elidedText = text
        text_width = fontMetrics.width(text)

        if text_width > available_width:
            elidedText = ""
            for char in text:
                if fontMetrics.width(elidedText + char) > available_width:
                    break
                elidedText += char

        return elidedText

    def paint(self, painter, option, index):
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, self.highlight_color)

        text = index.data(Qt.DisplayRole)
        if text:
            fontMetrics = option.fontMetrics
            available_width = option.rect.width() - 10
            elidedText = self.elideText(text, fontMetrics, available_width)

            painter.drawText(option.rect.adjusted(0, 0, -20, 0), Qt.AlignLeft | Qt.AlignTop, elidedText)

            if fontMetrics.width(text) > available_width or '\n' in text:
                buttonRect = QRect(option.rect.right() - 25, option.rect.top(), 25, option.rect.height())
                painter.setPen(QColor(Qt.blue))
                painter.drawText(buttonRect, Qt.AlignCenter | Qt.AlignTop, "...")
                painter.setPen(QColor(Qt.black))
        else:
            super(ElidedItemDelegate, self).paint(painter, option, index)

    def sizeHint(self, option, index):
        fontMetrics = option.fontMetrics
        return QSize(option.rect.width(), fontMetrics.height())

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease:
            pos = event.pos()
            text = index.data(Qt.DisplayRole)
            fontMetrics = QFontMetrics(option.font)
            available_width = option.rect.width() - 10
            if fontMetrics.width(text) > available_width or '\n' in text:
                buttonRect = QRect(option.rect.right() - 25, option.rect.top(), 25, option.rect.height())
                if buttonRect.contains(pos):
                    self.showInteractiveTooltip(text, event.globalPos())
                    return True
        return super(ElidedItemDelegate, self).editorEvent(event, model, option, index)

    def showInteractiveTooltip(self, text, pos):
        if self.tooltip:
            self.tooltip.close()
        self.tooltip = ResizableWidget(text, pos)
        self.tooltip.show()


class TracebackVisualizer(QMainWindow):
    """main window"""
    def __init__(self, events):
        super().__init__()
        self.events = events
        self.initUI()
        self.populateTree()

    def initUI(self):
        self.setWindowTitle("Traceback Visualizer")
        self.setGeometry(100, 100, 1200, 800)
        self.showMaximized()

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(['Function', 'Arguments', 'Kind', 'Filename:Line'])
        self.tree.itemClicked.connect(self.onItemClicked)

        self.details_widget = QTreeWidget()
        self.details_widget.setColumnCount(3)
        self.details_widget.setHeaderLabels(['Key', 'Type', 'Value'])
        self.details_widget.setItemDelegate(ElidedItemDelegate())
        self.details_widget.setSelectionBehavior(QAbstractItemView.SelectItems)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tree)
        main_widget = QWidget()
        main_widget.setLayout(main_layout)

        details_layout = QVBoxLayout()
        details_layout.addWidget(self.details_widget)
        details_widget = QWidget()
        details_widget.setLayout(details_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)
        splitter.addWidget(main_widget)
        splitter.addWidget(details_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

    def onItemClicked(self, item):
        self.details_widget.clear()
        index = item.index
        args = self.events[index - 1]["args"]["initial_args"]
        self.populateDetails(args)

    def populateDetails(self, data, parent=None):
        if parent is None:
            parent = self.details_widget.invisibleRootItem()

        def add_item(parent, key, value, item_type, length=None):
            if length is None:
                QTreeWidgetItem(parent, [key, f'{{{item_type}}}', str(value)])
            else:
                QTreeWidgetItem(parent, [key, f"{{{item_type}: {length}}}", ""])

        if isinstance(data, dict):
            for key, value in data.items():
                item_type = type(value).__name__
                if not isinstance(value, (list, dict, tuple, set)):
                    add_item(parent, key, value, item_type)
                else:
                    add_item(parent, key, "", item_type, len(value))
                    self.populateDetails(value, parent.child(parent.childCount() - 1))
        elif isinstance(data, (list, tuple, set)):
            for i, value in enumerate(data):
                item_type = type(value).__name__
                if not isinstance(value, (list, dict, tuple, set)):
                    add_item(parent, str(i), value, item_type)
                else:
                    add_item(parent, str(i), "", item_type, len(value))
                    self.populateDetails(value, parent.child(parent.childCount() - 1))
        else:
            item_type = type(data).__name__
            add_item(parent, "", data, item_type)

    def populateTree(self):
        top_level_items = []

        stack = []  # (current element, depth)
        for event in tqdm(self.events, desc="Processing events"):
            filename_lineno = f"{event['filename_prefix']}"
            kind = event['kind']
            function = f"{'=>' if kind == 'call' else '<=' if kind == 'return' else ''} {event['function']}"
            args = event["args"]["repr_args"]
            depth = event['depth']
            item = QTreeWidgetItem([function, args, kind, filename_lineno])
            item.index = event["counter"]

            while stack and stack[-1][1] >= depth:
                stack.pop()

            if stack:
                stack[-1][0].addChild(item)
            else:
                top_level_items.append(item)

            stack.append((item, depth))

        self.tree.addTopLevelItems(top_level_items)
