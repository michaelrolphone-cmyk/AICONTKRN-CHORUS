"""Command-line interface for CHORUS tooling."""

from __future__ import annotations

import argparse
from pathlib import Path

from chorus.continuity import bootstrap_continuity
from chorus.daemon import run_daemon
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

    return parser


def _add_common_paths(parser: argparse.ArgumentParser, *, include_session_log: bool) -> None:
    parser.add_argument("desires_path", type=Path, help="Path to desires markdown file.")
    parser.add_argument("ledger_path", type=Path, help="Output ledger file path.")
    parser.add_argument("state_path", type=Path, help="Output state JSON file path.")
    if include_session_log:
        parser.add_argument("session_log_path", type=Path, help="Output session log path.")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "bootstrap":
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
        ledger, snapshot = materialize_expansion(
            args.desires_path,
            ledger_path=args.ledger_path,
            state_path=args.state_path,
            source=args.source,
        )
        print(f"Expansion materialized with {len(ledger.entries)} desires at {snapshot.timestamp}.")
        return 0

    if args.command == "daemon":
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

    raise ValueError(f"Unhandled command: {args.command}")
