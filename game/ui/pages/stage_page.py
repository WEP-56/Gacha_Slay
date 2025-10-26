from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QPushButton, QHBoxLayout


class StagePage(QWidget):
    def __init__(self, on_pick, on_back=None):
        super().__init__()
        self.on_pick = on_pick
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

        title = QLabel("选择关卡")
        title.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(8)
        root.addLayout(grid)

        total = 40
        per_row = 5
        for i in range(total):
            r = i // per_row
            c = i % per_row
            idx = i + 1
            btn = QPushButton(str(idx))
            btn.setFixedSize(80, 80)
            if idx == 1:
                btn.setEnabled(True)
                btn.clicked.connect(lambda _, sid=idx: self.on_pick(sid))
            else:
                btn.setEnabled(False)
            grid.addWidget(btn, r, c)
