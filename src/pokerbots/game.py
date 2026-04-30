from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pokerkit import Automation, NoLimitTexasHoldem

def constant(f):
    def fset(_this, _value): return
    def fget(this): return f(this)
    return property(fget, fset)

@dataclass(frozen=True)
class HandStartInfo:
    button_player: str
    small_blind_player: str
    big_blind_player: str
    hand_players: list[str]


class HoldemGame:
    ROUND_STAGES = {
        0: "preflop",
        1: "flop",
        2: "turn",
        3: "river",
    }
    AUTOMATIONS = (
        Automation.ANTE_POSTING,
        Automation.BET_COLLECTION,
        Automation.BLIND_OR_STRADDLE_POSTING,
        Automation.CARD_BURNING,
        Automation.HOLE_DEALING,
        Automation.BOARD_DEALING,
        Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
        Automation.HAND_KILLING,
        Automation.CHIPS_PUSHING,
        Automation.CHIPS_PULLING,
    )

    @constant
    def STATE__PLAYER_ID(_this) -> str: return "player_id"
    @constant
    def STATE__HOLE_CARDS(_this) -> str: return "hole_cards"
    @constant
    def STATE__COMMUNITY_CARDS(_this) -> str: return "community_cards"
    @constant
    def STATE__POT_SIZE(_this) -> str: return "pot_size"
    @constant
    def STATE__CURRENT_BET(_this) -> str: return "current_bet"
    @constant
    def STATE__CALL_AMOUNT(_this) -> str: return "call_amount"
    @constant
    def STATE__MIN_RAISE(_this) -> str: return "min_raise"
    @constant
    def STATE__MAX_RAISE(_this) -> str: return "max_raise"
    @constant
    def STATE__PLAYER_STACK(_this) -> str: return "player_stack"
    @constant
    def STATE__ACTIVE_PLAYERS(_this) -> str: return "active_players"
    @constant
    def STATE__FOLDED_PLAYERS(_this) -> str: return "folded_players"
    @constant
    def STATE__ALL_IN_PLAYERS(_this) -> str: return "all_in_players"
    @constant
    def STATE__BETTING_HISTORY(_this) -> str: return "betting_history"
    @constant
    def STATE__CURRENT_PLAYER(_this) -> str: return "current_player"
    @constant
    def STATE__ROUND_STAGE(_this) -> str: return "round_stage"
    @constant
    def STATE__LEGAL_ACTIONS(_this) -> str: return "legal_actions"

    def __init__(
        self,
        player_ids: list[str],
        starting_stack: int = 100,
        small_blind: int = 1,
        big_blind: int = 2,
    ) -> None:
        if len(player_ids) < 2:
            raise ValueError("At least two players are required.")

        if len(set(player_ids)) != len(player_ids):
            raise ValueError("Player ids must be unique.")

        if small_blind <= 0 or big_blind <= 0 or small_blind >= big_blind:
            raise ValueError("Blinds must satisfy 0 < small_blind < big_blind.")

        self.seating_order = list(player_ids)
        self.stacks = {player_id: starting_stack for player_id in player_ids}
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.button_index = len(self.seating_order) - 1

        self.state = None
        self.hand_player_ids: list[str] = []
        self.current_round_stage = "preflop"
        self.round_betting_history: list[dict[str, Any]] = []
        self.hand_push_amounts: dict[str, int] = {}
        self.hand_pull_amounts: dict[str, int] = {}
        self.hand_starting_stacks: dict[str, int] = {}
        self.last_hand_result: dict[str, Any] | None = None

    @property
    def current_player_id(self) -> str | None:
        if self.state is None or not self.state.status or self.state.actor_index is None:
            return None

        return self.hand_player_ids[self.state.actor_index]

    def has_enough_players(self) -> bool:
        return len(self._players_with_chips()) >= 2

    def start_new_hand(self) -> HandStartInfo:
        if not self.has_enough_players():
            raise ValueError("Not enough players with chips to start a hand.")

        self.button_index = self._next_eligible_seat(self.button_index)
        button_player = self.seating_order[self.button_index]
        self.hand_player_ids = self._build_hand_player_order(button_player)
        self.hand_starting_stacks = {
            player_id: self.stacks[player_id] for player_id in self.hand_player_ids
        }
        self.hand_push_amounts = {player_id: 0 for player_id in self.hand_player_ids}
        self.hand_pull_amounts = {player_id: 0 for player_id in self.hand_player_ids}
        self.round_betting_history = []
        self.current_round_stage = "preflop"
        self.last_hand_result = None

        starting_stacks = tuple(self.stacks[player_id] for player_id in self.hand_player_ids)

        self.state = NoLimitTexasHoldem.create_state(
            self.AUTOMATIONS,
            True,
            0,
            (self.small_blind, self.big_blind),
            self.big_blind,
            starting_stacks,
            len(self.hand_player_ids),
        )

        small_blind_player, big_blind_player = self._blind_players(button_player)

        return HandStartInfo(
            button_player=button_player,
            small_blind_player=small_blind_player,
            big_blind_player=big_blind_player,
            hand_players=list(self.hand_player_ids),
        )

    def get_state(self, player_id: str) -> dict[str, Any]:
        if self.state is None:
            raise ValueError("No hand is currently running.")

        player_stacks = dict(self.stacks)
        for local_index, local_player_id in enumerate(self.hand_player_ids):
            player_stacks[local_player_id] = int(self.state.stacks[local_index])

        community_cards = self._community_cards()
        current_player = self.current_player_id
        legal_actions = self._legal_actions() if player_id == current_player else []
        current_player_local_index = self.hand_player_ids.index(player_id) if player_id in self.hand_player_ids else None

        active_players = [
            local_player_id
            for local_index, local_player_id in enumerate(self.hand_player_ids)
            if self.state.statuses[local_index]
        ]
        folded_players = [
            local_player_id
            for local_index, local_player_id in enumerate(self.hand_player_ids)
            if not self.state.statuses[local_index]
        ]
        all_in_players = [
            local_player_id
            for local_index, local_player_id in enumerate(self.hand_player_ids)
            if self.state.statuses[local_index] and self.state.stacks[local_index] == 0
        ]

        hole_cards: list[str] = []
        if current_player_local_index is not None:
            hole_cards = [
                self._card_text(card)
                for card in self.state.hole_cards[current_player_local_index]
            ]

        min_raise = None
        max_raise = None
        call_amount = None
        if current_player == player_id and self.state.can_check_or_call():
            call_amount = int(self.state.checking_or_calling_amount)
        if current_player == player_id and self.state.can_complete_bet_or_raise_to():
            min_raise = int(self.state.min_completion_betting_or_raising_to_amount)
            max_raise = int(self.state.max_completion_betting_or_raising_to_amount)

        return {
            self.STATE__PLAYER_ID: player_id,
            self.STATE__HOLE_CARDS: hole_cards,
            self.STATE__COMMUNITY_CARDS: community_cards,
            self.STATE__POT_SIZE: self._display_pot_size(),
            self.STATE__CURRENT_BET: int(max(self.state.bets)) if self.state.bets else 0,
            self.STATE__CALL_AMOUNT: call_amount,
            self.STATE__MIN_RAISE: min_raise,
            self.STATE__MAX_RAISE: max_raise,
            self.STATE__PLAYER_STACK: player_stacks,
            self.STATE__ACTIVE_PLAYERS: active_players,
            self.STATE__FOLDED_PLAYERS: folded_players,
            self.STATE__ALL_IN_PLAYERS: all_in_players,
            self.STATE__BETTING_HISTORY: [dict(entry) for entry in self.round_betting_history],
            self.STATE__CURRENT_PLAYER: current_player,
            self.STATE__ROUND_STAGE: self.current_round_stage,
            self.STATE__LEGAL_ACTIONS: legal_actions,
        }

    def apply_action(self, player_id: str, action: tuple) -> dict[str, Any]:
        if self.state is None:
            raise ValueError("No hand is currently running.")

        current_player = self.current_player_id
        if current_player != player_id:
            raise ValueError(f"It is not {player_id}'s turn.")

        action_name, amount = action
        operations_start = len(self.state.operations)
        call_amount_before = (
            int(self.state.checking_or_calling_amount) if self.state.can_check_or_call() else 0
        )
        board_stage_cursor = self.state.street_index

        if action_name == "fold":
            self.state.fold()
            action_label = "fold"
            action_amount = None
        elif action_name == "call":
            self.state.check_or_call()
            action_label = "check" if call_amount_before == 0 else "call"
            action_amount = 0 if call_amount_before == 0 else call_amount_before
        elif action_name == "raise":
            raise_to_amount = int(amount)
            self.state.complete_bet_or_raise_to(raise_to_amount)
            action_label = "raise"
            action_amount = raise_to_amount
        else:
            raise ValueError(f"Unknown action: {action_name}")

        self.round_betting_history.append(
            {
                "player_id": player_id,
                "action": action_label,
                "amount": action_amount,
            }
        )

        log_lines = [self._format_action_line(player_id, action_label, action_amount)]
        board_events: list[dict[str, Any]] = []
        showdown_reveals: list[dict[str, Any]] = []

        for operation in self.state.operations[operations_start:]:
            operation_name = type(operation).__name__

            if operation_name == "HoleCardsShowingOrMucking":
                revealed_cards = [
                    self._card_text(card)
                    for card in getattr(operation, "hole_cards", ())
                ]
                if revealed_cards:
                    showdown_reveals.append(
                        {
                            "player_id": self.hand_player_ids[operation.player_index],
                            "cards": revealed_cards,
                        }
                    )
                    log_lines.append(
                        f"Showdown: {self.hand_player_ids[operation.player_index]} shows {' '.join(revealed_cards)}"
                    )

            elif operation_name == "BoardDealing":
                if board_stage_cursor is None:
                    board_stage_cursor = 0
                board_stage_cursor += 1
                stage = self.ROUND_STAGES[board_stage_cursor]
                cards = [self._card_text(card) for card in operation.cards]
                board_events.append({"stage": stage, "cards": cards})
                self.current_round_stage = stage
                self.round_betting_history = []
                log_lines.append(f"{stage.title()}: {' '.join(cards)}")

            elif operation_name == "ChipsPushing":
                for local_index, pushed_amount in enumerate(operation.amounts):
                    if pushed_amount:
                        player = self.hand_player_ids[local_index]
                        self.hand_push_amounts[player] += int(pushed_amount)

            elif operation_name == "ChipsPulling":
                player = self.hand_player_ids[operation.player_index]
                self.hand_pull_amounts[player] += int(operation.amount)

        hand_over = not self.state.status
        if hand_over:
            self._finalize_hand()

        pot_size = self._display_pot_size()
        log_lines.append(f"Pot: {pot_size}")

        result = {
            "player_id": player_id,
            "action": action_label,
            "amount": action_amount,
            "pot_size": pot_size,
            "board_events": board_events,
            "showdown_reveals": showdown_reveals,
            "hand_over": hand_over,
            "winners": self.get_winner() if hand_over else [],
            "log_lines": log_lines,
        }

        if hand_over and self.last_hand_result is not None:
            result["chip_changes"] = dict(self.last_hand_result["chip_changes"])
            result["revealed_hole_cards"] = {
                player_id: list(cards)
                for player_id, cards in self.last_hand_result["revealed_hole_cards"].items()
            }

        return result

    def is_hand_over(self) -> bool:
        return self.state is None or not self.state.status

    def get_winner(self) -> list[str]:
        if self.last_hand_result is None:
            return []

        return list(self.last_hand_result["winners"])

    def get_last_hand_result(self) -> dict[str, Any] | None:
        if self.last_hand_result is None:
            return None

        return {
            "winners": list(self.last_hand_result["winners"]),
            "chip_changes": dict(self.last_hand_result["chip_changes"]),
            "revealed_hole_cards": {
                player_id: list(cards)
                for player_id, cards in self.last_hand_result["revealed_hole_cards"].items()
            },
        }

    def _players_with_chips(self) -> list[str]:
        return [
            player_id for player_id in self.seating_order if self.stacks[player_id] > 0
        ]

    def _next_eligible_seat(self, start_index: int) -> int:
        seat_count = len(self.seating_order)
        for offset in range(1, seat_count + 1):
            seat_index = (start_index + offset) % seat_count
            player_id = self.seating_order[seat_index]
            if self.stacks[player_id] > 0:
                return seat_index

        raise ValueError("No eligible player found.")

    def _next_active_player(self, player_id: str, active_players: list[str]) -> str:
        seat_index = self.seating_order.index(player_id)
        seat_count = len(self.seating_order)

        for offset in range(1, seat_count + 1):
            next_seat = (seat_index + offset) % seat_count
            next_player = self.seating_order[next_seat]
            if next_player in active_players:
                return next_player

        raise ValueError("No next active player found.")

    def _build_hand_player_order(self, button_player: str) -> list[str]:
        active_players = self._players_with_chips()

        if len(active_players) == 2:
            small_blind_player = button_player
            big_blind_player = self._next_active_player(button_player, active_players)
            return [big_blind_player, small_blind_player]

        small_blind_player = self._next_active_player(button_player, active_players)
        first_index = active_players.index(small_blind_player)
        return active_players[first_index:] + active_players[:first_index]

    def _blind_players(self, button_player: str) -> tuple[str, str]:
        if len(self.hand_player_ids) == 2:
            return self.hand_player_ids[1], self.hand_player_ids[0]

        small_blind_player = self._next_active_player(button_player, self._players_with_chips())
        big_blind_player = self._next_active_player(small_blind_player, self._players_with_chips())
        return small_blind_player, big_blind_player

    def _community_cards(self) -> list[str]:
        if self.state is None:
            return []

        return [self._card_text(card) for card in self.state.get_board_cards(0)]

    def _legal_actions(self) -> list[str]:
        if self.state is None or not self.state.status or self.state.actor_index is None:
            return []

        legal_actions: list[str] = []
        if self.state.can_fold():
            legal_actions.append("fold")
        if self.state.can_check_or_call():
            legal_actions.append("call")
        if self.state.can_complete_bet_or_raise_to():
            legal_actions.append("raise")

        return legal_actions

    def _display_pot_size(self) -> int:
        if self.state is not None and self.state.status:
            return int(self.state.total_pot_amount)

        return int(sum(self.hand_pull_amounts.values()))

    def _finalize_hand(self) -> None:
        current_stacks = {}
        revealed_hole_cards = {}

        for local_index, player_id in enumerate(self.hand_player_ids):
            stack = int(self.state.stacks[local_index])
            current_stacks[player_id] = stack
            self.stacks[player_id] = stack

            hole_cards = [
                self._card_text(card) for card in self.state.hole_cards[local_index]
            ]
            if hole_cards:
                revealed_hole_cards[player_id] = hole_cards

        chip_changes = {
            player_id: current_stacks[player_id] - self.hand_starting_stacks[player_id]
            for player_id in self.hand_player_ids
        }
        winners = [
            player_id
            for player_id, pulled_amount in self.hand_pull_amounts.items()
            if pulled_amount > 0
        ]

        self.last_hand_result = {
            "winners": winners,
            "chip_changes": chip_changes,
            "revealed_hole_cards": revealed_hole_cards,
        }

    @staticmethod
    def _format_action_line(player_id: str, action_name: str, action_amount: int | None) -> str:
        if action_name == "fold":
            return f"{player_id} folds"
        if action_name == "check":
            return f"{player_id} checks"
        if action_name == "call":
            return f"{player_id} calls {action_amount}"
        return f"{player_id} raises to {action_amount}"

    @staticmethod
    def _card_text(card: Any) -> str:
        return repr(card)
