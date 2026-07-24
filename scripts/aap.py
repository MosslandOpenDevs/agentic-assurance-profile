#!/usr/bin/env python3
"""aap — thin, read-only alpha CLI facade over the v0.4 assurance engine.

Source-checkout alpha. This is not a published package, and ``aap`` is a
provisional command name (see ``docs/V0.5-DESIGN.md`` §14). The only public
surface in this alpha is::

    aap check [--project-root PATH] [--adoption PATH] [--repo-visibility V]

``aap check`` runs an ``ADOPTER_SNAPSHOT`` evaluation of the current checkout.
It resolves the three low-level paths that a bare ``validate.py adopter``
invocation demands — ``--adoption``, ``--project-root``, and ``--schemas`` —
and then forwards an otherwise-unchanged evaluation to ``scripts/validate.py``.
The engine's behavior is not modified: this file only hides plumbing and maps
the result onto a small, explicit exit-code contract.

Deliberately narrow scope for this alpha:

* read-only, no network;
* current-worktree ``ADOPTER_SNAPSHOT`` only — no drift/transition, no
  ``base``/``head`` comparison;
* the existing v0.4 engine, unchanged;
* no public JSON contract, no stable finding codes, no ``init``/``review``/
  ``migrate``.

Exit codes::

    0  PASS      declared policy checks passed (engine reported no errors)
    1  FINDINGS  the engine reported at least one policy error
    2  USAGE     inputs could not be resolved (no adoption declaration found,
                 project root missing, or a bad option)
    3  INTERNAL  an unexpected error prevented evaluation

``PASS`` means only "the declared policy checks passed"; it is not a claim that
every possible check ran.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# The alpha ships from a profile source checkout; its schemas travel with it.
PROFILE_CHECKOUT = SCRIPT_DIR.parent

# Import the existing engine as a library so the facade drives the very same
# parser+handler the ``validate.py adopter`` CLI uses. Behavior cannot drift.
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import validate  # noqa: E402  (intentional: co-located engine module)

EXIT_PASS = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

ADOPTION_RELATIVE = Path(".agentic-assurance") / "adoption.yaml"


class UsageError(Exception):
    """A caller/environment input could not be resolved (maps to exit 2)."""


def _exit_for_engine_result(code: int) -> int:
    """Map the engine's 0/1 return onto the facade contract.

    The engine reports 0 (no errors) or 1 (errors). The richer 2/3 codes are
    owned by the facade and never originate here; an unexpected engine code is
    surfaced as ``INTERNAL`` rather than silently treated as success.
    """
    if code in (EXIT_PASS, EXIT_FINDINGS):
        return code
    return EXIT_INTERNAL


def resolve_snapshot_paths(project_root_arg, adoption_arg):
    """Resolve ``(project_root, adoption_path, schemas_dir)`` for a snapshot run.

    Raises :class:`UsageError` when the adopter inputs cannot be located, and
    :class:`RuntimeError` when the tool's own checkout is missing its schemas.
    """
    # Use ``.absolute()``, never ``.resolve()``: the engine deliberately
    # preserves symlinks in the paths it is handed — it does its own
    # containment resolution internally and emits distinct diagnostics for
    # in-project and non-portable symlinks. Pre-resolving here would collapse
    # those symlinks and diverge from ``validate.py adopter``, breaking the
    # behavior-preservation contract.
    if project_root_arg is not None:
        project_root = Path(project_root_arg).absolute()
    else:
        project_root = Path.cwd()
    if not project_root.is_dir():
        raise UsageError(f"project root is not a directory: {project_root}")

    if adoption_arg is not None:
        adoption_path = Path(adoption_arg).absolute()
    else:
        adoption_path = (project_root / ADOPTION_RELATIVE).absolute()
    if not adoption_path.is_file():
        raise UsageError(
            f"no adoption declaration at {adoption_path}. Run aap check from an "
            f"adopting repository, or pass --adoption / --project-root."
        )

    schemas_dir = (PROFILE_CHECKOUT / "schemas").resolve()
    if not schemas_dir.is_dir():
        raise RuntimeError(f"profile schemas directory missing at {schemas_dir}")

    return project_root, adoption_path, schemas_dir


def cmd_check(args) -> int:
    try:
        project_root, adoption_path, schemas_dir = resolve_snapshot_paths(
            args.project_root, args.adoption
        )
    except UsageError as exc:
        print(f"aap check: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except Exception as exc:  # broken tool checkout, unreadable path, etc.
        print(f"aap check: internal error: {exc}", file=sys.stderr)
        return EXIT_INTERNAL

    argv = [
        "adopter",
        "--adoption", os.fspath(adoption_path),
        "--project-root", os.fspath(project_root),
        "--schemas", os.fspath(schemas_dir),
    ]
    if args.repo_visibility is not None:
        argv += ["--repo-visibility", args.repo_visibility]

    try:
        engine_code = validate.main(argv)
    except SystemExit as exc:  # e.g. an argparse rejection inside the engine
        code = exc.code
        if isinstance(code, int):
            if code in (EXIT_PASS, EXIT_FINDINGS):
                return code
            if code == EXIT_USAGE:
                return EXIT_USAGE
        return EXIT_INTERNAL
    except Exception as exc:
        print(f"aap check: internal error during evaluation: {exc}", file=sys.stderr)
        return EXIT_INTERNAL

    result = _exit_for_engine_result(engine_code)
    if result == EXIT_PASS:
        print("aap check: PASS — declared policy checks passed (ADOPTER_SNAPSHOT).")
    elif result == EXIT_FINDINGS:
        print(
            "aap check: FINDINGS — the engine reported policy errors above "
            "(ADOPTER_SNAPSHOT)."
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aap",
        description="Agentic Assurance Profile — alpha CLI (source-checkout).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser(
        "check",
        help="run a read-only ADOPTER_SNAPSHOT check of the current checkout "
        "against the pinned profile (no network)",
    )
    check.add_argument(
        "--project-root",
        default=None,
        help="root of the adopting repository (default: current directory)",
    )
    check.add_argument(
        "--adoption",
        default=None,
        help="path to the adoption declaration (default: "
        "<project-root>/.agentic-assurance/adoption.yaml)",
    )
    check.add_argument(
        "--repo-visibility",
        default=None,
        choices=list(validate.REPO_VISIBILITIES),
        help="repository visibility; private/internal relaxes RESTRICTED/"
        "EMBARGOED entries per ADOPTION.md (default: public strictness)",
    )
    check.set_defaults(handler=cmd_check)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
