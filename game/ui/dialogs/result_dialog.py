from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout


class ResultDialog(QDialog):
    def __init__(self, payload: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("战斗结算")
        self.setModal(True)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        result = payload.get("result")
        stats = payload.get("stats", {})
        rewards = payload.get("rewards", {})

        title = QLabel("胜利" if result == "win" else "失败")
        title.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        title.setStyleSheet("font-size:22px; font-weight:700;")
        root.addWidget(title)

        s_rounds = stats.get("rounds", 0)
        s_dealt = stats.get("damage_dealt", 0)
        s_taken = stats.get("damage_taken", 0)

        lab_stats = QLabel(f"回合数: {s_rounds}\n造成伤害: {s_dealt}\n受到伤害: {s_taken}")
        root.addWidget(lab_stats)

        dia = rewards.get("diamonds", 0)
        prev_d = rewards.get("prev_diamonds")
        new_d = rewards.get("new_diamonds")
        lab_rewards = QLabel(f"奖励: 钻石 +{dia}")
        lab_rewards.setStyleSheet("color:#d4af37; font-weight:600;")
        root.addWidget(lab_rewards)

        if prev_d is not None and new_d is not None:
            lab_now = QLabel(f"背包钻石: {prev_d} -> {new_d}")
            lab_now.setStyleSheet("color:red; font-weight:700;")
            root.addWidget(lab_now)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_back = QPushButton("返回")
        btn_back.setFixedWidth(120)
        btn_back.clicked.connect(self.accept)
        btn_row.addWidget(btn_back, alignment=Qt.AlignHCenter)
        btn_row.addStretch(1)
        root.addLayout(btn_row)
