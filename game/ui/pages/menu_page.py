from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSizePolicy


class MenuPage(QWidget):
    def __init__(self, on_nav):
        super().__init__()
        self.on_nav = on_nav
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        self.title = QLabel("Gacha slay")
        self.title.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.title.setStyleSheet("font-size: 28px; font-weight: 700;")
        root.addWidget(self.title)

        center = QVBoxLayout()
        center.setSpacing(12)
        center.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        root.addLayout(center)

        def mkbtn(text, key):
            b = QPushButton(text)
            b.setFixedWidth(220)
            b.setFixedHeight(40)
            b.clicked.connect(lambda: self.on_nav(key))
            center.addWidget(b, alignment=Qt.AlignHCenter)
            return b

        mkbtn("抽卡", "gacha")
        mkbtn("背包", "inventory")
        mkbtn("卡组", "deck")
        mkbtn("战斗", "stage")
        mkbtn("结束游戏", "exit")
