import os
import json
from typing import List, Dict, Any


class SaveManager:
    def __init__(self, project_root: str, username: str):
        self.project_root = project_root
        self.username = (username or 'player').strip() or 'player'
        self.saves_dir = os.path.join(project_root, 'data', 'saves')
        self.user_path = os.path.join(self.saves_dir, f'{self.username}.json')
        # snapshot for legacy readers (inventory/battle)
        self.snapshot_path = os.path.join(project_root, 'data', 'player.json')
        self.state: Dict[str, Any] = {}
        self._ensure_loaded()

    def _default_state(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "diamonds": 1000,
            "owned_cards": [
                "attack_basic",
                "defend_basic",
                "heal_basic",
                "vulnerable_basic",
                "heavy_strike"
            ],
            "deck": [
                "attack_basic",
                "defend_basic",
                "vulnerable_basic",
                "heal_basic",
                "heavy_strike"
            ],
            "gacha": {
                "single": 0,
                "ten": 0
            },
            "playtime_seconds": 0,
            "progress": {
                "stages": {}
            }
        }

    def _ensure_loaded(self):
        os.makedirs(self.saves_dir, exist_ok=True)
        if not os.path.exists(self.user_path):
            self.state = self._default_state()
            self._flush()
        else:
            try:
                with open(self.user_path, 'r', encoding='utf-8') as f:
                    self.state = json.load(f)
            except Exception:
                self.state = self._default_state()
                self._flush()

    def _flush(self):
        # write user profile
        os.makedirs(self.saves_dir, exist_ok=True)
        with open(self.user_path, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
        # write snapshot for legacy readers
        os.makedirs(os.path.dirname(self.snapshot_path), exist_ok=True)
        with open(self.snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    # currency
    def get_diamonds(self) -> int:
        return int(self.state.get('diamonds', 0))

    def add_diamonds(self, amount: int) -> int:
        cur = self.get_diamonds()
        cur += int(amount)
        if cur < 0:
            cur = 0
        self.state['diamonds'] = cur
        self._flush()
        return cur

    def spend_diamonds(self, amount: int) -> bool:
        cur = self.get_diamonds()
        if cur < amount:
            return False
        self.state['diamonds'] = cur - amount
        self._flush()
        return True

    # cards
    def get_owned(self) -> List[str]:
        return list(self.state.get('owned_cards', []))

    def add_cards(self, ids: List[str]):
        owned = set(self.state.get('owned_cards', []))
        for i in ids:
            if i:
                owned.add(i)
        self.state['owned_cards'] = sorted(list(owned))
        self._flush()

    # deck
    def get_deck(self) -> List[str]:
        return list(self.state.get('deck', []))

    def set_deck(self, ids: List[str]):
        self.state['deck'] = list(ids)
        self._flush()

    # gacha stats
    def inc_gacha_single(self, n: int = 1):
        g = self.state.setdefault('gacha', {"single": 0, "ten": 0})
        g['single'] = int(g.get('single', 0)) + n
        self._flush()

    def inc_gacha_ten(self, n: int = 1):
        g = self.state.setdefault('gacha', {"single": 0, "ten": 0})
        g['ten'] = int(g.get('ten', 0)) + n
        self._flush()

    # time/progress
    def add_playtime(self, seconds: int):
        self.state['playtime_seconds'] = int(self.state.get('playtime_seconds', 0)) + int(seconds)
        self._flush()

    def set_stage_progress(self, stage_id: str, status: str):
        prog = self.state.setdefault('progress', {}).setdefault('stages', {})
        prog[str(stage_id)] = status
        self._flush()
