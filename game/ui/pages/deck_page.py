from PyQt5.QtCore import Qt, QSize, QMimeData
from PyQt5.QtGui import QIcon, QPixmap, QDrag
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QHBoxLayout, QPushButton, QFrame
)
import os, json


class DropSlot(QLabel):
    def __init__(self, index: int, get_all_slots):
        super().__init__("空")
        self.index = index
        self._get_all_slots = get_all_slots
        self.setFixedSize(92, 120)
        self.setFrameShape(QFrame.StyledPanel)
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.card_id = None
        self.pixmap_cache = None

    def dragEnterEvent(self, e):
        md = e.mimeData()
        if md.hasText():
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        md = e.mimeData()
        cid = md.text()
        # prevent duplicates across slots
        for s in self._get_all_slots():
            if s is not self and s.card_id == cid:
                e.ignore()
                return
        pix = e.source().icon().pixmap(84, 108) if hasattr(e.source(), 'icon') else None
        self.card_id = cid
        self.pixmap_cache = pix
        if pix is not None and not pix.isNull():
            self.setPixmap(pix.scaled(84, 108, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.setText(cid)
        e.acceptProposedAction()

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            # clear
            self.card_id = None
            self.pixmap_cache = None
            self.setPixmap(QPixmap())
            self.setText("空")
        else:
            super().mousePressEvent(e)


class DeckPage(QWidget):
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
        top.addStretch(1)

        title = QLabel("卡组编辑（最多10张）")
        title.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        root.addWidget(title)

        # slots row
        slots_row = QHBoxLayout()
        slots_row.setSpacing(6)
        root.addLayout(slots_row)
        self.slots = [DropSlot(i, lambda: self.slots) for i in range(10)]
        for s in self.slots:
            slots_row.addWidget(s)

        # all skills list
        self.list = QListWidget()
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setMovement(QListWidget.Static)
        self.list.setSpacing(8)
        self.list.setIconSize(QSize(84, 108))
        self.list.setDragEnabled(True)
        root.addWidget(self.list)

        # save button
        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self.btn_save = QPushButton("保存卡组")
        self.btn_save.clicked.connect(self.save_deck)
        save_row.addWidget(self.btn_save)
        save_row.addStretch(1)
        root.addLayout(save_row)

        self.reload_cards()
        self.load_deck()

        # enable dragging from list
        self.list.mouseMoveEvent = self._list_mouse_move

    def _resolve(self, rel):
        if os.path.isabs(rel):
            return rel
        return os.path.join(self.project_root, rel)

    def reload_cards(self):
        self.list.clear()
        try:
            with open(self._resolve('data/skillscard.json'), 'r', encoding='utf-8') as f:
                cards = json.load(f).get('cards', [])
        except Exception:
            cards = []
        for c in cards:
            img = self._resolve(c.get('image', ''))
            pix = QPixmap(img)
            if pix.isNull():
                pix = QPixmap(84, 108)
                pix.fill(Qt.gray)
            it = QListWidgetItem(QIcon(pix), f"{c.get('label','')}\nCost {c.get('cost',0)}")
            it.setData(Qt.UserRole, c.get('id'))
            self.list.addItem(it)

    def load_deck(self):
        # place existing deck into slots
        for s in self.slots:
            s.card_id = None
            s.setPixmap(QPixmap())
            s.setText("空")
        try:
            with open(self._resolve('data/deck.json'), 'r', encoding='utf-8') as f:
                ids = json.load(f).get('deck', [])
        except Exception:
            ids = []
        # build icon lookup
        icon_map = {}
        for i in range(self.list.count()):
            item = self.list.item(i)
            icon_map[item.data(Qt.UserRole)] = item.icon().pixmap(84, 108)
        for i, cid in enumerate(ids[:10]):
            self.slots[i].card_id = cid
            pix = icon_map.get(cid)
            if pix is not None:
                self.slots[i].setPixmap(pix)
            else:
                self.slots[i].setText(cid)

    def _list_mouse_move(self, e):
        item = self.list.currentItem()
        if not item:
            return
        drag = QDrag(self.list)
        mime = QMimeData()
        mime.setText(item.data(Qt.UserRole))
        drag.setMimeData(mime)
        drag.setPixmap(item.icon().pixmap(84, 108))
        drag.exec_(Qt.MoveAction)

    def save_deck(self):
        deck_ids = [s.card_id for s in self.slots if s.card_id]
        with open(self._resolve('data/deck.json'), 'w', encoding='utf-8') as f:
            json.dump({"deck": deck_ids}, f, ensure_ascii=False, indent=2)
