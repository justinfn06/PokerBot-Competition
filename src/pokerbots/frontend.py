from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from bot_base import BaseBot
from engine import PokerEngine

TABLE_BG = "#0f3d2e"
TABLE_ALT = "#164f3c"
PANEL_BG = "#f3efe3"
PANEL_ALT = "#e1d7bb"
TEXT_DARK = "#1f1a17"
TEXT_LIGHT = "#f8f4ec"
ACCENT = "#d8b45a"
SUCCESS = "#317a56"
WARNING = "#9a5a2b"
DANGER = "#8b3131"


class MatchController:
    def __init__(
        self,
        bots: list[BaseBot],
        hand_count: int,
        starting_stack: int,
        small_blind: int,
        big_blind: int,
    ) -> None:
        self.engine = PokerEngine(
            bots=bots,
            starting_stack=starting_stack,
            small_blind=small_blind,
            big_blind=big_blind,
            verbose=False,
        )
        self.target_hands = hand_count
        self.current_hand_number = 0
        self.finished = False
        self.log_lines: list[str] = []
        self.last_actions = {bot.name: "Waiting" for bot in bots}
        self.current_roles = {bot.name: "" for bot in bots}
        self.cached_hole_cards = {bot.name: [] for bot in bots}
        self.last_hand_result: dict | None = None
        self.match_message = "Ready to begin"

    def step(self) -> None:
        if self.finished:
            return

        game = self.engine.game
        if game.state is None or game.is_hand_over():
            if self.current_hand_number >= self.target_hands or not game.has_enough_players():
                self.finished = True
                self.match_message = "Match complete"
                self._append_log("Match complete.")
                remaining = [
                    player_id for player_id, stack in game.stacks.items() if stack > 0
                ]
                if len(remaining) == 1:
                    self._append_log(f"Champion: {remaining[0]}")
                return

            self._start_new_hand()
            return

        self._run_action_step()

    def get_snapshot(self) -> dict:
        game = self.engine.game
        current_player = game.current_player_id

        if game.state is not None:
            pot_size = (
                int(game.state.total_pot_amount)
                if game.state.status
                else int(sum(game.hand_pull_amounts.values()))
            )
            community_cards = [repr(card) for card in game.state.get_board_cards(0)]
            round_stage = game.current_round_stage
        else:
            pot_size = 0
            community_cards = []
            round_stage = "waiting"

        players = [self._build_player_snapshot(player_id) for player_id in game.seating_order]

        return {
            "match_message": self.match_message,
            "hand_number": self.current_hand_number,
            "target_hands": self.target_hands,
            "pot_size": pot_size,
            "community_cards": community_cards,
            "round_stage": round_stage,
            "current_player": current_player,
            "players": players,
            "logs": list(self.log_lines),
            "finished": self.finished,
            "last_hand_result": self.last_hand_result,
            "small_blind": game.small_blind,
            "big_blind": game.big_blind,
        }

    def _start_new_hand(self) -> None:
        hand_info = self.engine.game.start_new_hand()
        self.current_hand_number += 1
        self.last_hand_result = None
        self.match_message = f"Hand {self.current_hand_number} in progress"

        for player_id in self.last_actions:
            self.last_actions[player_id] = "Waiting"
            self.current_roles[player_id] = ""

        self.current_roles[hand_info.button_player] = "Button"
        self.current_roles[hand_info.small_blind_player] = "Small Blind"
        self.current_roles[hand_info.big_blind_player] = "Big Blind"

        self._cache_hole_cards()
        self._append_log("")
        self._append_log(f"=== Hand {self.current_hand_number} ===")
        self._append_log(
            f"Button: {hand_info.button_player} | "
            f"SB: {hand_info.small_blind_player} ({self.engine.game.small_blind}) | "
            f"BB: {hand_info.big_blind_player} ({self.engine.game.big_blind})"
        )

    def _run_action_step(self) -> None:
        game = self.engine.game
        player_id = game.current_player_id
        if player_id is None:
            return

        state = game.get_state(player_id)
        proposed_action, warning = self.engine._get_bot_action(player_id, state)
        if warning:
            self._append_log(warning)

        result = game.apply_action(player_id, proposed_action)
        self.last_actions[player_id] = self._format_last_action(
            result["action"],
            result["amount"],
        )

        for line in result["log_lines"]:
            self._append_log(line)

        if result["hand_over"]:
            self.last_hand_result = game.get_last_hand_result()
            winners = ", ".join(result["winners"]) if result["winners"] else "None"
            self.match_message = f"Hand {self.current_hand_number} complete"
            self._append_log(f"Winners: {winners}")
            if self.last_hand_result is not None:
                change_text = ", ".join(
                    f"{player_id} {self._format_chip_delta(change)}"
                    for player_id, change in self.last_hand_result["chip_changes"].items()
                )
                self._append_log(f"Chip changes: {change_text}")

    def _build_player_snapshot(self, player_id: str) -> dict:
        game = self.engine.game
        stack = game.stacks[player_id]
        status = "Waiting"
        chip_change = None

        if game.state is not None and player_id in game.hand_player_ids:
            local_index = game.hand_player_ids.index(player_id)
            stack = int(game.state.stacks[local_index])

            if not game.state.status and self.last_hand_result is not None:
                if player_id in self.last_hand_result["winners"]:
                    status = "Won hand"
                elif stack == 0:
                    status = "Busted"
                else:
                    status = "Lost hand"
                chip_change = self.last_hand_result["chip_changes"].get(player_id, 0)
            elif not game.state.statuses[local_index]:
                status = "Folded"
            elif stack == 0:
                status = "All-in"
            elif game.current_player_id == player_id:
                status = "Acting"
            else:
                status = "Active"
        elif stack <= 0:
            status = "Busted"

        if self.last_hand_result is not None and player_id in self.last_hand_result["chip_changes"]:
            chip_change = self.last_hand_result["chip_changes"][player_id]

        return {
            "name": player_id,
            "bot_type": type(self.engine.bots[player_id]).__name__,
            "stack": stack,
            "cards": list(self.cached_hole_cards.get(player_id, [])),
            "status": status,
            "role": self.current_roles.get(player_id, ""),
            "last_action": self.last_actions.get(player_id, "Waiting"),
            "chip_change": chip_change,
            "is_current": game.current_player_id == player_id,
        }

    def _cache_hole_cards(self) -> None:
        game = self.engine.game
        if game.state is None:
            return

        for player_id in game.seating_order:
            self.cached_hole_cards[player_id] = []

        for local_index, player_id in enumerate(game.hand_player_ids):
            self.cached_hole_cards[player_id] = [
                repr(card) for card in game.state.hole_cards[local_index]
            ]

    def _append_log(self, line: str) -> None:
        self.log_lines.append(line)
        self.log_lines = self.log_lines[-250:]

    @staticmethod
    def _format_last_action(action_name: str, amount: int | None) -> str:
        if action_name == "fold":
            return "Folded"
        if action_name == "check":
            return "Checked"
        if action_name == "call":
            return f"Called {amount}"
        return f"Raised to {amount}"

    @staticmethod
    def _format_chip_delta(change: int) -> str:
        return f"+{change}" if change > 0 else str(change)


class PokerFrontend:
    def __init__(
        self,
        bots: list[BaseBot],
        hand_count: int,
        starting_stack: int,
        small_blind: int,
        big_blind: int,
        delay_ms: int = 1100,
    ) -> None:
        self.controller = MatchController(
            bots=bots,
            hand_count=hand_count,
            starting_stack=starting_stack,
            small_blind=small_blind,
            big_blind=big_blind,
        )
        self.delay_ms = delay_ms
        self.running = True

        self.root = tk.Tk()
        self.root.title("Texas Hold'em Viewer")
        self.root.geometry("1360x860")
        self.root.configure(bg=TABLE_BG)
        self.root.minsize(1180, 760)

        self.status_var = tk.StringVar()
        self.hand_var = tk.StringVar()
        self.stage_var = tk.StringVar()
        self.pot_var = tk.StringVar()
        self.current_var = tk.StringVar()

        self.community_card_labels: list[tk.Label] = []
        self.player_widgets: dict[str, dict[str, object]] = {}

        self._build_ui()
        self._refresh_view()
        self.root.after(350, self._tick)

    def run(self) -> None:
        self.root.mainloop()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=2)
        self.root.rowconfigure(1, weight=1)

        header = tk.Frame(self.root, bg=TABLE_BG, padx=24, pady=18)
        header.grid(row=0, column=0, columnspan=2, sticky="nsew")
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)

        title_block = tk.Frame(header, bg=TABLE_BG)
        title_block.grid(row=0, column=0, sticky="w")

        tk.Label(
            title_block,
            text="Texas Hold'em Table",
            bg=TABLE_BG,
            fg=TEXT_LIGHT,
            font=("Georgia", 24, "bold"),
        ).pack(anchor="w")

        tk.Label(
            title_block,
            textvariable=self.status_var,
            bg=TABLE_BG,
            fg="#d8e6db",
            font=("Trebuchet MS", 11),
        ).pack(anchor="w", pady=(4, 0))

        controls = tk.Frame(header, bg=TABLE_BG)
        controls.grid(row=0, column=1, sticky="e")

        self.play_button = tk.Button(
            controls,
            text="Pause",
            command=self._toggle_running,
            bg=ACCENT,
            fg=TEXT_DARK,
            activebackground=PANEL_ALT,
            relief="flat",
            padx=16,
            pady=8,
            font=("Trebuchet MS", 11, "bold"),
        )
        self.play_button.grid(row=0, column=0, padx=(0, 10))

        tk.Button(
            controls,
            text="Step",
            command=self._manual_step,
            bg=PANEL_BG,
            fg=TEXT_DARK,
            activebackground=PANEL_ALT,
            relief="flat",
            padx=16,
            pady=8,
            font=("Trebuchet MS", 11, "bold"),
        ).grid(row=0, column=1, padx=(0, 16))

        speed_scale = tk.Scale(
            controls,
            from_=250,
            to=2500,
            orient="horizontal",
            command=self._set_speed,
            showvalue=False,
            bg=TABLE_BG,
            fg=TEXT_LIGHT,
            troughcolor=TABLE_ALT,
            highlightthickness=0,
            activebackground=ACCENT,
            length=180,
        )
        speed_scale.set(self.delay_ms)
        speed_scale.grid(row=0, column=2)

        tk.Label(
            controls,
            text="Playback speed",
            bg=TABLE_BG,
            fg="#d8e6db",
            font=("Trebuchet MS", 10),
        ).grid(row=1, column=2, sticky="ew")

        table_area = tk.Frame(self.root, bg=TABLE_BG, padx=24, pady=10)
        table_area.grid(row=1, column=0, sticky="nsew")
        table_area.rowconfigure(2, weight=1)
        table_area.columnconfigure(0, weight=1)

        board_panel = tk.Frame(
            table_area,
            bg=TABLE_ALT,
            padx=20,
            pady=18,
            highlightbackground=ACCENT,
            highlightthickness=2,
        )
        board_panel.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        board_panel.columnconfigure(0, weight=1)

        info_row = tk.Frame(board_panel, bg=TABLE_ALT)
        info_row.grid(row=0, column=0, sticky="ew")
        for column in range(4):
            info_row.columnconfigure(column, weight=1)

        self._build_metric(info_row, "Hand", self.hand_var, 0)
        self._build_metric(info_row, "Stage", self.stage_var, 1)
        self._build_metric(info_row, "Pot", self.pot_var, 2)
        self._build_metric(info_row, "Current Action", self.current_var, 3)

        cards_row = tk.Frame(board_panel, bg=TABLE_ALT)
        cards_row.grid(row=1, column=0, pady=(18, 2))
        for _ in range(5):
            label = self._create_card_label(cards_row, large=True)
            label.pack(side="left", padx=8)
            self.community_card_labels.append(label)

        players_panel = tk.Frame(table_area, bg=TABLE_BG)
        players_panel.grid(row=2, column=0, sticky="nsew")
        self._build_player_grid(players_panel)

        sidebar = tk.Frame(self.root, bg=TABLE_BG, padx=10, pady=10)
        sidebar.grid(row=1, column=1, sticky="nsew")
        sidebar.rowconfigure(1, weight=1)
        sidebar.columnconfigure(0, weight=1)

        summary_panel = tk.Frame(
            sidebar,
            bg=PANEL_BG,
            padx=18,
            pady=16,
            highlightbackground=ACCENT,
            highlightthickness=2,
        )
        summary_panel.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        summary_panel.columnconfigure(0, weight=1)

        tk.Label(
            summary_panel,
            text="Round Notes",
            bg=PANEL_BG,
            fg=TEXT_DARK,
            font=("Georgia", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")

        self.summary_label = tk.Label(
            summary_panel,
            text="Waiting for the first hand",
            justify="left",
            wraplength=360,
            bg=PANEL_BG,
            fg=TEXT_DARK,
            font=("Trebuchet MS", 11),
        )
        self.summary_label.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        log_panel = tk.Frame(
            sidebar,
            bg=PANEL_BG,
            padx=18,
            pady=16,
            highlightbackground=ACCENT,
            highlightthickness=2,
        )
        log_panel.grid(row=1, column=0, sticky="nsew")
        log_panel.rowconfigure(1, weight=1)
        log_panel.columnconfigure(0, weight=1)

        tk.Label(
            log_panel,
            text="Action Feed",
            bg=PANEL_BG,
            fg=TEXT_DARK,
            font=("Georgia", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")

        self.log_text = tk.Text(
            log_panel,
            wrap="word",
            bg="#faf7ef",
            fg=TEXT_DARK,
            relief="flat",
            font=("Consolas", 11),
            padx=10,
            pady=10,
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(12, 0))

        scrollbar = ttk.Scrollbar(log_panel, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(12, 0))
        self.log_text.configure(yscrollcommand=scrollbar.set, state="disabled")

    def _build_metric(self, parent: tk.Frame, label: str, variable: tk.StringVar, column: int) -> None:
        container = tk.Frame(parent, bg=TABLE_ALT)
        container.grid(row=0, column=column, sticky="ew")
        tk.Label(
            container,
            text=label,
            bg=TABLE_ALT,
            fg="#d8e6db",
            font=("Trebuchet MS", 10, "bold"),
        ).pack(anchor="center")
        tk.Label(
            container,
            textvariable=variable,
            bg=TABLE_ALT,
            fg=TEXT_LIGHT,
            font=("Georgia", 15, "bold"),
        ).pack(anchor="center", pady=(4, 0))

    def _build_player_grid(self, parent: tk.Frame) -> None:
        player_names = list(self.controller.engine.bots)
        column_count = 2 if len(player_names) <= 4 else 3
        row_count = math.ceil(len(player_names) / column_count)

        for row in range(row_count):
            parent.rowconfigure(row, weight=1)
        for column in range(column_count):
            parent.columnconfigure(column, weight=1)

        for index, player_id in enumerate(player_names):
            row = index // column_count
            column = index % column_count

            panel = tk.Frame(
                parent,
                bg=PANEL_BG,
                padx=16,
                pady=14,
                highlightbackground=ACCENT,
                highlightthickness=2,
            )
            panel.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
            panel.columnconfigure(0, weight=1)

            name_var = tk.StringVar()
            meta_var = tk.StringVar()
            status_var = tk.StringVar()
            action_var = tk.StringVar()
            chips_var = tk.StringVar()
            cards_vars = [tk.StringVar(value="--"), tk.StringVar(value="--")]

            name_label = tk.Label(
                panel,
                textvariable=name_var,
                bg=PANEL_BG,
                fg=TEXT_DARK,
                font=("Georgia", 16, "bold"),
            )
            name_label.grid(row=0, column=0, sticky="w")

            meta_label = tk.Label(
                panel,
                textvariable=meta_var,
                bg=PANEL_BG,
                fg="#51473c",
                font=("Trebuchet MS", 10),
            )
            meta_label.grid(row=1, column=0, sticky="w", pady=(2, 10))

            cards_row = tk.Frame(panel, bg=PANEL_BG)
            cards_row.grid(row=2, column=0, sticky="w")
            card_labels = []
            for card_var in cards_vars:
                label = self._create_card_label(cards_row, textvariable=card_var, large=False)
                label.pack(side="left", padx=(0, 8))
                card_labels.append(label)

            chips_label = tk.Label(
                panel,
                textvariable=chips_var,
                bg=PANEL_BG,
                fg=TEXT_DARK,
                font=("Trebuchet MS", 11, "bold"),
            )
            chips_label.grid(row=3, column=0, sticky="w", pady=(12, 2))

            status_label = tk.Label(
                panel,
                textvariable=status_var,
                bg=PANEL_BG,
                fg=SUCCESS,
                font=("Trebuchet MS", 11, "bold"),
            )
            status_label.grid(row=4, column=0, sticky="w")

            action_label = tk.Label(
                panel,
                textvariable=action_var,
                bg=PANEL_BG,
                fg="#51473c",
                font=("Trebuchet MS", 10),
                wraplength=250,
                justify="left",
            )
            action_label.grid(row=5, column=0, sticky="w", pady=(10, 0))

            self.player_widgets[player_id] = {
                "panel": panel,
                "name_label": name_label,
                "meta_label": meta_label,
                "chips_label": chips_label,
                "status_label": status_label,
                "action_label": action_label,
                "cards_row": cards_row,
                "name": name_var,
                "meta": meta_var,
                "status": status_var,
                "action": action_var,
                "chips": chips_var,
                "cards": cards_vars,
                "card_labels": card_labels,
            }

    def _create_card_label(
        self,
        parent: tk.Widget,
        *,
        textvariable: tk.StringVar | None = None,
        large: bool,
    ) -> tk.Label:
        return tk.Label(
            parent,
            textvariable=textvariable,
            text="--" if textvariable is None else None,
            width=5 if large else 4,
            height=2,
            bg="#fffdf8",
            fg=TEXT_DARK,
            relief="flat",
            bd=0,
            highlightbackground="#9e8d63",
            highlightthickness=1,
            font=("Consolas", 18 if large else 14, "bold"),
        )

    def _toggle_running(self) -> None:
        self.running = not self.running
        self.play_button.configure(text="Pause" if self.running else "Play")
        if self.running:
            self.root.after(100, self._tick)

    def _manual_step(self) -> None:
        if self.running:
            self._toggle_running()
        self.controller.step()
        self._refresh_view()

    def _set_speed(self, value: str) -> None:
        self.delay_ms = int(float(value))

    def _tick(self) -> None:
        if not self.running:
            return

        self.controller.step()
        self._refresh_view()

        if not self.controller.finished:
            self.root.after(self.delay_ms, self._tick)
        else:
            self.running = False
            self.play_button.configure(text="Play")

    def _refresh_view(self) -> None:
        snapshot = self.controller.get_snapshot()

        self.status_var.set(snapshot["match_message"])
        self.hand_var.set(f"{snapshot['hand_number']} / {snapshot['target_hands']}")
        self.stage_var.set(snapshot["round_stage"].title())
        self.pot_var.set(f"{snapshot['pot_size']} chips")
        current_actor = snapshot["current_player"] or "Settling hand"
        self.current_var.set(current_actor)

        for index, label in enumerate(self.community_card_labels):
            if index < len(snapshot["community_cards"]):
                label.configure(text=snapshot["community_cards"][index])
            else:
                label.configure(text="--")

        for player in snapshot["players"]:
            widgets = self.player_widgets[player["name"]]
            widgets["name"].set(player["name"])

            role_text = player["role"] if player["role"] else "Seat"
            widgets["meta"].set(f"{player['bot_type']} | {role_text}")
            widgets["chips"].set(f"Stack: {player['stack']} chips")
            widgets["status"].set(self._status_text(player))
            widgets["action"].set(f"Latest move: {player['last_action']}")

            cards = player["cards"] or ["--", "--"]
            for card_var, card in zip(widgets["cards"], cards[:2], strict=False):
                card_var.set(card)
            if len(cards) < 2:
                for card_var in widgets["cards"][len(cards):]:
                    card_var.set("--")

            panel_bg, status_fg = self._player_palette(player)
            widgets["panel"].configure(bg=panel_bg, highlightbackground=ACCENT)
            widgets["cards_row"].configure(bg=panel_bg)
            widgets["name_label"].configure(bg=panel_bg, fg=TEXT_DARK)
            widgets["meta_label"].configure(bg=panel_bg, fg="#51473c")
            widgets["chips_label"].configure(bg=panel_bg, fg=TEXT_DARK)
            widgets["status_label"].configure(bg=panel_bg, fg=status_fg)
            widgets["action_label"].configure(bg=panel_bg, fg="#51473c")
            for card_label in widgets["card_labels"]:
                card_label.configure(bg="#fffdf8")

        self.summary_label.configure(text=self._build_summary(snapshot))

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "\n".join(snapshot["logs"]))
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _build_summary(self, snapshot: dict) -> str:
        if snapshot["last_hand_result"] is not None and snapshot["current_player"] is None:
            winners = ", ".join(snapshot["last_hand_result"]["winners"])
            changes = ", ".join(
                f"{player_id} {self.controller._format_chip_delta(change)}"
                for player_id, change in snapshot["last_hand_result"]["chip_changes"].items()
            )
            return f"Hand complete. Winners: {winners}\nChip changes: {changes}"

        current_player = snapshot["current_player"]
        if current_player is None:
            return "Preparing the next hand."

        player = next(
            player for player in snapshot["players"] if player["name"] == current_player
        )
        return (
            f"{current_player} is acting.\n"
            f"{player['bot_type']} has {player['stack']} chips left.\n"
            f"Latest move: {player['last_action']}"
        )

    @staticmethod
    def _status_text(player: dict) -> str:
        base = player["status"]
        if player["chip_change"] not in (None, 0) and base in {"Won hand", "Lost hand", "Busted"}:
            delta = f"+{player['chip_change']}" if player["chip_change"] > 0 else str(player["chip_change"])
            return f"{base} ({delta})"
        return base

    @staticmethod
    def _player_palette(player: dict) -> tuple[str, str]:
        if player["is_current"]:
            return PANEL_ALT, WARNING
        if player["status"] == "Won hand":
            return "#e7f3ea", SUCCESS
        if player["status"] in {"Folded", "Lost hand"}:
            return "#f6e6e3", DANGER
        if player["status"] == "All-in":
            return "#f8edd7", WARNING
        if player["status"] == "Busted":
            return "#ece7df", DANGER
        return PANEL_BG, SUCCESS
