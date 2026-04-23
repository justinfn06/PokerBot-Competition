from __future__ import annotations

from bot_base import BaseBot


class MyBot(BaseBot):
    """
    copy this file and rename `MyBot` to build your own poker bot.

    your bot will usually be instantiated like: MyBot("YourBotName")

    the engine calls `act(state)` every time it is your turn.
    """

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

        # replace this logic with your bot implementation.
        return ("fold", None)
