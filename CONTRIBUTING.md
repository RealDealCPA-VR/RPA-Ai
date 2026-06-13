# Contributing

Thanks for your interest in improving the AI-Powered RPA System! This guide
covers local setup, running the test suite, the project layout, and how to send
a good pull request.

## Development setup

The project uses a standard PEP 621 layout (`pyproject.toml`). Work inside a
virtual environment and install the package in editable mode with the `dev`
and `gui` extras:

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2. Editable install with dev + gui extras
pip install -e .[dev,gui]
```

What the extras provide:

- **`dev`** — the test runner (`pytest`). Required to run the test suite.
- **`gui`** — real desktop-automation backends (`pyautogui`, `pynput`,
  `pillow`, `opencv-python`). Required only for live recording/execution; the
  prompt-parsing, validation, and dry-run APIs work without it.

> Tip: on a headless machine or CI, install just `pip install -e .[dev]` and use
> dry-run mode (`WorkflowExecutor(dry_run=True)` or the `--dry-run` CLI flag)
> plus `validate_workflow` to exercise the system without a display.

After installation the `ai-rpa` console command is available on your `PATH`.

## Running tests

```bash
pytest -q
```

`testpaths` is configured to `tests/` in `pyproject.toml`, so a bare `pytest`
discovers the suite from the project root. Run the quiet form above for a
concise summary; drop `-q` for verbose output, or pass a path/`-k` expression to
narrow the run:

```bash
pytest -q tests/test_validator.py
pytest -k "dry_run"
```

Please make sure the full suite passes before opening a pull request, and add
tests for any new behavior.

## Project layout

```
RPA/
├── pyproject.toml              # Packaging, extras, ai-rpa entry point, pytest config
├── CHANGELOG.md                # Keep a Changelog history
├── CONTRIBUTING.md             # This file
├── LICENSE                     # MIT
├── tests/                      # Pytest suite
├── workflows/                  # Default on-disk workflow storage (JSON)
└── ai_rpa_system/              # The package
    ├── __init__.py             # Public exports + __version__
    ├── __main__.py             # `python -m ai_rpa_system` entry
    ├── cli.py                  # `ai-rpa` argparse CLI (main(argv) -> int)
    ├── models.py               # Pydantic models (Workflow, ActionStep, ...)
    ├── prompt_parser.py        # Natural-language prompt -> actions
    ├── workflow_manager.py     # Recording, save/load, LLM export
    ├── automation_engine.py    # Low-level mouse/keyboard/screen backend
    ├── executor.py             # Workflow/prompt execution, dry-run, validate
    ├── validator.py            # Static validate_workflow()
    ├── py.typed                # PEP 561 marker (package is typed)
    └── README.md               # Package docs
```

The public API surface is whatever `ai_rpa_system/__init__.py` re-exports
(`__all__`). Prefer importing from the package root in tests and examples.

## Pull request guidance

- **Branch** off the default branch and keep each PR focused on a single change.
- **Keep the package typed.** The package ships `py.typed`; add type annotations
  to new public functions and keep existing ones accurate.
- **Add tests** for new features and bug fixes, and ensure `pytest -q` is green.
- **Update the docs.** If you change user-facing behavior, update the package
  `README.md` and add a bullet under the `Unreleased` section of `CHANGELOG.md`
  (Added / Changed / Fixed), following the Keep a Changelog style.
- **Mind headless safety.** New CLI subcommands and library entry points should
  remain importable and runnable without a display where reasonable; gate any
  real GUI work behind the `[gui]` extra and respect `dry_run`.
- **Write a clear PR description** explaining the motivation and the change, and
  link any related issue.

By contributing, you agree that your contributions are licensed under the
project's MIT License.
