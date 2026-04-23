from __future__ import annotations

from collections import Counter

from bot_base import BaseBot

RANK_ORDER = "23456789TJQKA"
RANK_VALUES = {rank: index for index, rank in enumerate(RANK_ORDER, start=2)}


class ConservativeBot(BaseBot):
    def act(self, state: dict) -> tuple:
        legal_actions = state["legal_actions"]
        call_amount = state["call_amount"] or 0

        if state["round_stage"] == "preflop":
            return self._act_preflop(state, legal_actions, call_amount)

        return self._act_postflop(state, legal_actions, call_amount)

    def _act_preflop(self, state: dict, legal_actions: list[str], call_amount: int) -> tuple:
        cards = state["hole_cards"]
        first_rank = cards[0][0]
        second_rank = cards[1][0]
        first_value = RANK_VALUES[first_rank]
        second_value = RANK_VALUES[second_rank]
        pair = first_rank == second_rank
        suited = cards[0][1] == cards[1][1]
        high_values = sorted((first_value, second_value), reverse=True)

        premium_hand = pair and high_values[0] >= 10
        strong_hand = pair and high_values[0] >= 7
        strong_aces = high_values == [14, 13] or high_values == [14, 12]
        broadway = min(high_values) >= 10

        if premium_hand or (strong_aces and suited):
            if "raise" in legal_actions:
                return ("raise", state["min_raise"])
            if "call" in legal_actions:
                return ("call", None)

        if strong_hand or strong_aces or (broadway and suited):
            if call_amount <= max(4, state["player_stack"][self.name] // 20):
                if "call" in legal_actions:
                    return ("call", None)

        if call_amount == 0 and "call" in legal_actions:
            return ("call", None)

        if "fold" in legal_actions:
            return ("fold", None)

        return ("call", None)

    def _act_postflop(self, state: dict, legal_actions: list[str], call_amount: int) -> tuple:
        ranks = [card[0] for card in state["hole_cards"] + state["community_cards"]]
        counts = sorted(Counter(ranks).values(), reverse=True)

        has_trips_or_better = counts[0] >= 3
        has_two_pair = len(counts) > 1 and counts[0] == 2 and counts[1] == 2
        has_pair = counts[0] == 2

        if has_trips_or_better or has_two_pair:
            if "raise" in legal_actions and call_amount <= max(8, state["player_stack"][self.name] // 10):
                return ("raise", state["min_raise"])
            if "call" in legal_actions:
                return ("call", None)

        if has_pair:
            if call_amount <= max(4, state["player_stack"][self.name] // 25) and "call" in legal_actions:
                return ("call", None)

        if call_amount == 0 and "call" in legal_actions:
            return ("call", None)

        if "fold" in legal_actions:
            return ("fold", None)

        return ("call", None)
