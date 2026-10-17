"""Keyboard-accessible segmented choices using native radio semantics."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QRadioButton, QButtonGroup


class SegmentedChoice(QFrame):
    currentTextChanged = Signal(str)

    def __init__(self, choices, parent=None):
        super().__init__(parent)
        self.setObjectName('segments')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.group = QButtonGroup(self)
        self.buttons = {}
        for text in choices:
            item = QRadioButton(text, self)
            item.setObjectName('segment')
            item.setAccessibleName(text)
            self.group.addButton(item)
            self.buttons[text] = item
            layout.addWidget(item, 1)
            item.toggled.connect(lambda checked, value=text: self.currentTextChanged.emit(value) if checked else None)
        self.buttons[choices[0]].setChecked(True)

    def currentText(self):
        return self.group.checkedButton().text()

    def setCurrentText(self, text):
        self.buttons[text].setChecked(True)


class GoalChoice(SegmentedChoice):
    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(['No goal', 'Set goal'], parent)
        self.currentTextChanged.connect(lambda _: self.toggled.emit(self.isChecked()))

    def isChecked(self):
        return self.currentText() == 'No goal'

    def setChecked(self, checked):
        self.setCurrentText('No goal' if checked else 'Set goal')
