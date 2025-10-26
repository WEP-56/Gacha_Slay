from PyQt5.QtCore import QPointF, QEasingCurve, QVariantAnimation, Qt
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsItem, QGraphicsRectItem
from PyQt5.QtGui import QPixmap, QColor, QPen
import os
import math


class CardItem(QGraphicsPixmapItem):
    def __init__(self, image_path: str, name: str, max_hp: int = 100, atk: int = 20):
        super().__init__()
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self.atk = atk
        self._anims = []  # keep animation references
        self.shield = 0
        self.next_damage_taken_multiplier = 1.0  # debuff like Vulnerable (next hit only)

        # Debug: image loading status
        print(f"[CardItem] Loading image for {name}: {image_path} exists={os.path.exists(image_path)}")
        pix = QPixmap()
        if os.path.exists(image_path):
            pix = QPixmap(image_path)
        print(f"[CardItem] QPixmap.isNull for {name}: {pix.isNull()}")
        if pix.isNull():
            pix = QPixmap(256, 256)
            pix.fill(QColor("gray"))
        self.setPixmap(pix.scaled(200, 200))
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setTransformOriginPoint(self.boundingRect().center())
        self._opacity = 1.0

        # Bars
        self._bar_bg = QGraphicsRectItem(0, 0, 200, 8, self)
        self._bar_bg.setBrush(QColor(60, 60, 60))
        self._bar_bg.setPen(QColor(20, 20, 20))
        self._bar_hp = QGraphicsRectItem(0, 0, 200, 8, self)
        self._bar_hp.setBrush(QColor(200, 60, 60))
        self._bar_hp.setPen(QPen(Qt.NoPen))
        self._bar_shield = QGraphicsRectItem(0, 0, 0, 8, self)
        self._bar_shield.setBrush(QColor(80, 140, 240))
        self._bar_shield.setPen(QPen(Qt.NoPen))
        # position bars under the card
        self._layout_bars()
        self.update_bars()

    def take_damage(self, dmg: int):
        # consume shield first
        # apply next-hit multiplier if any
        if self.next_damage_taken_multiplier != 1.0:
            dmg = int(math.ceil(dmg * self.next_damage_taken_multiplier))
            self.next_damage_taken_multiplier = 1.0
        if self.shield > 0:
            used = min(self.shield, dmg)
            self.shield -= used
            dmg -= used
        if dmg > 0:
            self.hp = max(0, self.hp - dmg)
        self.update_bars()
        return self.hp

    def is_dead(self) -> bool:
        return self.hp <= 0

    def add_shield(self, amount: int):
        self.shield += max(0, int(amount))
        self.update_bars()

    def heal(self, amount: int):
        if amount <= 0:
            return self.hp
        self.hp = min(self.max_hp, self.hp + int(amount))
        self.update_bars()
        return self.hp

    def play_hit_fx(self):
        # simple flash scale with QVariantAnimation
        anim = QVariantAnimation()
        anim.setDuration(120)
        anim.setStartValue(1.0)
        anim.setEndValue(0.9)
        anim.setEasingCurve(QEasingCurve.InOutQuad)

        def on_value(v):
            try:
                self.setScale(float(v))
            except Exception:
                pass

        def on_finish():
            self.setScale(1.0)
            if anim in self._anims:
                self._anims.remove(anim)

        anim.valueChanged.connect(on_value)
        anim.finished.connect(on_finish)
        self._anims.append(anim)
        anim.start()

    def charge_attack(self, target_pos: QPointF, on_hit):
        # move to mid then back using QVariantAnimation
        start = self.pos()
        mid = QPointF((start.x() + target_pos.x()) / 2, (start.y() + target_pos.y()) / 2)

        go = QVariantAnimation()
        go.setDuration(260)
        go.setStartValue(start)
        go.setEndValue(mid)
        go.setEasingCurve(QEasingCurve.OutCubic)

        back = QVariantAnimation()
        back.setDuration(260)
        back.setStartValue(mid)
        back.setEndValue(start)
        back.setEasingCurve(QEasingCurve.InCubic)

        def go_value(v):
            self.setPos(v)

        def back_value(v):
            self.setPos(v)

        def back_finish():
            if back in self._anims:
                self._anims.remove(back)

        def go_finish():
            if callable(on_hit):
                on_hit()
            back.start()
            # remove go from refs when finished and back started
            if go in self._anims:
                self._anims.remove(go)

        go.valueChanged.connect(go_value)
        back.valueChanged.connect(back_value)
        back.finished.connect(back_finish)
        go.finished.connect(go_finish)

        self._anims.extend([go, back])
        go.start()

    def _layout_bars(self):
        # bars placed slightly below the card image
        img_rect = self.boundingRect()
        x = 0
        y = img_rect.height() + 4
        for r in (self._bar_bg, self._bar_hp, self._bar_shield):
            r.setPos(x, y)

    def update_bars(self):
        # width based on 200px image width
        total_w = 200
        hp_ratio = 0 if self.max_hp <= 0 else max(0.0, min(1.0, self.hp / self.max_hp))
        self._bar_hp.setRect(0, 0, total_w * hp_ratio, 8)
        # shield width clamp; visualize as addition on top of hp bar length
        shield_ratio = 0 if self.max_hp <= 0 else max(0.0, min(1.0, self.shield / self.max_hp))
        self._bar_shield.setRect(0, 0, total_w * shield_ratio, 8)

    def heartbeat(self, times: int = 3, duration_ms: int = 1000):
        # scale up/down in a sine wave pattern: 1 + 0.12*sin(2*pi*f*t), f = times over duration
        anim = QVariantAnimation()
        anim.setDuration(max(200, duration_ms))
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        base_scale = 1.0
        amplitude = 0.12

        def on_val(v: float):
            s = base_scale + amplitude * math.sin(2 * math.pi * times * v)
            self.setScale(s)

        def on_finish():
            self.setScale(1.0)
            if anim in self._anims:
                self._anims.remove(anim)

        anim.valueChanged.connect(on_val)
        anim.finished.connect(on_finish)
        self._anims.append(anim)
        anim.start()

    def wobble(self, duration_ms: int = 800):
        # horizontal shake around current position
        anim = QVariantAnimation()
        anim.setDuration(max(200, duration_ms))
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        origin = QPointF(self.pos())
        amplitude = 10.0
        freq = 8  # shakes

        def on_val(v: float):
            dx = amplitude * math.sin(2 * math.pi * freq * v)
            self.setPos(QPointF(origin.x() + dx, origin.y()))

        def on_finish():
            self.setPos(origin)
            if anim in self._anims:
                self._anims.remove(anim)

        anim.valueChanged.connect(on_val)
        anim.finished.connect(on_finish)
        self._anims.append(anim)
        anim.start()
