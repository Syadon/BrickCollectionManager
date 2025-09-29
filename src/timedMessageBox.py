from typing import List
from PySide6.QtWidgets import QMessageBox, QWidget
from PySide6.QtCore import QTimer

class TimedMessageBox(QMessageBox):
    def __init__(self, timeout : float=5, 
                 buttons : List[QMessageBox.StandardButton]|None = None, 
                 parent : QWidget|None = None, **kwargs):

        if not buttons:
            buttons = [QMessageBox.StandardButton.Ok, 
                       QMessageBox.StandardButton.Abort, 
                       QMessageBox.StandardButton.Cancel]

        self.timer = QTimer()
        self.timeout = timeout
        self.timer.timeout.connect(self.tick)
        self.timer.setInterval(1000)
        super(TimedMessageBox, self).__init__(parent=parent)

        if "text" in kwargs:
            self.setText(kwargs["text"])
        if "title" in kwargs:
            self.setWindowTitle(kwargs["title"])
        self.t_btn = self.addButton(buttons.pop(0))
        self.t_btn_text = self.t_btn.text()
        self.setDefaultButton(self.t_btn)
        for button in buttons:
            self.addButton(button)

    def showEvent(self, e):
        super(TimedMessageBox, self).showEvent(e)
        self.tick()
        self.timer.start()

    def tick(self):
        self.timeout -= 1
        if self.timeout >= 0:
            self.t_btn.setText(self.t_btn_text + " (%i)" % self.timeout)
        else:
            self.timer.stop()
            self.defaultButton().animateClick()

    # @staticmethod
    # def question(**kwargs):
    #     w = TimedMessageBox(**kwargs)
    #     w.setIcon(QMessageBox.Icon.Question)
    #     return w.exec_()