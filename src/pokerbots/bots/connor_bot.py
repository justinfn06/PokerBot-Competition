from __future__ import annotations

from bot_base import BaseBot

def constant(f):
    def fset(_this, _value): return
    def fget(this): return f(this)
    return property(fget, fset)

class ConnorBot(BaseBot):
    """
    the engine calls `act(state)` every time it is your turn.
    """

    @constant
    def RANK_ORDER(_this) -> str: return "23456789TJQKA"
    @constant
    def RANK_VALS(this) -> dict[str, int]: return {rank: idx for idx, rank in enumerate(this.RANK_ORDER, start=2)}

    # def _card_point_eval(self, state: dict) -> dict[str, float]:
    #     """
    #     Calculate likliyhoods of getting each hand from the current hand.
    #     I don't have the time to implement this for the competition, so it's getting scrapped
    #     """
    #     hand: list[str] = state["hole_cards"] + state["community_cards"]
    #     return

    def _bluff_detector(self, state: dict) -> int:
        # See if anyone is trying an obvious bluff
        return

    def _bluffer(self, state: dict) -> int:
        # Check to see if I could bluff
        return

    def get_current_chips(self, state: dict) -> int:
        return state["player_stack"][state["player_id"]]

    def act(self, state: dict) -> tuple:
        """
        this function is called whenever it is your turn.

        you receive a dictionary called `state` containing all information your bot is allowed to know.

        --------------------------------------------------
        what you can access:

        state["player_id"]
            your own player name/id.

        state["hole_cards"]
            your two private cards, like ["As", "Td"].

        state["community_cards"]
            the shared board cards revealed so far.

        state["pot_size"]
            total chips currently in the pot.

        state["current_bet"]
            the highest amount any active player has committed in this betting round.

        state["call_amount"]
            how many chips it costs to call right now.
            if this is 0, then "call" means check.

        state["min_raise"]
            the minimum legal "raise to" amount.
            This is only useful when "raise" is in state["legal_actions"].

        state["max_raise"]
            the maximum legal "raise to" amount.
            This is usually your all-in amount.

        state["player_stack"]
            Dictionary mapping every player_id to their remaining chips.

        state["active_players"]
            Players still live in the current hand.

        state["folded_players"]
            Players who have already folded this hand.

        state["all_in_players"]
            Players who are all-in and cannot take further betting actions.

        state["betting_history"]
            actions taken in the current betting round, in order.
            Each item looks like:
                {"player_id": "...", "action": "fold/call/check/raise", "amount": ...}

        state["current_player"]
            The player whose turn it is. When `act` is called, this will be your id.

        state["round_stage"]
            One of: "preflop", "flop", "turn", "river"

        state["legal_actions"]
            The actions you may currently choose from.
            Possible entries are "fold", "call", and "raise".

        --------------------------------------------------
        What you need to do:

        return only ONE of the following actions:

        ("fold", None)
        ("call", None)
        ("raise", amount)

        Rules:
        - you may only choose actions in state["legal_actions"]
        - if you return ("raise", amount), amount must be an integer
        - raise amounts are "raise to" amounts, not "raise by" amounts
        - when "raise" is legal, amount must satisfy:
          state["min_raise"] <= amount <= state["max_raise"]
        - when state["call_amount"] == 0, returning ("call", None) checks

        --------------------------------------------------
        example (simple strategy):

        if "raise" in state["legal_actions"]:
            return ("raise", state["min_raise"])

        if "call" in state["legal_actions"]:
            return ("call", None)

        return ("fold", None)
        """

        # If calling requires a 4th or more of my pot, fold
        if state["call_amount"] >= get_current_chips(state) * 0.25: return ("fold", None)

        # If I can raise, and the pot is less than 1 10th of my pot, raise to 1 10th
        if "raise" in state["legal_actions"] and state["max_raise"] <= get_current_chips(state): return ("raise", get_current_chips(state) * 0.10)

        # If I can check, check
        if "check" in state["legal_actions"]: return ("check", None)

        # Otherwise, fold
        return ("fold", None)