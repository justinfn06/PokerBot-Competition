from __future__ import annotations

import random

from bot_base import BaseBot


class RandomBot(BaseBot):
    def act(self, state: dict) -> tuple:
        legal_actions = list(state["legal_actions"])
        action = random.choice(legal_actions)

        if action != "raise":
            return (action, None)

        min_raise = state["min_raise"]
        max_raise = state["max_raise"]

        if min_raise is None or max_raise is None:
            return ("call", None)

        if min_raise == max_raise:
            return ("raise", min_raise)

        return ("raise", random.randint(min_raise, max_raise))
