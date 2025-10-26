from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QMessageBox
import os
import json
import random
from ...save.save_manager import SaveManager


class GachaPage(QWidget):
    def __init__(self, save: SaveManager, on_back=None):
        super().__init__()
        self.on_back = on_back
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.save = save

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

        title = QLabel("抽卡")
        title.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        root.addWidget(title)

        ctrls = QHBoxLayout()
        root.addLayout(ctrls)
        self.btn_single = QPushButton("单抽（10钻）")
        self.btn_ten = QPushButton("十连（100钻）")
        self.btn_single.clicked.connect(self._do_single)
        self.btn_ten.clicked.connect(self._do_ten)
        ctrls.addStretch(1)
        ctrls.addWidget(self.btn_single)
        ctrls.addWidget(self.btn_ten)
        ctrls.addStretch(1)

        self.list = QListWidget()
        root.addWidget(self.list)

        self._load_pool()
        self._refresh()

    def _refresh(self):
        self.lbl_diamond.setText(f"钻石 {self.save.get_diamonds()}")

    def _load_pool(self):
        # load all card ids from skillscard.json
        try:
            with open(os.path.join(self.project_root, 'data', 'skillscard.json'), 'r', encoding='utf-8') as f:
                self.all_cards = [c.get('id') for c in json.load(f).get('cards', []) if c.get('id')]
        except Exception:
            self.all_cards = []
        # initial deck should only have base five; pool includes新加入的四张及基础五张也可被抽取

    def _do_single(self):
        if not self.save.spend_diamonds(10):
            QMessageBox.warning(self, "提示", "钻石不足")
            return
        self.save.inc_gacha_single(1)
        results = self._roll_once()
        self._apply_results(results)
        self._show_results(results)
        self._refresh()

    def _do_ten(self):
        if not self.save.spend_diamonds(100):
            QMessageBox.warning(self, "提示", "钻石不足")
            return
        self.save.inc_gacha_ten(1)
        all_results = []
        for _ in range(10):
            all_results.append(self._roll_once())
        # apply aggregate
        for r in all_results:
            self._apply_results(r)
        # show
        self.list.clear()
        for r in all_results:
            self._append_result_item(r)
        self._refresh()

    def _roll_once(self):
        # probabilities:
        # 50% +1 diamond, 20% +1 card, 5% +3 diamonds, 3% +8 diamonds, 2% +3 cards, else 20% no reward
        x = random.random()
        if x < 0.50:
            return {"diamonds": 1}
        x -= 0.50
        if x < 0.20:
            return {"cards": [self._rand_card()]}
        x -= 0.20
        if x < 0.05:
            return {"diamonds": 3}
        x -= 0.05
        if x < 0.03:
            return {"diamonds": 8}
        x -= 0.03
        if x < 0.02:
            return {"cards": [self._rand_card(), self._rand_card(), self._rand_card()]}
        return {"none": True}

    def _rand_card(self) -> str:
        if not self.all_cards:
            return ""
        return random.choice(self.all_cards)

    def _apply_results(self, r: dict):
        if 'diamonds' in r:
            self.save.add_diamonds(int(r['diamonds']))
        if 'cards' in r:
            self.save.add_cards([c for c in r['cards'] if c])

    def _append_result_item(self, r: dict):
        if 'none' in r:
            txt = "未获得奖励"
        elif 'diamonds' in r:
            txt = f"获得 钻石 +{r['diamonds']}"
        elif 'cards' in r:
            items = ', '.join(r['cards'])
            txt = f"获得 卡牌：{items}"
        else:
            txt = str(r)
        self.list.addItem(QListWidgetItem(txt))

    def _show_results(self, r: dict):
        self.list.clear()
        self._append_result_item(r)
