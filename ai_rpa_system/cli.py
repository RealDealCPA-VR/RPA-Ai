"""
Command-line interface for the AI-Powered RPA system.

Exposes ``main(argv=None) -> int`` built on argparse. Every subcommand is safe
to invoke headlessly (the only operations that touch the real GUI are actual,
non-dry workflow/prompt runs). ``main`` never raises on user error: it prints a
message and returns a non-zero exit code instead.

Wired as the ``ai-rpa`` console entry point by the packaging configuration.
"""

import argparse
import json
import sys
import time
from typing import List, Optional, Dict

from . import (
    __version__,
    WorkflowExecutor,
    WorkflowManager,
    PromptParser,
    Workflow,
    validate_workflow,
    scan_workflow,
)


def _safe_print(text: str) -> None:
    """Print ``text`` without dying on a narrow console codec (e.g. Windows
    cp1252 vs the U+2713/U+2717 marks in ExecutionResult summaries)."""
    try:
        print(text)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        sys.stdout.write(text.encode(enc, errors="replace").decode(enc) + "\n")


def _parse_vars(pairs: Optional[List[str]]) -> Dict[str, str]:
    """Turn a list of ``key=value`` strings into a dict.

    Raises ``ValueError`` for malformed entries so callers can surface a clean
    error and exit non-zero rather than crashing.
    """
    variables: Dict[str, str] = {}
    for item in pairs or []:
        if "=" not in item:
            raise ValueError(f"Invalid --var '{item}' (expected key=value)")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid --var '{item}' (empty key)")
        variables[key] = value
    return variables


def _prompt_to_actions(parser: PromptParser, prompt: str):
    """Parse a prompt into a list of PromptAction(s), mirroring executor logic."""
    if any(sep in prompt.lower() for sep in ["then", "and then", "next", "after that"]):
        return parser.parse_multi_step(prompt)
    return [parser.parse(prompt)]


def _load_workflow_for_scan(args) -> Optional[Workflow]:
    """Load a Workflow from ``--file PATH`` or a saved ``NAME`` for scanning.

    Returns the Workflow, or ``None`` after printing an error to stderr when it
    cannot be loaded (caller should treat ``None`` as a failure).
    """
    if getattr(args, "file", None):
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                text = fh.read()
            return Workflow(**json.loads(text))
        except Exception as exc:  # noqa: BLE001 - surface as clean CLI error
            print(f"Error loading workflow file '{args.file}': {exc}", file=sys.stderr)
            return None
    if getattr(args, "name", None):
        manager = WorkflowManager(storage_dir=args.dir)
        workflow = manager.load_workflow(args.name)
        if workflow is None:
            print(f"Workflow '{args.name}' not found.", file=sys.stderr)
            return None
        return workflow
    print("scan requires NAME or --file PATH.", file=sys.stderr)
    return None


def _confirm_real_run(args) -> Optional[int]:
    """Gate a REAL (non-dry-run) execution behind an explicit confirmation.

    Returns ``None`` when it is safe to proceed with the real run, or a non-zero
    int exit code that the caller must return WITHOUT performing real actions.

    Rules (never trigger a blocking ``input()`` in tests / non-interactive use):
      * dry-run never needs confirmation -> proceed.
      * ``--yes`` -> proceed.
      * stdin is not a TTY (tests, pipes) -> do NOT prompt; refuse the real run
        with a clear message and a non-zero code.
      * interactive TTY without ``--yes`` -> prompt once; proceed only on y/yes.
    """
    if getattr(args, "dry_run", False):
        return None
    if getattr(args, "yes", False):
        return None

    is_tty = False
    try:
        is_tty = bool(sys.stdin) and sys.stdin.isatty()
    except Exception:  # noqa: BLE001 - some streams lack isatty
        is_tty = False

    if not is_tty:
        print(
            "Refusing to perform a REAL run without confirmation. "
            "Re-run with --dry-run to simulate, or pass --yes to proceed.",
            file=sys.stderr,
        )
        return 3

    print(
        "WARNING: this will perform REAL mouse/keyboard/application actions on "
        "your machine."
    )
    try:
        answer = input("Proceed? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = ""
    if answer not in ("y", "yes"):
        print("Aborted.", file=sys.stderr)
        return 3
    return None


# --------------------------------------------------------------------------- #
# Subcommand handlers. Each returns an int exit code.
# --------------------------------------------------------------------------- #

def _cmd_version(args) -> int:
    print(__version__)
    return 0


def _cmd_list(args) -> int:
    manager = WorkflowManager(storage_dir=args.dir)
    workflows = manager.list_workflows()
    if not workflows:
        print("No workflows found.")
        return 0
    for wf in workflows:
        name = wf.get("name")
        steps = wf.get("steps", 0)
        description = wf.get("description") or ""
        print(f"{name} ({steps} steps) - {description}")
    return 0


def _cmd_parse(args) -> int:
    parser = PromptParser()
    actions = _prompt_to_actions(parser, args.prompt)
    print(json.dumps([pa.model_dump() for pa in actions], indent=2, default=str))
    return 0


def _cmd_validate(args) -> int:
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                text = fh.read()
            workflow = Workflow(**json.loads(text))
        except Exception as exc:
            print(f"Error loading workflow file '{args.file}': {exc}", file=sys.stderr)
            return 1
    elif args.name:
        manager = WorkflowManager(storage_dir=args.dir)
        workflow = manager.load_workflow(args.name)
        if workflow is None:
            print(f"Workflow '{args.name}' not found.", file=sys.stderr)
            return 1
    else:
        print("validate requires NAME or --file PATH.", file=sys.stderr)
        return 1

    issues = validate_workflow(workflow)
    if not issues:
        print("Workflow is valid.")
        return 0
    print(f"Workflow is invalid ({len(issues)} issue(s)):")
    for issue in issues:
        print(f"  - {issue}")
    return 1


def _cmd_export(args) -> int:
    manager = WorkflowManager(storage_dir=args.dir)
    print(manager.export_workflow_for_llm(args.name))
    return 0


def _cmd_scan(args) -> int:
    """Load a workflow and run the security scanner.

    Prints findings grouped by severity and returns exit code 1 when any
    CRITICAL finding exists, else 0.
    """
    workflow = _load_workflow_for_scan(args)
    if workflow is None:
        return 1

    findings = scan_workflow(workflow)

    order = ("critical", "major", "minor")
    grouped: Dict[str, list] = {sev: [] for sev in order}
    for finding in findings:
        sev = getattr(finding, "severity", "minor")
        grouped.setdefault(sev, []).append(finding)

    if not findings:
        print("No security findings.")
        return 0

    critical_count = len(grouped.get("critical", []))
    print(f"Security scan: {len(findings)} finding(s).")
    for sev in order:
        items = grouped.get(sev, [])
        if not items:
            continue
        print(f"\n{sev.upper()} ({len(items)}):")
        for finding in items:
            category = getattr(finding, "category", "")
            step_index = getattr(finding, "step_index", -1)
            message = getattr(finding, "message", str(finding))
            print(f"  - [{category}] step {step_index}: {message}")
    # Any other (unknown) severities, surfaced so nothing is silently dropped.
    for sev, items in grouped.items():
        if sev in order or not items:
            continue
        print(f"\n{sev.upper()} ({len(items)}):")
        for finding in items:
            print(f"  - {finding}")

    return 1 if critical_count else 0


def _cmd_run_prompt(args) -> int:
    try:
        variables = _parse_vars(args.var)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    gate = _confirm_real_run(args)
    if gate is not None:
        return gate

    executor = WorkflowExecutor(dry_run=args.dry_run)

    # Build the workflow from the prompt ourselves (mirroring execute_prompt) so
    # we can route through execute_workflow with the security/audit options.
    prompt_actions = _prompt_to_actions(executor.parser, args.prompt)
    all_steps = []
    for action in prompt_actions:
        all_steps.extend(action.suggested_steps)

    extra_warnings: List[str] = []
    low_conf = [a for a in prompt_actions if a.confidence < 0.3]
    if low_conf:
        lowest = min(a.confidence for a in low_conf)
        extra_warnings.append(
            f"Low parse confidence (lowest {lowest:.2f}); the generated "
            f"workflow may not accurately reflect the prompt: {args.prompt!r}"
        )
    if not all_steps:
        extra_warnings.append(
            f"No actionable steps were generated from the prompt: {args.prompt!r}"
        )

    workflow = Workflow(
        name=f"prompt_workflow_{int(time.time())}",
        description=args.prompt,
        steps=all_steps,
        variables=variables or {},
    )

    if args.save:
        executor.workflow_manager.save_workflow(workflow)

    result = executor.execute_workflow(
        workflow,
        variables=variables,
        extra_warnings=extra_warnings or None,
        allow_unsafe=getattr(args, "unsafe", False),
        audit_log=getattr(args, "audit", None),
    )
    _safe_print(result.to_llm_summary())
    return 0 if result.success else 1


def _cmd_run(args) -> int:
    try:
        variables = _parse_vars(args.var)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    gate = _confirm_real_run(args)
    if gate is not None:
        return gate

    manager = WorkflowManager(storage_dir=args.dir)
    executor = WorkflowExecutor(workflow_manager=manager, dry_run=args.dry_run)

    workflow = manager.load_workflow(args.name)
    if workflow is None:
        print(f"Workflow '{args.name}' not found.", file=sys.stderr)
        return 1

    result = executor.execute_workflow(
        workflow,
        variables=variables,
        take_screenshots=args.screenshots,
        allow_unsafe=getattr(args, "unsafe", False),
        audit_log=getattr(args, "audit", None),
    )
    _safe_print(result.to_llm_summary())
    return 0 if result.success else 1


# --------------------------------------------------------------------------- #
# Argument parser construction
# --------------------------------------------------------------------------- #

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-rpa",
        description="AI-Powered RPA system command-line interface.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
    )
    sub = parser.add_subparsers(dest="command")

    # version
    p_version = sub.add_parser("version", help="Print the package version.")
    p_version.set_defaults(func=_cmd_version)

    # list
    p_list = sub.add_parser("list", help="List saved workflows.")
    p_list.add_argument("--dir", default="workflows", help="Workflow storage directory.")
    p_list.set_defaults(func=_cmd_list)

    # parse
    p_parse = sub.add_parser("parse", help="Parse a prompt into PromptAction JSON.")
    p_parse.add_argument("prompt", help="Natural-language prompt to parse.")
    p_parse.set_defaults(func=_cmd_parse)

    # validate
    p_validate = sub.add_parser("validate", help="Validate a saved workflow or JSON file.")
    p_validate.add_argument("name", nargs="?", help="Name of a saved workflow.")
    p_validate.add_argument("--file", help="Path to a workflow JSON file.")
    p_validate.add_argument("--dir", default="workflows", help="Workflow storage directory.")
    p_validate.set_defaults(func=_cmd_validate)

    # export
    p_export = sub.add_parser("export", help="Print the LLM-friendly export of a workflow.")
    p_export.add_argument("name", help="Name of the workflow to export.")
    p_export.add_argument("--dir", default="workflows", help="Workflow storage directory.")
    p_export.set_defaults(func=_cmd_export)

    # scan
    p_scan = sub.add_parser("scan", help="Security-scan a saved workflow or JSON file.")
    p_scan.add_argument("name", nargs="?", help="Name of a saved workflow.")
    p_scan.add_argument("--file", help="Path to a workflow JSON file.")
    p_scan.add_argument("--dir", default="workflows", help="Workflow storage directory.")
    p_scan.set_defaults(func=_cmd_scan)

    # run-prompt
    p_run_prompt = sub.add_parser("run-prompt", help="Execute a natural-language prompt.")
    p_run_prompt.add_argument("prompt", help="Natural-language prompt to execute.")
    p_run_prompt.add_argument("--dry-run", action="store_true", help="Simulate without acting.")
    p_run_prompt.add_argument("--save", action="store_true", help="Save the generated workflow.")
    p_run_prompt.add_argument(
        "--var", action="append", metavar="KEY=VALUE", help="Variable substitution (repeatable)."
    )
    p_run_prompt.add_argument(
        "--unsafe", action="store_true",
        help="Skip the security scan and run even with CRITICAL findings.",
    )
    p_run_prompt.add_argument("--audit", metavar="PATH", help="Append per-step audit JSON lines to PATH.")
    p_run_prompt.add_argument(
        "--yes", action="store_true", help="Skip the real-run confirmation prompt.",
    )
    p_run_prompt.set_defaults(func=_cmd_run_prompt)

    # run
    p_run = sub.add_parser("run", help="Execute a saved workflow by name.")
    p_run.add_argument("name", help="Name of the workflow to run.")
    p_run.add_argument("--dir", default="workflows", help="Workflow storage directory.")
    p_run.add_argument("--dry-run", action="store_true", help="Simulate without acting.")
    p_run.add_argument("--screenshots", action="store_true", help="Capture screenshots per step.")
    p_run.add_argument(
        "--var", action="append", metavar="KEY=VALUE", help="Variable substitution (repeatable)."
    )
    p_run.add_argument(
        "--unsafe", action="store_true",
        help="Skip the security scan and run even with CRITICAL findings.",
    )
    p_run.add_argument("--audit", metavar="PATH", help="Append per-step audit JSON lines to PATH.")
    p_run.add_argument(
        "--yes", action="store_true", help="Skip the real-run confirmation prompt.",
    )
    p_run.set_defaults(func=_cmd_run)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point. Parse ``argv`` (default ``sys.argv[1:]``) and dispatch.

    Returns an int exit code and never raises on user/runtime error.
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = _build_parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse calls sys.exit on bad input / --help / --version. Translate
        # that into a returned exit code so main() is test-safe.
        code = exc.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        return 2

    if not getattr(args, "command", None):
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001 - CLI must not propagate exceptions
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
