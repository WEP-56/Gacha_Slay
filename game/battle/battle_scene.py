from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtGui import QBrush, QColor


class BattleScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 900, 500)
        self.setBackgroundBrush(QBrush(QColor(30, 30, 38)))

        # Layers z-values
        self.Z_BG = 0
        self.Z_UNIT = 10
        self.Z_FX = 20
        self.Z_UI = 30
