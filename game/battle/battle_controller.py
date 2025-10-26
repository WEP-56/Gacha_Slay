from PyQt5.QtCore import QTimer, QPointF
from .battle_view import BattleView
from .card_item import CardItem
from .skill_card_item import SkillCardItem
import os
import json
from PyQt5.QtWidgets import QLabel
import random
from types import SimpleNamespace


class BattleController:
    def __init__(self, view: BattleView):
        self.view = view
        self.scene = view.battle_scene
        # manual turn-based
        self.turn = 0  # even: player, odd: enemy
        self.player: CardItem = None
        self.enemy: CardItem = None
        self.skill_cards = []
        # __file__ = .../game/battle/battle_controller.py; go up two to reach project root
        self._project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        # energy
        self.energy_max = 5
        self.energy = 5
        self._energy_label: QLabel | None = None
        # end callback
        self.on_end = None
        self._battle_result = None  # 'win' or 'lose'
        # visuals
        self._slot_bg_items = []
        # stats
        self.rounds = 0
        self.damage_dealt = 0
        self.damage_taken = 0
        # logger
        self.log_fn = None

    def load_demo_stage(self):
        # Resolve project root from this file: .../game/battle/battle_controller.py -> project root
        assets_dir = os.path.join(self._project_root, "assets", "Card")
        assets_dir = os.path.abspath(assets_dir)
        face = os.path.join(assets_dir, "FrontTexture.png")
        enemy_face = os.path.join(assets_dir, "Plastic1.png")
        print(f"[BattleController] Hero image path: {face} exists={os.path.exists(face)}")
        print(f"[BattleController] Enemy image path: {enemy_face} exists={os.path.exists(enemy_face)}")

        self.player = CardItem(face, name="Hero", max_hp=120, atk=25)
        self.enemy = CardItem(enemy_face, name="Slime", max_hp=100, atk=18)

        self.scene.addItem(self.player)
        self.scene.addItem(self.enemy)

        # layout: hero further left, slime further right
        self.player.setPos(100, 150)
        self.enemy.setPos(650, 150)

        # load hero energy_max from data/cards.json if available
        try:
            with open(os.path.join(self._project_root, "data", "cards.json"), "r", encoding="utf-8") as f:
                cards_cfg = json.load(f).get("cards", [])
                for c in cards_cfg:
                    if c.get("name") == "Hero" and "energy_max" in c:
                        self.energy_max = int(c["energy_max"]) or 5
                        break
        except Exception:
            pass
        self.energy = self.energy_max

    def start_battle(self):
        self.turn = 0  # player turn
        self.rounds = 0
        self.damage_dealt = 0
        self.damage_taken = 0
        self.start_player_turn()

    def stop_battle(self):
        # nothing periodic now
        pass

    def create_skill_cards(self):
        scene_rect = self.scene.sceneRect()
        # fixed five slots; card size 84x108
        card_w, card_h = 84, 108
        spacing = 16
        # load definitions
        data_dir = os.path.join(self._project_root, "data")
        cfg_path = os.path.join(data_dir, "skillscard.json")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                defs = cfg.get("cards", [])
        except Exception:
            defs = []
        # map by id for deck resolution
        defs_by_id = {c.get("id"): c for c in defs if c.get("id")}
        # load effect logic
        logic = self._load_effect_logic()
        # read deck: prefer player.json deck, fallback to deck.json
        deck_ids = []
        try:
            with open(os.path.join(self._project_root, "data", "player.json"), "r", encoding="utf-8") as f:
                deck_ids = json.load(f).get("deck", [])
        except Exception:
            try:
                with open(os.path.join(self._project_root, "data", "deck.json"), "r", encoding="utf-8") as f:
                    deck_ids = json.load(f).get("deck", [])
            except Exception:
                deck_ids = []
        # build pool from deck (fallback to all defs)
        pool = [defs_by_id[i] for i in deck_ids if i in defs_by_id] or list(defs)
        # pick up to 5 cards without replacement; if不足5则留空
        chosen: list[dict] = []
        if len(pool) > 0:
            chosen = random.sample(pool, min(5, len(pool)))

        # compute layout for exactly five slots
        n = 5
        total_w = card_w * n + spacing * (n - 1)
        start_x = (scene_rect.width() - total_w) / 2
        y = scene_rect.height() - card_h - 12

        # draw slot backgrounds (5 fixed positions)
        self._draw_slot_backgrounds(start_x, y, card_w, card_h, spacing)

        # helper target checks
        def collides(a_item, b_item):
            try:
                return a_item.collidesWithItem(b_item)
            except Exception:
                # fallback: bounding box check
                return a_item.mapToScene(a_item.boundingRect()).boundingRect().intersects(
                    b_item.mapToScene(b_item.boundingRect()).boundingRect()
                )

        # helpers
        def resolve_image(rel_path: str) -> str:
            # allow assets/... relative to project root
            if os.path.isabs(rel_path):
                return rel_path
            return os.path.join(self._project_root, rel_path.replace("/", os.sep))

        def add_card(idx: int, cdef: dict):
            label = cdef.get("label", "")
            img = resolve_image(cdef.get("image", ""))
            cost = int(cdef.get("cost", 0))
            origin = QPointF(start_x + idx * (card_w + spacing), y)
            effects = cdef.get("effects", [])

            # decide required target: if any effect targets enemy -> enemy, else self
            required_target = 'self'
            for e in effects:
                ename = e.get('name')
                ed = logic.get('effects', {}).get(ename, {})
                if ed.get('target') == 'enemy':
                    required_target = 'enemy'
                    break

            def is_valid(item: SkillCardItem):
                if required_target == 'enemy':
                    return collides(item, self.enemy)
                else:
                    return collides(item, self.player)

            def apply(item: SkillCardItem):
                if not self.spend_energy(cost):
                    return False
                # execute all declared effects
                for eff in effects:
                    ename = eff.get('name')
                    params = dict(eff)
                    edef = logic.get('effects', {}).get(ename, {})
                    self._execute_effect(edef, params, label)
                return True

            card = SkillCardItem(card_w, card_h, label, origin, apply, is_valid, img)
            self.scene.addItem(card)
            self.skill_cards.append(card)
            try:
                card.appear(220)
            except Exception:
                pass

        for i in range(5):
            if i < len(chosen):
                add_card(i, chosen[i])
            else:
                # empty slot; no card
                pass

    def clear_skill_cards(self):
        for c in list(self.skill_cards):
            try:
                self.scene.removeItem(c)
            except Exception:
                pass
        self.skill_cards.clear()

    def start_player_turn(self):
        if self.player.is_dead() or self.enemy.is_dead():
            self.on_battle_end()
            return
        self.turn = 0
        self.rounds += 1
        # refill energy at start of player's turn
        self.energy = self.energy_max
        self.update_energy_label()
        self.clear_skill_cards()
        self.create_skill_cards()

    def end_player_turn(self):
        # player indicates end of turn
        self.clear_skill_cards()
        self.enemy_turn()

    def enemy_turn(self):
        if self.player.is_dead() or self.enemy.is_dead():
            self.on_battle_end()
            return
        attacker = self.enemy
        defender = self.player

        def on_hit():
            prev_hp, prev_shield = defender.hp, defender.shield
            hp_left = defender.take_damage(attacker.atk)
            defender.play_hit_fx()
            dealt = (prev_hp + prev_shield) - (defender.hp + defender.shield)
            self.damage_taken += max(0, int(dealt))
            if callable(self.log_fn):
                try:
                    self.log_fn(f"{attacker.name} 攻击了 {defender.name}，造成了 {max(0,int(dealt))} 点伤害")
                except Exception:
                    pass
            if hp_left <= 0:
                # player died -> lose
                self._battle_result = 'lose' if defender is self.player else 'win'
                self.on_battle_end()
                return
            # back to player's turn after enemy completes
            QTimer.singleShot(250, self.start_player_turn)

        attacker.charge_attack(defender.pos(), on_hit)

    def on_battle_end(self):
        self.clear_skill_cards()
        if callable(self.on_end):
            try:
                rewards = {}
                if self._battle_result == 'win':
                    rewards = {"diamonds": 5}
                    # persist to data/player.json
                    try:
                        ppath = os.path.join(self._project_root, 'data', 'player.json')
                        import json as _json
                        data = {}
                        if os.path.exists(ppath):
                            with open(ppath, 'r', encoding='utf-8') as f:
                                data = _json.load(f)
                        cur = int(data.get('diamonds', 0))
                        new_val = cur + rewards['diamonds']
                        data['diamonds'] = new_val
                        with open(ppath, 'w', encoding='utf-8') as f:
                            _json.dump(data, f, ensure_ascii=False, indent=2)
                        rewards['prev_diamonds'] = cur
                        rewards['new_diamonds'] = new_val
                    except Exception:
                        pass
                payload = {
                    "result": self._battle_result,
                    "stats": {
                        "rounds": self.rounds,
                        "damage_dealt": self.damage_dealt,
                        "damage_taken": self.damage_taken,
                    },
                    "rewards": rewards,
                }
                self.on_end(payload)
            except Exception:
                pass

    def _draw_slot_backgrounds(self, start_x: float, y: float, w: int, h: int, spacing: int):
        # remove old
        for it in list(self._slot_bg_items):
            try:
                self.scene.removeItem(it)
            except Exception:
                pass
        self._slot_bg_items.clear()
        try:
            from PyQt5.QtWidgets import QGraphicsRectItem
            from PyQt5.QtGui import QColor, QPen
        except Exception:
            return
        for i in range(5):
            rx = start_x + i * (w + spacing)
            rect = QGraphicsRectItem(rx - 2, y - 2, w + 4, h + 28)  # include label space
            rect.setBrush(QColor(40, 40, 40, 80))
            rect.setPen(QPen(QColor(120, 120, 120)))
            rect.setZValue(10)
            self.scene.addItem(rect)
            self._slot_bg_items.append(rect)

    # --- data-driven effect engine ---
    def _load_effect_logic(self) -> dict:
        try:
            with open(os.path.join(self._project_root, 'data', 'skillcardLogic.json'), 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"effects": {}}

    def _compute_formula(self, formula: str, source: CardItem, target: CardItem, params: dict) -> int:
        # safe eval with restricted namespace
        safe_globals = {"__builtins__": {}}
        safe_globals.update({"round": round, "min": min, "max": max})
        safe_locals = {
            "source": SimpleNamespace(
                atk=int(getattr(source, 'atk', 0) + getattr(source, 'strength', 0)),
                max_hp=int(getattr(source, 'max_hp', 0)),
                hp=int(getattr(source, 'hp', 0)),
                shield=int(getattr(source, 'shield', 0)),
            ),
            "target": SimpleNamespace(
                atk=int(getattr(target, 'atk', 0)) if target else 0,
                max_hp=int(getattr(target, 'max_hp', 0)) if target else 0,
                hp=int(getattr(target, 'hp', 0)) if target else 0,
                shield=int(getattr(target, 'shield', 0)) if target else 0,
            ),
            "multiplier": float(params.get('multiplier', 1.0)),
        }
        try:
            val = eval(formula, safe_globals, safe_locals)
            return int(val)
        except Exception:
            return 0

    def _execute_effect(self, edef: dict, params: dict, label: str):
        etarget = edef.get('target', 'enemy')
        apply_kind = edef.get('apply')
        formula = edef.get('formula', '0')
        log_tpl = edef.get('log', '')
        src = self.player
        tgt = self.enemy if etarget == 'enemy' else self.player

        # compute value
        value = self._compute_formula(formula, src, tgt, params)

        if apply_kind == 'damage':
            # play attack animation then apply hit
            prev_hp, prev_shield = tgt.hp, tgt.shield

            def on_hit():
                hp_left = tgt.take_damage(max(0, int(value)))
                tgt.play_hit_fx()
                dealt = (prev_hp + prev_shield) - (tgt.hp + tgt.shield)
                self.damage_dealt += max(0, int(dealt))
                # log after knowing real dealt
                if callable(self.log_fn) and log_tpl:
                    try:
                        target_name = tgt.name if hasattr(tgt, 'name') else '目标'
                        txt = log_tpl.format(label=label, value=int(dealt), target_name=target_name)
                        self.log_fn(txt)
                    except Exception:
                        pass

            self.player.charge_attack(tgt.pos(), on_hit)
            return
        elif apply_kind == 'damage_n':
            # multi-hit without repeated charge; apply sequential hits
            times = int(params.get('times', 2))
            total_dealt = 0
            for _ in range(max(1, times)):
                prev_hp, prev_shield = tgt.hp, tgt.shield
                hp_left = tgt.take_damage(max(0, int(value)))
                try:
                    tgt.play_hit_fx()
                except Exception:
                    pass
                dealt = (prev_hp + prev_shield) - (tgt.hp + tgt.shield)
                total_dealt += max(0, int(dealt))
                if hp_left <= 0:
                    break
            self.damage_dealt += total_dealt
            if callable(self.log_fn) and log_tpl:
                try:
                    target_name = tgt.name if hasattr(tgt, 'name') else '目标'
                    txt = log_tpl.format(label=label, value=int(total_dealt), target_name=target_name)
                    self.log_fn(txt)
                except Exception:
                    pass
        elif apply_kind == 'heal':
            src.heal(max(0, int(value)))
            try:
                src.heartbeat(times=3, duration_ms=800)
            except Exception:
                pass
        elif apply_kind == 'shield':
            src.add_shield(max(0, int(value)))
            try:
                src.heartbeat(times=3, duration_ms=1000)
            except Exception:
                pass
        elif apply_kind == 'lifesteal':
            # deal damage, then heal same amount actually dealt
            prev_hp, prev_shield = tgt.hp, tgt.shield
            def on_hit():
                hp_left = tgt.take_damage(max(0, int(value)))
                try:
                    tgt.play_hit_fx()
                except Exception:
                    pass
                dealt = (prev_hp + prev_shield) - (tgt.hp + tgt.shield)
                dealt = max(0, int(dealt))
                self.damage_dealt += dealt
                if dealt > 0:
                    src.heal(dealt)
                if callable(self.log_fn) and log_tpl:
                    try:
                        target_name = tgt.name if hasattr(tgt, 'name') else '目标'
                        txt = log_tpl.format(label=label, value=int(dealt), target_name=target_name)
                        self.log_fn(txt)
                    except Exception:
                        pass
            self.player.charge_attack(tgt.pos(), on_hit)
            return
        elif apply_kind == 'set_next_damage_taken_multiplier':
            try:
                tgt.next_damage_taken_multiplier = float(params.get('multiplier', 1.0))
                tgt.wobble(duration_ms=800)
            except Exception:
                pass
        elif apply_kind == 'gain_energy':
            val = max(0, int(value))
            self.energy = min(self.energy_max, self.energy + val)
            self.update_energy_label()
        elif apply_kind == 'add_strength':
            add = max(0, int(value))
            cur = int(getattr(self.player, 'strength', 0))
            setattr(self.player, 'strength', cur + add)
            try:
                self.player.heartbeat(times=2, duration_ms=600)
            except Exception:
                pass
        # log immediate effects
        if apply_kind != 'damage' and callable(self.log_fn) and log_tpl:
            try:
                target_name = tgt.name if hasattr(tgt, 'name') else '目标'
                txt = log_tpl.format(label=label, value=int(value), target_name=target_name)
                self.log_fn(txt)
            except Exception:
                pass

    # energy helpers and UI
    def set_energy_label(self, lbl: QLabel):
        self._energy_label = lbl
        self.update_energy_label()

    def update_energy_label(self):
        if self._energy_label is not None:
            self._energy_label.setText(f"能量 {self.energy}/{self.energy_max}")

    def spend_energy(self, cost: int) -> bool:
        cost = max(0, int(cost))
        if self.energy < cost:
            # not enough
            return False
        self.energy -= cost
        self.update_energy_label()
        return True
