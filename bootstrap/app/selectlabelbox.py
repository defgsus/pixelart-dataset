import json
from functools import partial
from typing import List, Optional
from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .labelmodel import LabelModel


class SelectLabelBox(QDialog):

    signal_set_label = pyqtSignal(dict)
    signal_closed = pyqtSignal()

    def __init__(self, *args, init_text: Optional[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_text = init_text
        self._label_model = LabelModel(self)
        self._create_widgets()

    def _create_widgets(self):
        l = QVBoxLayout(self)
        l.addWidget(QLabel("select label"))

        self.completer = QCompleter(self._label_model.labels(), self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)

        self.name_edit = QLineEdit(self)
        l.addWidget(self.name_edit)
        self.name_edit.setCompleter(self.completer)
        if self._init_text:
            self.name_edit.setText(self._init_text)
        self.name_edit.returnPressed.connect(self._apply)
        self.completer.activated.connect(self._apply)

    def _apply(self, name: Optional[str] = None):
        if name is None:
            name = self.name_edit.text()

        label = self._label_model.get_label(name)
        if label:
            self.signal_set_label.emit(label)

        self.close()

    def closeEvent(self, event):
        self.signal_closed.emit()
