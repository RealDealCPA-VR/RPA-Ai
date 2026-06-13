<div align="center">

# 🤖⚡ AI-Powered RPA System

### Turn plain English into real desktop automation — safely.

**Describe what you want. Get a repeatable, validated, LLM-ready workflow that clicks, types, and navigates your desktop for you.**

[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-186%20passing-brightgreen.svg)](#-tested-to-the-teeth)
[![Security](https://img.shields.io/badge/security-secure%20by%20default-success.svg)](#-secure-by-default-not-an-afterthought)
[![Typed](https://img.shields.io/badge/typing-py.typed-blueviolet.svg)](#)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Pydantic](https://img.shields.io/badge/pydantic-v2-e92063.svg)](https://docs.pydantic.dev/)

</div>

---

## 🚀 What is this?

A **production-grade Robotic Process Automation engine** built for the AI era. It converts natural-language prompts (or LLM-generated JSON) into structured, replayable workflows — and then runs them on your real desktop with **mouse, keyboard, and screen control**.

It was built **LLM-first**: every workflow is clean, validated JSON that a model can read, write, and refine. And it's **secure by default** — destructive automation is blocked before it ever touches your machine.

```python
from ai_rpa_system import WorkflowExecutor

executor = WorkflowExecutor(dry_run=True)          # preview safely first
result = executor.execute_prompt("open chrome then wait 2 seconds")
print(result.to_llm_summary())                     # ✓ Success: 2/2 steps in 0.00s
```

---

## ✨ Why you'll love it

| | |
|---|---|
| 🗣️ **Natural language → automation** | "click the login button, then type the password, then press enter" → a real workflow |
| 🧠 **LLM-native** | Workflows are strict, validated JSON — perfect for generate → execute → analyze loops |
| 🛡️ **Secure by default** | A built-in safety engine blocks `rm -rf`, `format`, `shutdown`, shell launches & more |
| 👀 **Dry-run mode** | Simulate an entire workflow with **zero real clicks** before going live |
| 🎯 **`wait_for_element`** | Poll-until-visible — the reliability primitive real automation lives or dies on |
| 🔁 **Repeat & optional steps** | Lightweight loops and fault-tolerant steps without branching spaghetti |
| 🔌 **One-line CLI** | `ai-rpa run`, `parse`, `validate`, `scan`, `export` — automation from your terminal |
| 📼 **Record & replay** | Capture your real mouse/keyboard actions into a reusable workflow |
| 🧾 **Audit logging** | JSONL trail of every executed step — with secrets redacted |
| 🖥️ **Cross-platform** | Windows, macOS, Linux — adapts automatically |
| 📦 **Headless-friendly** | Imports & tests with **no display and no GUI deps** (lazy-loaded) |

---

## ⚡ 60-second quick start

```bash
# Core (parsing, validation, dry-run, CLI) — no GUI needed:
pip install -e .

# Add real desktop control (mouse/keyboard/screen):
pip install -e .[gui]
```

### From the command line

```bash
ai-rpa version
ai-rpa parse "open chrome then wait 2 seconds"        # preview the parsed steps (JSON)
ai-rpa run-prompt "click the login button" --dry-run  # simulate — no real clicks
ai-rpa scan my_workflow                                # security-scan before running
ai-rpa run my_workflow --var username=alice --dry-run
```

### From Python

```python
from ai_rpa_system import Workflow, ActionStep, WorkflowExecutor

wf = Workflow(
    name="login",
    description="Log into the app",
    steps=[
        ActionStep(action="click",     description="username field", coordinates=[400, 200]),
        ActionStep(action="type",      description="enter user",     text="{{username}}"),
        ActionStep(action="press_key", description="tab",            key="tab"),
        ActionStep(action="type",      description="enter pass",     text="{{password}}", sensitive=True),
        ActionStep(action="press_key", description="submit",         key="enter"),
    ],
    variables={"username": "alice", "password": "secret"},
)

executor = WorkflowExecutor(dry_run=True)            # flip to dry_run=False for real
result = executor.execute_workflow(wf, validate=True)  # validate, then run
print(result.to_llm_summary())
```

---

## 🛡️ Secure by default (not an afterthought)

Most automation tools will happily run whatever they're told. This one won't.

Every execution is scanned first. **CRITICAL operations are blocked unless you explicitly opt in:**

```python
from ai_rpa_system import WorkflowExecutor, Workflow, ActionStep

danger = Workflow(name="oops", description="...", steps=[
    ActionStep(action="open_application", description="shell", target="powershell"),
])

WorkflowExecutor().execute_workflow(danger)            # ❌ blocked — CRITICAL: shell launch
WorkflowExecutor().execute_workflow(danger, allow_unsafe=True)   # ✅ you explicitly chose this
```

Hardened against the things that actually bite RPA tools:

- 🚫 **Command injection** — no `shell=True`; app launches use `os.startfile` / list-form `subprocess`
- 🚫 **Path traversal** — workflow names & screenshot paths are sanitized and confined to their directories
- 🚫 **Secret leakage** — `sensitive` steps are redacted in logs and the audit trail
- 🚫 **Untrusted JSON** — models use `extra="forbid"`, rejecting unknown fields from LLM output
- 🚫 **Runaway workflows** — step-count and wait-time limits

See [`SECURITY.md`](SECURITY.md) for the full threat model and responsible-use guidance.

> ⚠️ **Real runs control your actual mouse and keyboard.** Always `--dry-run` first. Safety valve: slam the mouse into a screen corner to abort (PyAutoGUI FAILSAFE).

---

## 🧪 Tested to the teeth

```bash
pytest -q     # 186 passed
```

**186 passing tests** covering models, parsing, execution, the validator, the safety engine, the CLI, path-traversal & injection defenses, secret redaction — and live pen-tests of every fix. Plus a GitHub Actions CI matrix across Python 3.9–3.12.

---

## 🏗️ Architecture

```
Natural language / LLM JSON
            │
            ▼
   ┌──────────────────┐     ┌──────────────────┐
   │  Prompt Parser   │     │    Validator     │  catch bad steps early
   └────────┬─────────┘     └──────────────────┘
            ▼
   ┌──────────────────┐     ┌──────────────────┐
   │ Workflow (JSON)  │────▶│  Safety Engine   │  block CRITICAL ops
   └────────┬─────────┘     └──────────────────┘
            ▼
   ┌──────────────────┐     ┌──────────────────┐
   │     Executor     │────▶│ Automation Engine│  mouse / keyboard / screen
   └──────────────────┘     └──────────────────┘
            │
            ▼
     ExecutionResult  ──▶  LLM-friendly summary + audit log
```

| Module | Role |
|---|---|
| `prompt_parser.py` | Natural language → structured action steps |
| `models.py` | Pydantic v2 models (`Workflow`, `ActionStep`, …), strict & JSON-serializable |
| `validator.py` | Pre-flight validation of every step |
| `security.py` | `scan_workflow()` + `SafetyPolicy` guardrails |
| `executor.py` | Variable substitution, retries, dry-run, audit logging |
| `automation_engine.py` | Cross-platform desktop control (lazy PyAutoGUI) |
| `workflow_manager.py` | Save/load/record workflows (path-safe, atomic) |
| `cli.py` | The `ai-rpa` command-line interface |

---

## 📚 Docs

- [`ai_rpa_system/QUICKSTART.md`](ai_rpa_system/QUICKSTART.md) — 5-minute setup
- [`ai_rpa_system/docs/USER_GUIDE.md`](ai_rpa_system/docs/USER_GUIDE.md) — full guide
- [`ai_rpa_system/docs/API_REFERENCE.md`](ai_rpa_system/docs/API_REFERENCE.md) — every class & method
- [`ai_rpa_system/docs/LLM_INTEGRATION.md`](ai_rpa_system/docs/LLM_INTEGRATION.md) — generate → execute → analyze patterns
- [`SECURITY.md`](SECURITY.md) — threat model & guarantees
- [`CHANGELOG.md`](CHANGELOG.md) · [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

## 🗺️ Roadmap

- 🔭 Vision-based element detection (OCR / template matching beyond images)
- 🌳 Conditional branching & richer loops in workflows
- 🗓️ Scheduling & triggers
- 🎛️ Visual workflow editor

---

## 📝 License

MIT — see [`LICENSE`](LICENSE). Built for the future of AI-powered automation. **Automate boldly. Automate safely.** 🚀
