from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QStackedWidget, QMessageBox, QTextEdit, QDialog, QInputDialog
)
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QSurfaceFormat
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import QTimer

from game.battle.battle_view import BattleView
from game.battle.battle_controller import BattleController
from .pages.menu_page import MenuPage
from .pages.gacha_page import GachaPage
from ..save.save_manager import SaveManager
from .pages.inventory_page import InventoryPage
from .dialogs.result_dialog import ResultDialog
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gacha slay")
        self.resize(960, 600)

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stacked pages
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Initialize save/profile
        self.save = self._init_save()

        # Pages
        self.menu_page = MenuPage(self._on_nav)
        self.gacha_page = GachaPage(self.save, on_back=self._back_to_menu)
        self.inventory_page = InventoryPage(self._project_root(), on_back=self._back_to_menu)
        # Deck/Stage pages will be created below

        self.stack.addWidget(self.menu_page)      # index 0
        self.stack.addWidget(self.gacha_page)     # index 1
        self.stack.addWidget(self.inventory_page) # index 2

        # Deck page placeholder; set later
        self.deck_page = None
        # Stage page placeholder; set later
        self.stage_page = None

        # Battle page container
        self.battle_container = QWidget(self)
        battle_layout = QVBoxLayout(self.battle_container)
        battle_layout.setContentsMargins(0, 0, 8, 8)

        # Top row with Pause button on right
        top_row = QHBoxLayout()
        top_row.setContentsMargins(8, 8, 8, 0)
        battle_layout.addLayout(top_row)
        top_row.addStretch(1)
        self.btn_pause = QPushButton("暂停")
        self.btn_pause.setFixedWidth(80)
        top_row.addWidget(self.btn_pause)

        # Log area (actions info)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(150)
        self.txt_log.setStyleSheet("background: #1e1e1e; color: #ddd;")
        battle_layout.addWidget(self.txt_log)

        self.view = BattleView(self)
        battle_layout.addWidget(self.view)

        # Bottom controls (only visible on battle page)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.setContentsMargins(0, 0, 0, 0)
        battle_layout.addLayout(btn_row)

        self.lbl_energy = QLabel("能量 0/0")
        self.lbl_energy.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        btn_row.addWidget(self.lbl_energy)

        self.btn_end_turn = QPushButton("结束回合")
        self.btn_end_turn.setFixedHeight(36)
        self.btn_end_turn.setCursor(Qt.PointingHandCursor)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_end_turn)

        self.stack.addWidget(self.battle_container)  # index 3 (battle)

        self.setCentralWidget(container)

        # Controller (created on entering battle)
        self.controller: BattleController | None = None

        # Initially show menu
        self.stack.setCurrentIndex(0)

    def _project_root(self) -> str:
        # .../game/ui/main_window.py -> project root
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def _init_save(self) -> SaveManager:
        root = self._project_root()
        username, ok = QInputDialog.getText(self, "选择存档", "请输入用户名：", text="player")
        if not ok:
            username = "player"
        sm = SaveManager(root, username)
        # ensure snapshot written
        # SaveManager already flushes on load
        return sm

    def _on_nav(self, key: str):
        if key == "gacha":
            self.stack.setCurrentIndex(1)
        elif key == "inventory":
            self.inventory_page.reload()
            self.stack.setCurrentIndex(2)
        elif key == "deck":
            self._ensure_deck_page()
            self.stack.setCurrentIndex(self.stack.indexOf(self.deck_page))
        elif key == "stage":
            self._ensure_stage_page()
            self.stack.setCurrentIndex(self.stack.indexOf(self.stage_page))
        elif key == "exit":
            self.close()

    def _ensure_deck_page(self):
        if self.deck_page is not None:
            return
        from .pages.deck_page import DeckPage
        self.deck_page = DeckPage(self._project_root(), on_back=self._back_to_menu)
        self.stack.addWidget(self.deck_page)

    def _ensure_stage_page(self):
        if self.stage_page is not None:
            return
        from .pages.stage_page import StagePage
        self.stage_page = StagePage(on_pick=self._start_battle, on_back=self._back_to_menu)
        self.stack.addWidget(self.stage_page)

    def _start_battle(self, stage_id: int):
        # init controller lazily
        if self.controller is None:
            self.controller = BattleController(self.view)
            try:
                self.controller.load_demo_stage()
            except Exception as e:
                QMessageBox.critical(self, "Load Error", str(e))
            self.btn_end_turn.clicked.connect(self.controller.end_player_turn)
            self.controller.set_energy_label(self.lbl_energy)
            # battle end handler
            def on_end(payload):
                # payload: {result, stats, rewards}
                try:
                    dlg = ResultDialog(payload, self)
                    dlg.exec_()
                except Exception:
                    # fallback simple message
                    result = payload.get('result') if isinstance(payload, dict) else str(payload)
                    if result == 'win':
                        QMessageBox.information(self, "胜利", "战斗胜利！")
                    else:
                        QMessageBox.warning(self, "失败", "战斗失败…")
                # back to stage list
                self.stack.setCurrentIndex(self.stack.indexOf(self.stage_page))
            self.controller.on_end = on_end
            # log wiring
            self.controller.log_fn = self._append_log

            # pause button
            self.btn_pause.clicked.connect(self._show_pause_dialog)

        self.stack.setCurrentIndex(self.stack.indexOf(self.battle_container))
        self.txt_log.clear()
        QTimer.singleShot(50, self.controller.start_battle)

    def _back_to_menu(self):
        self.stack.setCurrentIndex(self.stack.indexOf(self.menu_page))

    def _append_log(self, text: str):
        if not isinstance(text, str):
            return
        self.txt_log.append(text)

    def _show_pause_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("暂停")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        btn_cont = QPushButton("继续战斗")
        btn_exit = QPushButton("退出战斗")
        btn_cont.clicked.connect(dlg.accept)
        def _exit():
            dlg.accept()
            # return to stage list
            self.stack.setCurrentIndex(self.stack.indexOf(self.stage_page))
        btn_exit.clicked.connect(_exit)
        lay.addWidget(btn_cont)
        lay.addWidget(btn_exit)
        dlg.exec_()
