from __future__ import annotations

from bot_base import BaseBot


class AllInBot(BaseBot):
    def act(self, state: dict) -> tuple:
        if      "raise" in state["legal_actions"]:  return ("raise", state.get("max_raise", state.get("min_raise", 0)))
        elif    "call"  in state["legal_actions"]:  return ("call", None)
        else:                                       return ("fold", None)