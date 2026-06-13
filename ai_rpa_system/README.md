# AI-Powered RPA System

An intelligent Robotic Process Automation system that uses natural language prompts to automate desktop activities. The system can record, learn, and execute repeatable workflows that are fully compatible with LLM integration.

## Features

- **Natural Language Control**: Use simple prompts to define automation tasks
- **Workflow Recording**: Record desktop actions and convert them to reusable workflows
- **LLM Integration**: Workflows are structured for easy LLM interpretation and execution
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Repeatable Processes**: Save and replay workflows with variable substitution
- **Smart Action Recognition**: Automatically identifies UI elements and actions

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
│              (Natural Language Prompts)                  │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                 Prompt Parser                            │
│         (Converts prompts to action sequences)           │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              Workflow Manager                            │
│    (Records, stores, and retrieves workflows)            │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│            Automation Engine                             │
│  (Executes actions: click, type, scroll, etc.)          │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              Desktop Interface                           │
│        (Mouse, Keyboard, Screen capture)                 │
└──────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Core install (prompt parsing + workflow execution APIs)
pip install -e .

# Enable real desktop automation (pyautogui/pynput) and recording
pip install -e .[gui]
```

## Quick Start

### 1. Record a Workflow
Recording requires the optional `[gui]` dependencies (see Installation).
```python
from ai_rpa_system import WorkflowRecorder, WorkflowManager

recorder = WorkflowRecorder()
recorder.start_recording("login_workflow")
# Perform your desktop actions
wf = recorder.stop_recording()
WorkflowManager().save_workflow(wf)
```

### 2. Execute with Prompt
```python
from ai_rpa_system import WorkflowExecutor

executor = WorkflowExecutor()
executor.execute_prompt("Open Chrome and navigate to example.com")
```

### 3. Use Saved Workflows
```python
executor.execute_workflow_by_name("login_workflow", variables={
    "username": "user@example.com",
    "password": "secure_password"
})
```

## Workflow Format

Workflows are stored in JSON format that's easily parseable by LLMs:

```json
{
  "name": "example_workflow",
  "description": "Opens browser and logs in",
  "steps": [
    {
      "action": "click",
      "target": "Chrome icon",
      "coordinates": [100, 200],
      "description": "Launch Chrome browser"
    },
    {
      "action": "type",
      "text": "{{username}}",
      "description": "Enter username"
    }
  ]
}
```

## Use Cases

- Form filling automation
- Data entry tasks
- Application testing
- Report generation
- Email automation
- File management
- Web scraping with UI interaction

## Command-Line Interface

After installing the package (`pip install -e .`), an `ai-rpa` console command is
available. It wraps the same library API, returns proper exit codes, and never
raises on user error — it prints a message and exits non-zero instead. You can
also run it as a module with `python -m ai_rpa_system`.

```bash
ai-rpa --help
ai-rpa --version
```

### Subcommands

| Command | Description |
| --- | --- |
| `version` | Print the package version. |
| `list` | List saved workflows (`--dir` to choose the storage directory). |
| `parse PROMPT` | Parse a natural-language prompt into `PromptAction` JSON. |
| `validate [NAME] [--file PATH]` | Validate a saved workflow (by name) or a workflow JSON file. |
| `export NAME` | Print the LLM-friendly export of a saved workflow. |
| `scan [NAME] [--file PATH]` | Security-scan a saved workflow (by name) or a JSON file and print findings. |
| `run-prompt PROMPT` | Execute a natural-language prompt. |
| `run NAME` | Execute a saved workflow by name. |

### Common options

- `--dir DIR` — workflow storage directory (default: `workflows`). Applies to
  `list`, `validate`, `export`, and `run`.
- `--dry-run` — simulate without touching the desktop (`run-prompt`, `run`).
- `--save` — save the generated workflow (`run-prompt`).
- `--screenshots` — capture a screenshot per step (`run`).
- `--var KEY=VALUE` — variable substitution; repeatable (`run-prompt`, `run`).
- `--unsafe` — skip the security scan and run even with CRITICAL findings
  (`run-prompt`, `run`). Use only for trusted, reviewed inputs.
- `--audit PATH` — append one per-step audit JSON line to `PATH` (`run-prompt`,
  `run`). Raw step text is never written; sensitive steps record `[REDACTED]`.
- `--yes` — skip the real-run confirmation prompt (`run-prompt`, `run`). A real
  (non-dry) run is refused without confirmation in non-interactive contexts.

### Examples

```bash
# List saved workflows in a custom directory
ai-rpa list --dir ./workflows

# Parse a prompt to JSON (great for piping into an LLM)
ai-rpa parse "Open Chrome then type hello"

# Validate a saved workflow or a JSON file on disk
ai-rpa validate login_workflow
ai-rpa validate --file ./my_workflow.json

# Export a workflow in LLM-friendly form
ai-rpa export login_workflow

# Security-scan a workflow before running it (exits non-zero on CRITICAL)
ai-rpa scan login_workflow
ai-rpa scan --file ./my_workflow.json

# Dry-run a prompt with variables (no desktop side effects)
ai-rpa run-prompt "Log in as {{user}}" --var user=alice --dry-run

# Run a saved workflow with screenshots
ai-rpa run login_workflow --var username=alice --var password=secret --screenshots
```

Exit codes: `0` on success, `1` for failures (invalid workflow, not found,
runtime errors), and `2` for malformed `--var` input.

## Dry-run & Validation

Two features make it safe to develop and test workflows without a display or any
real desktop side effects — ideal for CI and headless machines.

### Dry-run mode

Construct an executor with `dry_run=True` (or pass `--dry-run` on the CLI) to
simulate every supported action instead of performing it:

```python
from ai_rpa_system import WorkflowExecutor

executor = WorkflowExecutor(dry_run=True)
result = executor.execute_prompt("Open Chrome and type hello")
print(result.to_llm_summary())
```

In a dry run, supported steps succeed immediately and are tagged with
`dry_run: True` plus a `simulated` message in their step result. All sleeps
(`wait_before`, `wait_after`, retry back-off) and per-step screenshots are
skipped, so runs are instant and side-effect free. Unknown action types still
fall through to the normal dispatch and produce the standard
"Unknown action type" failure.

### Static validation

`validate_workflow` statically checks a `Workflow` and returns a list of
human-readable, 1-based-indexed issue messages. An empty list means the workflow
is valid. It is dependency-free and headless-safe.

```python
from ai_rpa_system import validate_workflow, WorkflowManager

workflow = WorkflowManager().load_workflow("login_workflow")
issues = validate_workflow(workflow)
if issues:
    for issue in issues:
        print(issue)
else:
    print("Workflow is valid.")
```

Validation covers the 14 known action types, coordinate/end-coordinate shape
(a list of exactly two ints), the confidence range `[0.0, 1.0]`, and per-action
required fields — for example, `type` requires non-empty text, `press_key`
requires a key, `hotkey` requires at least two keys, and `drag` requires
end coordinates (or a note containing two numbers).

### Validate before executing

`execute_workflow` accepts `validate=True`. When enabled, the workflow is checked
first and, if any issues are found, a failed `ExecutionResult` is returned with
the issues as `errors` and **no steps executed**:

```python
result = executor.execute_workflow(workflow, validate=True)
if not result.success:
    print(result.errors)
```

Combine `dry_run=True` with `validate=True` to fully exercise a workflow's
structure and flow without performing any real desktop actions.

## Security

The system is **secure by default**. Before executing, `execute_workflow` runs a
static, headless-safe security scan (`scan_workflow`) and **refuses to run any
workflow that contains a CRITICAL finding** — a failed `ExecutionResult` is
returned with the findings as `errors` and **no step is executed**. Non-critical
(MAJOR/MINOR) findings are surfaced as `warnings` and never block.

CRITICAL findings cover genuinely destructive, command-shaped operations
(recursive force-deletes, disk formatting, registry destruction, `curl | sh`,
`DROP TABLE`, …), launching a shell/script host via `open_application`,
over-long workflows (`max_steps`, default 200), and excessive waits
(`max_wait_seconds`, default 300s). The scanner is intentionally narrow, so
ordinary prose like "delete the old file" does **not** trip it.

```python
from ai_rpa_system import scan_workflow, SafetyPolicy, WorkflowExecutor

# Inspect a workflow without running it.
findings = scan_workflow(workflow)
for f in findings:
    print(f)  # e.g. [CRITICAL] destructive_command (step 2): ...

# Run normally (scan on by default); a CRITICAL finding blocks execution.
result = WorkflowExecutor().execute_workflow(workflow)

# Override for trusted input (skips the scan entirely).
result = WorkflowExecutor().execute_workflow(workflow, allow_unsafe=True)

# Or keep the scan and tune thresholds with a custom policy.
result = WorkflowExecutor().execute_workflow(
    workflow, policy=SafetyPolicy(max_steps=500, max_wait_seconds=600)
)
```

On the CLI, `--unsafe` (on `run` / `run-prompt`) skips the scan. Other
protections include **path-traversal-safe screenshot paths**, an **audit log**
that never writes raw step text, and **secret redaction** for steps marked
`sensitive=True`. See the top-level [SECURITY.md](../SECURITY.md) for the full
threat model, blocked patterns, and how to report issues.

### `ai-rpa scan` — read-only security scan

Scan a saved workflow or a JSON file and print findings grouped by severity
without executing anything. Exits non-zero only when a CRITICAL finding exists,
which makes it convenient as a pre-flight gate in CI or before a real run.

```bash
ai-rpa scan login_workflow            # a saved workflow by name
ai-rpa scan --file ./workflow.json    # a workflow JSON file on disk
ai-rpa scan login_workflow --dir ./workflows
```

Example output:

```
Security scan: 2 finding(s).

CRITICAL (1):
  - [destructive_command] step 2: 'text' matches a destructive command pattern (...).

MINOR (1):
  - [style] step 3: step has no human-readable description.
```

## New step features: `wait_for_element`, `repeat`, `optional`

These `ActionStep` capabilities make workflows more robust against timing and
flaky steps. They are opt-in and fully backward compatible.

### `wait_for_element` action

A new action type that **polls the screen for an image until it appears** or a
timeout elapses — ideal for waiting on UI that loads asynchronously instead of
guessing a fixed `wait`. It requires `image_path`; on success the step result
includes the found `location` as `[x, y]`, and on timeout the step fails.

```python
from ai_rpa_system import ActionStep

ActionStep(
    action="wait_for_element",
    description="Wait for the dashboard to load",
    image_path="dashboard_logo.png",
    timeout=30.0,        # seconds to keep polling (default 10.0 when None)
    poll_interval=0.5,   # seconds between checks  (default 0.5 when None)
    confidence=0.85,     # image-match threshold
)
```

### `repeat`

Execute a single step N times. The step succeeds only if **every** iteration
succeeds; the first failing iteration stops and is reported (with
`repeat_iteration` in the step result). Defaults to `1`, so existing workflows
are unchanged. Must be `>= 1`.

```python
ActionStep(action="press_key", key="down", repeat=10,
           description="Scroll down ten rows")
```

### `optional`

Mark a step that is allowed to fail. If an `optional` step fails (or its
surrounding machinery raises), the executor records a **warning instead of an
error** and does **not** fail the overall workflow or trigger retries.

```python
ActionStep(action="click", coordinates=[20, 20], optional=True,
           description="Dismiss the cookie banner if present")
```

## License

MIT License
