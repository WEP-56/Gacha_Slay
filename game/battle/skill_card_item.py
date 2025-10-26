from PyQt5.QtCore import Qt, QPointF, QVariantAnimation, QEasingCurve
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsItem, QGraphicsSimpleTextItem
from PyQt5.QtGui import QPixmap, QColor


class SkillCardItem(QGraphicsPixmapItem):
    def __init__(self, width: int, height: int, label: str, origin_pos: QPointF,
                 apply_fn, is_valid_target_fn, image_path: str = ""):
        super().__init__()
        self._w = width
        self._h = height
        self.origin_pos = QPointF(origin_pos)
        self.apply_fn = apply_fn
        self.is_valid_target_fn = is_valid_target_fn
        self.dragging = False
        self._anims = []
        # load image or use colored placeholder
        pix = QPixmap()
        if image_path:
            pix = QPixmap(image_path)
        if pix.isNull():
            pix = QPixmap(width, height)
            pix.fill(QColor(60, 120, 200))
        self.setPixmap(pix.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setTransformOriginPoint(self.boundingRect().center())
        self.setZValue(50)

        # label (below image)
        self.text_item = QGraphicsSimpleTextItem(label, self)
        self.text_item.setBrush(QColor("white"))
        br = self.text_item.boundingRect()
        self.text_item.setPos((width - br.width())/2, height + 6)

        self.setPos(self.origin_pos)

    def appear(self, duration_ms: int = 250):
        try:
            self.setOpacity(0.0)
        except Exception:
            return
        anim = QVariantAnimation()
        anim.setDuration(max(60, duration_ms))
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def on_val(v):
            try:
                self.setOpacity(float(v))
            except Exception:
                pass

        anim.valueChanged.connect(on_val)
        # keep a ref on self to avoid GC
        self._appear_anim = anim
        anim.start()

    def mousePressEvent(self, event):
        self.dragging = True
        self._press_offset = event.pos()
        self.setScale(1.1)
        self.setZValue(100)
        event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            scene_pos = self.mapToScene(event.pos())
            new_pos = scene_pos - self._press_offset
            self.setPos(new_pos)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.setZValue(50)
        # check valid target
        success = False
        if callable(self.is_valid_target_fn) and callable(self.apply_fn):
            if self.is_valid_target_fn(self):
                try:
                    res = self.apply_fn(self)
                    success = bool(res)
                except Exception:
                    success = False
        if success:
            # remove/hide on use
            self.scene().removeItem(self)
        else:
            self.animate_back()
        event.accept()

    def animate_back(self):
        pos_anim = QVariantAnimation()
        pos_anim.setDuration(200)
        pos_anim.setStartValue(self.pos())
        pos_anim.setEndValue(self.origin_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutCubic)

        def on_val(v):
            self.setPos(v)
        def on_finish():
            self.setScale(1.0)
            if pos_anim in self._anims:
                self._anims.remove(pos_anim)
        pos_anim.valueChanged.connect(on_val)
        pos_anim.finished.connect(on_finish)
        self._anims.append(pos_anim)
        pos_anim.start()
