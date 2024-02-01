import sys
import time

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import qdarkstyle

from bootstrap.app.mainwindow import MainWindow


def main():
    app = QApplication(sys.argv)

    app.setStyleSheet(qdarkstyle.load_stylesheet())
    screen = app.primaryScreen()

    win = MainWindow()
    # app.aboutToQuit.connect(win.slot_save_sessions)

    win.showMaximized()
    win.setGeometry(screen.availableGeometry())

    result = app.exec_()

    sys.exit(result)


if __name__ == "__main__":
    main()
