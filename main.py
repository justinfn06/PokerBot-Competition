from __future__ import annotations

import argparse

from bots import ConservativeBot, RandomBot
from engine import PokerEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a Texas Hold'em bot match.")
    parser.add_argument(
        "--hands",
        type=int,
        default=10,
        help="Number of hands to run.",
    )
    parser.add_argument(
        "--stack",
        type=int,
        default=100,
        help="Starting stack for every player.",
    )
    parser.add_argument(
        "--small-blind",
        type=int,
        default=1,
        help="Small blind amount.",
    )
    parser.add_argument(
        "--big-blind",
        type=int,
        default=2,
        help="Big blind amount.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print extra debugging information.",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run the original terminal view instead of the desktop frontend.",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=1100,
        help="GUI playback delay between actions in milliseconds.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    bots = [
        ConservativeBot("Conservative_1"),
        RandomBot("Random_1"),
        RandomBot("Random_2"),
        ConservativeBot("Conservative_2"),
    ]

    if args.cli:
        engine = PokerEngine(
            bots=bots,
            starting_stack=args.stack,
            small_blind=args.small_blind,
            big_blind=args.big_blind,
            verbose=args.verbose,
        )
        engine.run(hand_count=args.hands)
        return

    from frontend import PokerFrontend

    app = PokerFrontend(
        bots=bots,
        hand_count=args.hands,
        starting_stack=args.stack,
        small_blind=args.small_blind,
        big_blind=args.big_blind,
        delay_ms=args.delay_ms,
    )
    app.run()


if __name__ == "__main__":
    main()
