from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QHBoxLayout, QPushButton
from PyQt5.QtGui import QIcon, QPixmap
import os, json


class InventoryPage(QWidget):
    def __init__(self, project_root: str, on_back=None):
        super().__init__()
        self.project_root = project_root
        self.on_back = on_back
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        root.addLayout(top)
        btn_back = QPushButton("返回")
        btn_back.clicked.connect(lambda: self.on_back() if callable(self.on_back) else None)
        top.addWidget(btn_back, alignment=Qt.AlignLeft)

        self.lbl_diamond = QLabel("钻石 0")
        self.lbl_diamond.setStyleSheet("border:2px solid red; padding:4px 8px; border-radius:6px; color:red; font-weight:600;")
        top.addWidget(self.lbl_diamond, alignment=Qt.AlignLeft)
        top.addStretch(1)

        title = QLabel("背包（已拥有技能卡）")
        title.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        root.addWidget(title)

        self.list = QListWidget()
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setMovement(QListWidget.Static)
        self.list.setSpacing(8)
        self.list.setIconSize(QSize(84, 108))
        root.addWidget(self.list)

        self.reload()

    def _resolve(self, rel):
        if os.path.isabs(rel):
            return rel
        return os.path.join(self.project_root, rel)

    def reload(self):
        # update diamonds
        try:
            with open(self._resolve('data/player.json'), 'r', encoding='utf-8') as f:
                import json as _json
                d = _json.load(f)
                v = int(d.get('diamonds', 0))
        except Exception:
            v = 0
        self.lbl_diamond.setText(f"钻石 {v}")

        self.list.clear()
        cfg_path = os.path.join(self.project_root, 'data', 'skillscard.json')
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                cards = json.load(f).get('cards', [])
        except Exception:
            cards = []
        for c in cards:
            img = self._resolve(c.get('image', ''))
            pix = QPixmap(img)
            if pix.isNull():
                pix = QPixmap(84, 108)
                pix.fill(Qt.gray)
            item = QListWidgetItem(QIcon(pix), f"{c.get('label','')}\nCost {c.get('cost',0)}")
            item.setData(Qt.UserRole, c.get('id'))
            self.list.addItem(item)
