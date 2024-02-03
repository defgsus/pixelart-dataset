import json
from functools import partial
from typing import List
from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class NewLabelBox(QDialog):

    signal_add_label = pyqtSignal(dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._create_widgets()

    def _create_widgets(self):
        l = QVBoxLayout(self)
        l.addWidget(QLabel("name"))

        self.name_edit = QLineEdit(self)
        l.addWidget(self.name_edit)

        lh = QHBoxLayout()
        l.addLayout(lh)

        self.color_edits = [QSpinBox(self) for _ in range(3)]
        for e in self.color_edits:
            e.setRange(0, 255)
            e.setValue(128)
            lh.addWidget(e)

        butt = QPushButton("add label", self)
        l.addWidget(butt)
        butt.clicked.connect(self._apply)

    def _apply(self):
        name = self.name_edit.text()
        color = [e.value() for e in self.color_edits]

        self.signal_add_label.emit({"name": name, "color": color})
        self.close()
