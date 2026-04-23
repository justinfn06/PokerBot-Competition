from __future__ import annotations

from typing import Any

from bot_base import BaseBot
from game import HoldemGame


class PokerEngine:
    def __init__(
        self,
        bots: list[BaseBot],
        starting_stack: int = 100,
        small_blind: int = 1,
        big_blind: int = 2,
        verbose: bool = False,
    ) -> None:
        self.bots = {bot.name: bot for bot in bots}
        self.verbose = verbose
        self.game = HoldemGame(
            player_ids=[bot.name for bot in bots],
            starting_stack=starting_stack,
            small_blind=small_blind,
            big_blind=big_blind,
        )

    def run(self, hand_count: int) -> None:
        for hand_number in range(1, hand_count + 1):
            if not self.game.has_enough_players():
                break

            self.run_hand(hand_number)

        self._print_final_standings()

    def run_hand(self, hand_number: int) -> None:
        hand_info = self.game.start_new_hand()

        print(f"\n=== Hand {hand_number} ===")
        print(
            "Button: "
            f"{hand_info.button_player} | "
            f"Small blind: {hand_info.small_blind_player} ({self.game.small_blind}) | "
            f"Big blind: {hand_info.big_blind_player} ({self.game.big_blind})"
        )
        print(f"Players: {', '.join(hand_info.hand_players)}")
        print(f"Stacks: {self._format_stacks()}")

        while not self.game.is_hand_over():
            player_id = self.game.current_player_id
            if player_id is None:
                break

            state = self.game.get_state(player_id)
            raw_action, warning = self._get_bot_action(player_id, state)

            if warning:
                print(warning)

            result = self.game.apply_action(player_id, raw_action)

            for line in result["log_lines"]:
                print(line)

            if self.verbose:
                next_player = self.game.current_player_id
                if next_player is not None:
                    next_state = self.game.get_state(next_player)
                    print(
                        "Next up: "
                        f"{next_player} | "
                        f"Stage: {next_state['round_stage']} | "
                        f"Legal: {', '.join(next_state['legal_actions'])}"
                    )

        self._print_hand_result()

    def _get_bot_action(self, player_id: str, state: dict[str, Any]) -> tuple[tuple, str | None]:
        bot = self.bots[player_id]

        try:
            proposed_action = bot.act(state)
        except Exception as exc:  # pragma: no cover - defensive for user bots
            fallback = self._fallback_action(state)
            warning = f"{player_id} raised {exc.__class__.__name__}: {exc}. Using {fallback!r}."
            return fallback, warning

        validated_action, reason = self._validate_action(proposed_action, state)
        if reason is None:
            return validated_action, None

        warning = f"{player_id} returned {proposed_action!r}. {reason} Using {validated_action!r}."
        return validated_action, warning

    def _validate_action(self, action: Any, state: dict[str, Any]) -> tuple[tuple, str | None]:
        legal_actions = set(state["legal_actions"])

        if not isinstance(action, tuple) or len(action) != 2:
            return self._fallback_action(state), "Actions must be a 2-item tuple."

        action_name, amount = action
        if action_name not in {"fold", "call", "raise"}:
            return self._fallback_action(state), "Unknown action type."

        if action_name not in legal_actions:
            return self._fallback_action(state), f"{action_name!r} is not currently legal."

        if action_name != "raise":
            return (action_name, None), None

        if isinstance(amount, bool) or not isinstance(amount, int):
            return self._fallback_action(state), "Raise amounts must be integers."

        min_raise = state["min_raise"]
        max_raise = state["max_raise"]
        if min_raise is None or max_raise is None:
            return self._fallback_action(state), "Raising is not available right now."

        if amount < min_raise or amount > max_raise:
            return (
                self._fallback_action(state),
                f"Raise must be between {min_raise} and {max_raise}.",
            )

        return ("raise", amount), None

    @staticmethod
    def _fallback_action(state: dict[str, Any]) -> tuple:
        if "fold" in state["legal_actions"]:
            return ("fold", None)
        if "call" in state["legal_actions"]:
            return ("call", None)
        if "raise" in state["legal_actions"]:
            return ("raise", state["min_raise"])
        raise ValueError("No fallback action is available.")

    def _print_hand_result(self) -> None:
        hand_result = self.game.get_last_hand_result()
        if hand_result is None:
            return

        print(f"Winners: {', '.join(hand_result['winners'])}")
        print(
            "Chip changes: "
            + ", ".join(
                f"{player_id} {self._format_chip_delta(change)}"
                for player_id, change in hand_result["chip_changes"].items()
            )
        )

        if self.verbose and hand_result["revealed_hole_cards"]:
            showdown_cards = ", ".join(
                f"{player_id}: {' '.join(cards)}"
                for player_id, cards in hand_result["revealed_hole_cards"].items()
            )
            print(f"Visible hole cards: {showdown_cards}")

        print(f"Stacks: {self._format_stacks()}")

    def _print_final_standings(self) -> None:
        print("\n=== Final Stacks ===")
        print(self._format_stacks())

        remaining_players = [
            player_id for player_id, stack in self.game.stacks.items() if stack > 0
        ]
        if len(remaining_players) == 1:
            print(f"Champion: {remaining_players[0]}")

    def _format_stacks(self) -> str:
        return ", ".join(
            f"{player_id}: {stack}" for player_id, stack in self.game.stacks.items()
        )

    @staticmethod
    def _format_chip_delta(change: int) -> str:
        return f"+{change}" if change > 0 else str(change)
