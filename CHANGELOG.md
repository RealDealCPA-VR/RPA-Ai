# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- **Secure-by-default workflow scanning.** New `scan_workflow(workflow, policy)`
  (exported from the package root) statically analyses a `Workflow` and returns
  `SecurityFinding`s at `critical`/`major`/`minor` severity. It is pure-Python
  and headless-safe (no GUI imports). `WorkflowExecutor.execute_workflow` now
  runs this scan by default (`safe=True`) and **refuses to execute any workflow
  with a CRITICAL finding** — a failed `ExecutionResult` is returned with the
  findings as `errors` and **no step is executed**. MAJOR/MINOR findings are
  surfaced as `warnings` and never block.
- **CRITICAL detection (narrow by design).** Flags genuinely destructive,
  command-shaped text in `text`/`target`/`notes`/`description`
  (`destructive_command`: recursive force-deletes, disk formatting, registry
  destruction, fork bombs, `curl | sh`, `DROP`/`TRUNCATE TABLE`, …), shell/script
  hosts launched via `open_application`/`close_application` (`shell_launch`:
  `cmd`, `powershell`, `bash`, `wscript`, `mshta`, `rundll32`, …), over-long
  workflows (`workflow_too_long`, default `max_steps=200`), and excessive
  waits/timeouts (`excessive_wait`, default `max_wait_seconds=300`). Patterns
  are anchored to command syntax so ordinary prose does not match.
- **Overrides.** `execute_workflow(..., allow_unsafe=True)` (CLI `--unsafe`)
  skips the scan for trusted input; a custom `SafetyPolicy` can tune thresholds
  and blocklists without disabling the scan.
- **Path-traversal-safe screenshots.** Screenshot output is confined to the
  executor's `screenshot_dir`. A `screenshot` step's `notes` filename is
  sanitized — absolute paths, `..` traversal, leading separators, and
  drive-letter/colon forms are rejected and replaced with an auto-generated safe
  name, and the resolved path is verified to stay under `screenshot_dir`.
- **Secret redaction.** Steps marked `sensitive=True` are typed via
  `type_text(..., sensitive=True)` so the backend never logs the raw text. The
  optional audit log **never writes raw step text** and records sensitive steps
  as `"[REDACTED]"`.
- **Audit logging.** `execute_workflow(..., audit_log=PATH)` (CLI `--audit PATH`)
  appends one JSON line per executed step (`step`, `action`, `success`,
  `dry_run`, `ts_monotonic`); audit I/O failures are swallowed so they can never
  break a run.
- **Real-run confirmation gate.** The CLI refuses a REAL (non-dry) `run`/
  `run-prompt` without confirmation: it prompts once on an interactive TTY and
  refuses in non-interactive/piped contexts unless `--yes` is passed.
- **`SafetyError` exception.** Added to the public exception hierarchy
  (`RPAError` → `SafetyError`/`WorkflowValidationError`/`ExecutionError`).

### Added

- **`wait_for_element` action.** New `ActionStep` action that polls the screen
  for `image_path` until it appears or `timeout` elapses (polling every
  `poll_interval`), returning the matched `location` on success and failing on
  timeout. Defaults: `timeout` 10.0s and `poll_interval` 0.5s when left as
  `None`. Added to the supported/validated action set (now 15 actions).
- **`ActionStep` control-flow & security fields.** `repeat` (int, `>= 1`,
  default 1) runs a step N times and fails on the first failing iteration;
  `optional` (bool) records a warning instead of an error when a step fails and
  skips retries; `sensitive` (bool) redacts the step's text in logs/audit;
  `timeout` and `poll_interval` (floats) tune `wait_for_element`.
- **New public exports.** `scan_workflow`, `SafetyPolicy`, and `SecurityFinding`
  (from `ai_rpa_system.security`) plus the `RPAError`, `SafetyError`,
  `WorkflowValidationError`, and `ExecutionError` exceptions are now exported
  from the package root.
- **`ai-rpa scan` subcommand.** Read-only security scan of a saved workflow
  (`NAME`) or a JSON file (`--file PATH`). Prints findings grouped by severity
  and exits non-zero only when a CRITICAL finding exists.
- **CLI security flags.** `run` and `run-prompt` gained `--unsafe` (skip the
  scan), `--audit PATH` (per-step audit log), and `--yes` (skip the real-run
  confirmation prompt).
- **Dry-run mode.** `WorkflowExecutor(dry_run=True)` simulates every supported
  action without touching the desktop. In a dry run, supported steps succeed
  immediately and are tagged with `dry_run: True` and a `simulated` message in
  their step result; `wait_before`, `wait_after`, retry back-off sleeps, and
  per-step screenshots are all skipped so headless/CI runs are instant and
  side-effect free. Unknown actions still fall through to the real dispatch so
  they continue to surface the standard "Unknown action type" failure.
- **Static workflow validation.** New `validate_workflow(workflow)` function
  (exported from the package root) statically checks a `Workflow` for
  structural problems and returns a list of human-readable, 1-based-indexed
  issue messages (empty list means valid). It is dependency-free and
  headless-safe, and covers the 14 known action types, coordinate/end-coordinate
  shape, confidence range `[0.0, 1.0]`, and per-action required fields
  (e.g. `type` needs non-empty text, `hotkey` needs at least 2 keys, `drag`
  needs end coordinates or a note with two numbers).
- **`execute_workflow(..., validate=True)`.** `WorkflowExecutor.execute_workflow`
  accepts a `validate` flag; when enabled the workflow is validated first and, if
  any issues are found, a failed `ExecutionResult` is returned with the issues as
  `errors` and **no steps executed**. A companion `extra_warnings` parameter lets
  callers prepend warnings to the result.
- **`ai-rpa` command-line interface.** A new console entry point (wired via
  `[project.scripts]`) exposing `main(argv=None) -> int`, built on argparse and
  safe to invoke headlessly. Subcommands: `version`, `list`, `parse`,
  `validate`, `export`, `run-prompt`, and `run`, with flags including
  `--dry-run`, `--save`, `--screenshots`, `--var KEY=VALUE` (repeatable), and
  `--dir`. The CLI never propagates exceptions: it prints a message and returns a
  non-zero exit code instead. See the README "Command-Line Interface" section.
- **`py.typed` marker.** The package now ships a `py.typed` file (declared in
  `package-data`), so downstream type checkers treat `ai_rpa_system` as typed
  and consume its inline annotations.

### Changed

- **`updated_at` is now bumped on save.** `WorkflowManager.save_workflow` sets
  `workflow.updated_at = datetime.now()` immediately before serializing, so the
  persisted timestamp always reflects the most recent save.

### Fixed

- **Unicode-safe CLI output.** Result summaries that contain the U+2713/U+2717
  check/cross marks no longer crash on narrow console codecs (e.g. Windows
  cp1252); output is re-encoded with replacement when the stdout codec cannot
  represent a character.
- **`--var` parsing errors are reported cleanly.** Malformed `key=value` pairs
  (missing `=` or empty key) cause the CLI to print a clear error and exit
  non-zero rather than crashing.
- **Dry runs no longer double-count `wait`.** A `wait` action consumes its
  duration inside step execution, so `wait_after` is not applied again for it.

## [1.0.0]

### Added

- Initial release of the AI-Powered RPA System.
- Natural-language prompt parsing into action sequences (`PromptParser`,
  including multi-step prompts).
- Workflow recording and storage (`WorkflowRecorder`, `WorkflowManager`) with
  JSON, LLM-friendly persistence.
- Workflow execution engine (`WorkflowExecutor`, `AutomationEngine`) with
  variable substitution, retries, and per-step screenshots.
- Pydantic models: `Workflow`, `ActionStep`, `PromptAction`, `ExecutionResult`.
- Optional `[gui]` extra for real desktop automation (pyautogui/pynput/pillow/
  opencv) and `[dev]` extra for the test suite.

[Unreleased]: https://example.com/ai-rpa-system/compare/v1.0.0...HEAD
[1.0.0]: https://example.com/ai-rpa-system/releases/tag/v1.0.0
