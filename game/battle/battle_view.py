from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtGui import QTransform
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt
from .battle_scene import BattleScene


class BattleView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.setViewport(QOpenGLWidget())
        except Exception:
            pass
        self.setRenderHints(self.renderHints())
        self.setAlignment(Qt.AlignCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        scene = BattleScene(self)
        self.setScene(scene)
        self.setSceneRect(0, 0, 900, 500)

    @property
    def battle_scene(self) -> BattleScene:
        return self.scene()
