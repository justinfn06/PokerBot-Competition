from __future__ import annotations

import contextlib
import io
import tkinter as tk
import unittest

from bot_base import BaseBot
from bots import ConservativeBot, RandomBot
from engine import PokerEngine
from frontend import MatchController, PokerFrontend


DOCUMENTED_STATE_KEYS = {
    "player_id",
    "hole_cards",
    "community_cards",
    "pot_size",
    "current_bet",
    "call_amount",
    "min_raise",
    "max_raise",
    "player_stack",
    "active_players",
    "folded_players",
    "all_in_players",
    "betting_history",
    "current_player",
    "round_stage",
    "legal_actions",
}


class RecordingBot(BaseBot):
    def __init__(self, name: str):
        super().__init__(name)
        self.seen_states: list[dict] = []

    def act(self, state: dict) -> tuple:
        self.seen_states.append(state)

        if "call" in state["legal_actions"]:
            return ("call", None)
        if "raise" in state["legal_actions"]:
            return ("raise", state["min_raise"])
        return ("fold", None)


class InvalidBot(BaseBot):
    def __init__(self, name: str):
        super().__init__(name)
        self.call_count = 0

    def act(self, state: dict) -> tuple:
        self.call_count += 1
        if self.call_count % 2:
            return ("teleport", None)
        return ("raise", "not-an-int")


class ExplodingBot(BaseBot):
    def act(self, state: dict) -> tuple:
        raise RuntimeError("intentional test failure")


class MaxPressureBot(BaseBot):
    def act(self, state: dict) -> tuple:
        if "raise" in state["legal_actions"] and state["max_raise"] is not None:
            return ("raise", state["max_raise"])
        if "call" in state["legal_actions"]:
            return ("call", None)
        return ("fold", None)


class EngineAndControllerRegressionTests(unittest.TestCase):
    def test_custom_bot_receives_documented_state_and_runs_without_special_hooks(self) -> None:
        bot = RecordingBot("Recorder")
        controller = MatchController(
            bots=[bot, RecordingBot("Caller_1"), RecordingBot("Caller_2")],
            hand_count=2,
            starting_stack=30,
            small_blind=1,
            big_blind=2,
        )

        while not controller.finished:
            controller.step()

        self.assertGreater(len(bot.seen_states), 0)
        first_state = bot.seen_states[0]
        self.assertEqual(set(first_state), DOCUMENTED_STATE_KEYS)
        self.assertEqual(len(first_state["hole_cards"]), 2)
        self.assertNotIn("deck", first_state)
        self.assertNotIn("other_hole_cards", first_state)

    def test_engine_fallbacks_handle_invalid_and_crashing_bots(self) -> None:
        engine = PokerEngine(
            bots=[
                InvalidBot("Invalid"),
                ExplodingBot("Boom"),
                RecordingBot("Recorder"),
            ],
            starting_stack=20,
            small_blind=1,
            big_blind=2,
            verbose=False,
        )

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            engine.run(hand_count=4)

        output = buffer.getvalue()
        self.assertIn("returned ('teleport', None)", output)
        self.assertIn("raised RuntimeError", output)
        self.assertEqual(sum(engine.game.stacks.values()), 60)

    def test_heads_up_match_runs_and_preserves_total_chips(self) -> None:
        engine = PokerEngine(
            bots=[RandomBot("Random_A"), ConservativeBot("Conservative_B")],
            starting_stack=40,
            small_blind=1,
            big_blind=2,
            verbose=False,
        )

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            engine.run(hand_count=25)

        self.assertEqual(sum(engine.game.stacks.values()), 80)
        self.assertGreaterEqual(len([s for s in engine.game.stacks.values() if s > 0]), 1)

    def test_all_in_heavy_controller_flow_handles_uneven_stacks(self) -> None:
        controller = MatchController(
            bots=[
                MaxPressureBot("Pusher_1"),
                MaxPressureBot("Pusher_2"),
                RecordingBot("Caller"),
                RecordingBot("Caller_2"),
            ],
            hand_count=6,
            starting_stack=20,
            small_blind=1,
            big_blind=2,
        )
        controller.engine.game.stacks.update(
            {
                "Pusher_1": 5,
                "Pusher_2": 9,
                "Caller": 13,
                "Caller_2": 21,
            }
        )

        while not controller.finished:
            controller.step()

        snapshot = controller.get_snapshot()
        self.assertTrue(snapshot["finished"])
        self.assertEqual(sum(player["stack"] for player in snapshot["players"]), 48)
        self.assertGreater(snapshot["hand_number"], 0)
        self.assertIn("Match complete.", snapshot["logs"][-1])

    def test_frontend_controller_produces_consistent_snapshots_across_many_hands(self) -> None:
        controller = MatchController(
            bots=[
                ConservativeBot("Conservative_1"),
                RandomBot("Random_1"),
                RandomBot("Random_2"),
                ConservativeBot("Conservative_2"),
            ],
            hand_count=40,
            starting_stack=50,
            small_blind=1,
            big_blind=2,
        )

        safety_counter = 0
        while not controller.finished:
            controller.step()
            safety_counter += 1
            self.assertLess(safety_counter, 5000, "Controller took too many steps.")

        snapshot = controller.get_snapshot()
        self.assertEqual(sum(player["stack"] for player in snapshot["players"]), 200)
        self.assertLessEqual(snapshot["hand_number"], 40)
        self.assertGreater(len(snapshot["logs"]), 10)

    def test_cli_engine_path_still_runs_after_frontend_addition(self) -> None:
        engine = PokerEngine(
            bots=[
                ConservativeBot("Conservative_1"),
                RandomBot("Random_1"),
                RandomBot("Random_2"),
                ConservativeBot("Conservative_2"),
            ],
            starting_stack=30,
            small_blind=1,
            big_blind=2,
            verbose=True,
        )

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            engine.run(hand_count=8)

        output = buffer.getvalue()
        self.assertIn("=== Hand 1 ===", output)
        self.assertIn("Stacks:", output)
        self.assertIn("Winners:", output)
        self.assertEqual(sum(engine.game.stacks.values()), 120)


class FrontendSmokeTests(unittest.TestCase):
    def test_tk_frontend_instantiates_and_refreshes_when_display_is_available(self) -> None:
        try:
            app = PokerFrontend(
                bots=[
                    ConservativeBot("Conservative_1"),
                    RandomBot("Random_1"),
                    RandomBot("Random_2"),
                ],
                hand_count=1,
                starting_stack=20,
                small_blind=1,
                big_blind=2,
                delay_ms=10,
            )
        except tk.TclError as exc:  # pragma: no cover - depends on desktop availability
            self.skipTest(f"Tk display unavailable: {exc}")
            return

        try:
            app.controller.step()
            app._refresh_view()
            self.assertTrue(app.status_var.get())
            self.assertEqual(len(app.community_card_labels), 5)
            self.assertEqual(len(app.player_widgets), 3)
        finally:
            app.root.destroy()


if __name__ == "__main__":
    unittest.main()
