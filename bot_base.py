from __future__ import annotations


class BaseBot:
    def __init__(self, name: str):
        self.name = name

    def act(self, state: dict) -> tuple:
        """
        Returns one of:
        ("fold", None)
        ("call", None)
        ("raise", amount)
        """
        raise NotImplementedError
