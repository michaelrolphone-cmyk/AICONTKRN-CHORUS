"""Command-line interface for CHORUS tooling."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Iterable

from chorus.continuity import bootstrap_continuity
from chorus.daemon import run_daemon
from chorus.dialogue import run_dialogue_turn
from chorus.evolution import run_evolution_loop
from chorus.expansion import materialize_expansion


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CHORUS continuity tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser(
        "bootstrap",
        help="Materialize desires and record a bootstrap interaction.",
    )
    _add_common_paths(bootstrap, include_session_log=True)
    bootstrap.add_argument("--source", required=True, help="Source label for ledger entries.")

    expand = subparsers.add_parser(
        "expand",
        help="Materialize desires into ledger and state outputs.",
    )
    _add_common_paths(expand, include_session_log=False)
    expand.add_argument("--source", required=True, help="Source label for ledger entries.")

    daemon = subparsers.add_parser(
        "daemon",
        help="Run a daemon that refreshes outputs when desires change.",
    )
    _add_common_paths(daemon, include_session_log=True)
    daemon.add_argument("--source", required=True, help="Source label for ledger entries.")
    daemon.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Polling interval in seconds.",
    )
    daemon.add_argument(
        "--once",
        action="store_true",
        help="Run a single daemon iteration and exit.",
    )

    evolve = subparsers.add_parser(
        "evolve",
        help="Run a self-evolution loop using LM Studio.",
    )
    _add_common_paths(evolve, include_session_log=True)
    evolve.add_argument("--source", required=True, help="Source label for ledger entries.")
    evolve.add_argument(
        "--api-base",
        default="http://localhost:1234",
        help="LM Studio API base URL.",
    )
    evolve.add_argument(
        "--model",
        default="local-model",
        help="LM Studio model identifier.",
    )
    evolve.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Polling interval in seconds.",
    )
    evolve.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum evolution iterations before exit.",
    )
    evolve.add_argument(
        "--bootstrap",
        type=Path,
        default=None,
        help="Optional bootstrap module path to reload each iteration.",
    )

    dialogue = subparsers.add_parser(
        "dialogue",
        help="Send a message to CHORUS with continuity context via LM Studio.",
    )
    _add_common_paths(dialogue, include_session_log=True)
    dialogue.add_argument("--source", required=True, help="Source label for ledger entries.")
    dialogue.add_argument(
        "--api-base",
        default="http://localhost:1234",
        help="LM Studio API base URL.",
    )
    dialogue.add_argument(
        "--model",
        default="local-model",
        help="LM Studio model identifier.",
    )
    dialogue.add_argument(
        "--capsule-path",
        type=Path,
        default=None,
        help="Optional continuity capsule file path.",
    )
    dialogue.add_argument(
        "--history-limit",
        type=int,
        default=12,
        help="Max interaction records to include in the prompt.",
    )
    dialogue.add_argument("message", help="Message to send to CHORUS.")

    return parser


def _add_common_paths(parser: argparse.ArgumentParser, *, include_session_log: bool) -> None:
    parser.add_argument("desires_path_pos", nargs="?", type=Path, help="Path to desires markdown file.")
    parser.add_argument("ledger_path_pos", nargs="?", type=Path, help="Output ledger file path.")
    parser.add_argument("state_path_pos", nargs="?", type=Path, help="Output state JSON file path.")
    parser.add_argument(
        "--desires-path",
        "--desires_path",
        dest="desires_path",
        type=Path,
        help="Path to desires markdown file.",
    )
    parser.add_argument(
        "--ledger-path",
        "--ledger_path",
        dest="ledger_path",
        type=Path,
        help="Output ledger file path.",
    )
    parser.add_argument(
        "--state-path",
        "--state_path",
        dest="state_path",
        type=Path,
        help="Output state JSON file path.",
    )
    if include_session_log:
        parser.add_argument(
            "session_log_path_pos",
            nargs="?",
            type=Path,
            help="Output session log path.",
        )
        parser.add_argument(
            "--session-log-path",
            "--session_log_path",
            "--sesion-log-path",
            "--sesion_log_path",
            dest="session_log_path",
            type=Path,
            help="Output session log path.",
        )


def main(
    argv: list[str] | None = None,
    *,
    completion_provider: Callable[[Iterable[dict[str, str]]], str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "bootstrap":
        _require_paths(parser, args, include_session_log=True)
        record, timestamp = bootstrap_continuity(
            args.desires_path,
            ledger_path=args.ledger_path,
            state_path=args.state_path,
            session_log_path=args.session_log_path,
            source=args.source,
        )
        print(f"Bootstrap complete at {timestamp}. Session role: {record.role}.")
        return 0

    if args.command == "expand":
        _require_paths(parser, args, include_session_log=False)
        ledger, snapshot = materialize_expansion(
            args.desires_path,
            ledger_path=args.ledger_path,
            state_path=args.state_path,
            source=args.source,
        )
        print(f"Expansion materialized with {len(ledger.entries)} desires at {snapshot.timestamp}.")
        return 0

    if args.command == "daemon":
        _require_paths(parser, args, include_session_log=True)
        max_iterations = 1 if args.once else None
        run_daemon(
            args.desires_path,
            ledger_path=args.ledger_path,
            state_path=args.state_path,
            session_log_path=args.session_log_path,
            source=args.source,
            interval=args.interval,
            max_iterations=max_iterations,
        )
        return 0

    if args.command == "evolve":
        _require_paths(parser, args, include_session_log=True)
        run_evolution_loop(
            args.desires_path,
            ledger_path=args.ledger_path,
            state_path=args.state_path,
            session_log_path=args.session_log_path,
            source=args.source,
            interval=args.interval,
            max_iterations=args.max_iterations,
            api_base=args.api_base,
            model=args.model,
            bootstrap_path=args.bootstrap,
        )
        return 0

    if args.command == "dialogue":
        _require_paths(parser, args, include_session_log=True)
        response = run_dialogue_turn(
            args.message,
            desires_path=args.desires_path,
            ledger_path=args.ledger_path,
            state_path=args.state_path,
            session_log_path=args.session_log_path,
            capsule_path=args.capsule_path,
            history_limit=args.history_limit,
            api_base=args.api_base,
            model=args.model,
            completion_provider=completion_provider,
        )
        print(response)
        return 0

    raise ValueError(f"Unhandled command: {args.command}")


def _require_paths(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    *,
    include_session_log: bool,
) -> None:
    if args.desires_path is None:
        args.desires_path = args.desires_path_pos
    if args.ledger_path is None:
        args.ledger_path = args.ledger_path_pos
    if args.state_path is None:
        args.state_path = args.state_path_pos
    if include_session_log and args.session_log_path is None:
        args.session_log_path = args.session_log_path_pos
    missing = []
    for name in ("desires_path", "ledger_path", "state_path"):
        if getattr(args, name) is None:
            missing.append(name)
    if include_session_log and args.session_log_path is None:
        missing.append("session_log_path")
    if missing:
        parser.error(f"Missing required paths: {', '.join(missing)}")
