# API Reference

Complete API documentation for the AI-Powered RPA System.

## Table of Contents

1. [Core Classes](#core-classes)
2. [Data Models](#data-models)
3. [Automation Engine](#automation-engine)
4. [Workflow Management](#workflow-management)
5. [Execution](#execution)
6. [Prompt Parsing](#prompt-parsing)

---

## Core Classes

### WorkflowExecutor

Main class for executing workflows and prompts.

```python
from ai_rpa_system import WorkflowExecutor

executor = WorkflowExecutor(workflow_manager=None)
```

#### Methods

##### `execute_workflow(workflow, variables=None, take_screenshots=False, validate=False, extra_warnings=None, safe=True, allow_unsafe=False, policy=None, audit_log=None)`

Execute a complete workflow.

**Parameters:**
- `workflow` (Workflow): Workflow object to execute
- `variables` (dict, optional): Variables for substitution
- `take_screenshots` (bool): Whether to capture screenshots
- `validate` (bool): Validate first and return a failed result (no steps run) on
  any issue
- `extra_warnings` (List[str], optional): Warnings to prepend to the result
- `safe` (bool): Run the security scan before executing and refuse workflows
  with CRITICAL findings (default `True`)
- `allow_unsafe` (bool): Skip the scan entirely and run even with CRITICAL
  findings (default `False`)
- `policy` (SafetyPolicy, optional): Policy controlling the scan; module
  `DEFAULT_POLICY` when `None`
- `audit_log` (str, optional): Path to append one per-step audit JSON line to
  (raw text is never written; sensitive steps record `[REDACTED]`)

**Returns:** `ExecutionResult`

**Example:**
```python
result = executor.execute_workflow(
    workflow,
    variables={"username": "user@example.com"},
    take_screenshots=True
)
```

##### `execute_prompt(prompt, variables=None, save_workflow=False)`

Execute a natural language prompt directly.

**Parameters:**
- `prompt` (str): Natural language description
- `variables` (dict, optional): Variables for substitution
- `save_workflow` (bool): Whether to save generated workflow

**Returns:** `ExecutionResult`

**Example:**
```python
result = executor.execute_prompt(
    "Open Chrome and navigate to example.com",
    save_workflow=True
)
```

##### `execute_workflow_by_name(workflow_name, variables=None, take_screenshots=False)`

Load and execute a saved workflow by name.

**Parameters:**
- `workflow_name` (str): Name of the workflow
- `variables` (dict, optional): Variables for substitution
- `take_screenshots` (bool): Whether to capture screenshots

**Returns:** `ExecutionResult`

**Example:**
```python
result = executor.execute_workflow_by_name(
    "login_workflow",
    variables={"username": "user", "password": "pass"}
)
```

---

### WorkflowManager

Manages workflow storage and retrieval.

```python
from ai_rpa_system import WorkflowManager

manager = WorkflowManager(storage_dir="workflows")
```

#### Methods

##### `save_workflow(workflow)`

Save a workflow to disk.

**Parameters:**
- `workflow` (Workflow): Workflow to save

**Returns:** `str` - Path to saved file

**Example:**
```python
path = manager.save_workflow(workflow)
```

##### `load_workflow(workflow_name)`

Load a workflow from disk.

**Parameters:**
- `workflow_name` (str): Name of the workflow

**Returns:** `Workflow` or `None`

**Example:**
```python
workflow = manager.load_workflow("my_workflow")
```

##### `list_workflows()`

List all available workflows.

**Returns:** `List[Dict]` - List of workflow metadata

**Example:**
```python
workflows = manager.list_workflows()
for wf in workflows:
    print(f"{wf['name']}: {wf['description']}")
```

##### `delete_workflow(workflow_name)`

Delete a workflow from disk.

**Parameters:**
- `workflow_name` (str): Name of the workflow

**Returns:** `bool` - Success status

##### `export_workflow_for_llm(workflow_name)`

Export workflow in LLM-friendly format.

**Parameters:**
- `workflow_name` (str): Name of the workflow

**Returns:** `str` - Formatted text representation

---

### WorkflowRecorder

Records user actions into workflows.

```python
from ai_rpa_system import WorkflowRecorder

recorder = WorkflowRecorder()
```

#### Methods

##### `start_recording(workflow_name, description="")`

Start recording desktop actions.

**Parameters:**
- `workflow_name` (str): Name for the workflow
- `description` (str, optional): Description

**Example:**
```python
recorder.start_recording("my_workflow", "Login automation")
# Perform actions...
```

##### `stop_recording()`

Stop recording and return the workflow.

**Returns:** `Workflow`

**Example:**
```python
workflow = recorder.stop_recording()
```

---

### AutomationEngine

Low-level automation engine for desktop interactions.

```python
from ai_rpa_system import AutomationEngine

engine = AutomationEngine()
```

#### Methods

##### `click(x, y, button="left", clicks=1)`

Click at specified coordinates.

**Parameters:**
- `x` (int): X coordinate
- `y` (int): Y coordinate
- `button` (str): Mouse button ("left", "right", "middle")
- `clicks` (int): Number of clicks

**Returns:** `bool`

##### `type_text(text, interval=0.05)`

Type text with specified interval.

**Parameters:**
- `text` (str): Text to type
- `interval` (float): Seconds between keystrokes

**Returns:** `bool`

##### `press_key(key)`

Press a single key.

**Parameters:**
- `key` (str): Key name (e.g., "enter", "tab", "escape")

**Returns:** `bool`

##### `hotkey(*keys)`

Press a combination of keys.

**Parameters:**
- `*keys` (str): Keys to press together

**Returns:** `bool`

**Example:**
```python
engine.hotkey("ctrl", "c")  # Copy
engine.hotkey("ctrl", "v")  # Paste
```

##### `move_mouse(x, y, duration=0.5)`

Move mouse to coordinates.

**Parameters:**
- `x` (int): X coordinate
- `y` (int): Y coordinate
- `duration` (float): Movement duration

**Returns:** `bool`

##### `scroll(clicks, x=None, y=None)`

Scroll the mouse wheel.

**Parameters:**
- `clicks` (int): Number of clicks (positive=up, negative=down)
- `x` (int, optional): X coordinate
- `y` (int, optional): Y coordinate

**Returns:** `bool`

##### `screenshot(region=None, save_path=None)`

Take a screenshot.

**Parameters:**
- `region` (tuple, optional): (x, y, width, height)
- `save_path` (str, optional): Path to save

**Returns:** `str` - Path to screenshot

##### `find_image_on_screen(image_path, confidence=0.8)`

Find an image on screen.

**Parameters:**
- `image_path` (str): Path to image
- `confidence` (float): Confidence threshold (0.0-1.0)

**Returns:** `tuple` - (x, y) coordinates or None

##### `wait(seconds)`

Wait for specified duration.

**Parameters:**
- `seconds` (float): Seconds to wait

**Returns:** `bool`

##### `get_mouse_position()`

Get current mouse position.

**Returns:** `tuple` - (x, y)

##### `get_screen_size()`

Get screen dimensions.

**Returns:** `tuple` - (width, height)

---

### PromptParser

Parses natural language prompts into structured actions.

```python
from ai_rpa_system import PromptParser

parser = PromptParser()
```

#### Methods

##### `parse(prompt)`

Parse a natural language prompt.

**Parameters:**
- `prompt` (str): Natural language description

**Returns:** `PromptAction`

**Example:**
```python
action = parser.parse("Click on the login button")
print(f"Intent: {action.intent}")
print(f"Confidence: {action.confidence}")
```

##### `parse_multi_step(prompt)`

Parse a multi-step prompt.

**Parameters:**
- `prompt` (str): Multi-step description

**Returns:** `List[PromptAction]`

**Example:**
```python
actions = parser.parse_multi_step(
    "First open Chrome, then navigate to example.com"
)
```

##### `prompt_to_workflow_json(prompt, workflow_name="generated_workflow")`

Convert prompt to workflow JSON.

**Parameters:**
- `prompt` (str): Natural language prompt
- `workflow_name` (str): Name for workflow

**Returns:** `str` - JSON string

---

## Data Models

### Workflow

Represents a complete automation workflow.

```python
from ai_rpa_system import Workflow, ActionStep

workflow = Workflow(
    name="my_workflow",
    description="What this workflow does",
    steps=[...],
    variables={},
    retry_on_failure=True,
    max_retries=3,
    tags=["tag1", "tag2"]
)
```

**Attributes:**
- `name` (str): Unique identifier
- `description` (str): What the workflow accomplishes
- `steps` (List[ActionStep]): Ordered list of actions
- `variables` (dict): Variable substitutions
- `created_at` (datetime): Creation timestamp
- `updated_at` (datetime): Last update timestamp
- `author` (str, optional): Author name
- `tags` (List[str]): Tags for categorization
- `retry_on_failure` (bool): Whether to retry failed steps
- `max_retries` (int): Maximum retry attempts

---

### ActionStep

Represents a single automation action.

```python
from ai_rpa_system import ActionStep

step = ActionStep(
    action="click",
    description="Click the login button",
    coordinates=[500, 300],
    wait_before=0.5,
    wait_after=1.0
)
```

**Attributes:**
- `action` (str): Action type (click, type, press_key, etc.)
- `description` (str): Human-readable description
- `target` (str, optional): Target element description
- `coordinates` (List[int], optional): [x, y] coordinates
- `text` (str, optional): Text to type
- `key` (str, optional): Key to press
- `keys` (List[str], optional): Keys for hotkey
- `wait_before` (float): Seconds to wait before
- `wait_after` (float): Seconds to wait after
- `image_path` (str, optional): Path to image for matching
- `confidence` (float): Image matching confidence
- `timestamp` (datetime, optional): When recorded
- `notes` (str, optional): Additional notes
- `end_coordinates` (List[int], optional): [x, y] end coordinates for a `drag`
- `sensitive` (bool): Redact this step's text in logs/audit output (default `False`)
- `repeat` (int): Execute this step N times; must be `>= 1` (default `1`)
- `optional` (bool): If the step fails, record a warning instead of failing the
  workflow (and skip retries) (default `False`)
- `timeout` (float, optional): For `wait_for_element`, seconds to poll before
  giving up (defaults to `10.0` when `None`)
- `poll_interval` (float, optional): For `wait_for_element`, seconds between
  polls (defaults to `0.5` when `None`)

**Action Types:**
- `click`: Click at coordinates or image
- `double_click`: Double-click at coordinates
- `right_click`: Right-click at coordinates
- `type`: Type text
- `press_key`: Press a single key
- `hotkey`: Press key combination
- `move_mouse`: Move mouse to position
- `scroll`: Scroll mouse wheel
- `drag`: Drag from one point to another
- `wait`: Wait for duration
- `screenshot`: Take screenshot
- `find_element`: Find element by image
- `open_application`: Open an application
- `close_application`: Close an application
- `wait_for_element`: Poll the screen for `image_path` until it appears or
  `timeout` elapses

#### `wait_for_element`

Polls the screen for `image_path` every `poll_interval` seconds until the image
is found or `timeout` seconds have elapsed. Requires `image_path`. On success
the step result includes the matched `location` as `[x, y]`; on timeout the step
fails. Useful for waiting on asynchronously-loaded UI instead of a fixed `wait`.

```python
from ai_rpa_system import ActionStep

step = ActionStep(
    action="wait_for_element",
    description="Wait for the dashboard to load",
    image_path="dashboard_logo.png",
    timeout=30.0,       # default 10.0 when None
    poll_interval=0.5,  # default 0.5 when None
    confidence=0.85,
)
```

---

### ExecutionResult

Result of workflow execution.

```python
result = executor.execute_workflow(workflow)

print(result.success)  # bool
print(result.steps_completed)  # int
print(result.total_steps)  # int
print(result.execution_time)  # float
print(result.errors)  # List[str]
print(result.warnings)  # List[str]
print(result.screenshots)  # List[str]
```

**Attributes:**
- `workflow_name` (str): Name of executed workflow
- `success` (bool): Overall success status
- `steps_completed` (int): Number of completed steps
- `total_steps` (int): Total number of steps
- `execution_time` (float): Total execution time in seconds
- `errors` (List[str]): List of errors
- `warnings` (List[str]): List of warnings
- `step_results` (List[dict]): Detailed step results
- `screenshots` (List[str]): Paths to screenshots
- `timestamp` (datetime): Execution timestamp

**Methods:**
- `to_llm_summary()`: Generate human-readable summary

---

### PromptAction

Parsed natural language prompt.

```python
action = parser.parse("Open Chrome")

print(action.intent)  # str
print(action.entities)  # dict
print(action.confidence)  # float
print(action.suggested_steps)  # List[ActionStep]
```

**Attributes:**
- `intent` (str): Main intent of the prompt
- `entities` (dict): Extracted entities
- `confidence` (float): Parsing confidence (0.0-1.0)
- `suggested_steps` (List[ActionStep]): Suggested actions

---

## Security

The package exports a static, headless-safe security scanner. See the top-level
[SECURITY.md](../../SECURITY.md) for the full threat model and blocked patterns.

### scan_workflow

```python
from ai_rpa_system import scan_workflow, SafetyPolicy

findings = scan_workflow(workflow, policy=None)
```

Statically analyse a `Workflow` and return a list of `SecurityFinding`s. The
function is pure-Python (no GUI imports), performs no I/O, and never raises for
benign workflows.

**Parameters:**
- `workflow` (Workflow): Workflow to scan
- `policy` (SafetyPolicy, optional): Thresholds/blocklists; the module
  `DEFAULT_POLICY` is used when `None`

**Returns:** `List[SecurityFinding]` — may contain `critical`, `major`, and
`minor` findings.

`WorkflowExecutor.execute_workflow` calls this automatically when `safe=True`
(the default) and refuses to execute any workflow with a CRITICAL finding unless
`allow_unsafe=True`.

### SecurityFinding

A single issue discovered while scanning a workflow.

**Attributes:**
- `severity` (str): One of `'critical'`, `'major'`, `'minor'`
- `category` (str): Finding category (e.g. `destructive_command`,
  `shell_launch`, `workflow_too_long`, `excessive_wait`,
  `suspicious_coordinates`, `oversized_text`, `risky_hotkey`, `style`)
- `step_index` (int): 1-based step index, or `0` for workflow-level findings
- `message` (str): Human-readable explanation

`str(finding)` renders as `[SEVERITY] category (step N): message`.

### SafetyPolicy

Thresholds and blocklists that drive `scan_workflow`.

```python
from ai_rpa_system import SafetyPolicy

policy = SafetyPolicy(max_steps=500, max_wait_seconds=600)
```

**Attributes (defaults):**
- `mode` (str): `"standard"`
- `max_steps` (int): `200` — workflows longer than this are CRITICAL
- `max_wait_seconds` (float): `300` — any wait/timeout/poll above this is CRITICAL
- `max_text_length` (int): `5000` — longer `text` is a MAJOR `oversized_text`
- `blocked_app_substrings` (tuple): shell/script hosts whose launch is CRITICAL
- `critical_command_patterns` (tuple): destructive command regexes (CRITICAL)
- `risky_hotkey_tokens` (tuple): `("del", "f4")` — combined with `alt` is MAJOR

---

## Exceptions

All custom errors derive from `RPAError`, so callers can catch the whole family
with a single `except RPAError`.

```python
from ai_rpa_system import (
    RPAError, SafetyError, WorkflowValidationError, ExecutionError,
)
```

- `RPAError` — base class for all errors raised by the system.
- `SafetyError` — raised when a workflow is blocked by the safety policy.
- `WorkflowValidationError` — raised when a workflow fails structural or
  semantic validation.
- `ExecutionError` — raised when a workflow step fails during execution.

---

## Usage Patterns

### Pattern 1: Simple Execution

```python
from ai_rpa_system import WorkflowExecutor

executor = WorkflowExecutor()
result = executor.execute_prompt("Open Chrome and navigate to example.com")
print(result.to_llm_summary())
```

### Pattern 2: Workflow Creation

```python
from ai_rpa_system import Workflow, ActionStep, WorkflowExecutor

workflow = Workflow(
    name="login",
    description="Login to application",
    steps=[
        ActionStep(action="click", coordinates=[400, 200]),
        ActionStep(action="type", text="{{username}}"),
        ActionStep(action="press_key", key="tab"),
        ActionStep(action="type", text="{{password}}"),
        ActionStep(action="press_key", key="enter")
    ],
    variables={"username": "user", "password": "pass"}
)

executor = WorkflowExecutor()
result = executor.execute_workflow(workflow)
```

### Pattern 3: Recording

```python
from ai_rpa_system import WorkflowRecorder, WorkflowManager

recorder = WorkflowRecorder()
manager = WorkflowManager()

recorder.start_recording("my_workflow")
# Perform actions...
workflow = recorder.stop_recording()
manager.save_workflow(workflow)
```

### Pattern 4: LLM Integration

```python
import json
from ai_rpa_system import Workflow, WorkflowExecutor

# LLM generates this JSON
llm_json = '''
{
  "name": "workflow",
  "description": "Description",
  "steps": [...]
}
'''

workflow = Workflow(**json.loads(llm_json))
executor = WorkflowExecutor()
result = executor.execute_workflow(workflow)
```

---

## Error Handling

All methods return appropriate error indicators:

```python
try:
    result = executor.execute_workflow(workflow)
    if not result.success:
        print("Errors:", result.errors)
except Exception as e:
    print(f"Exception: {e}")
```

---

## Best Practices

1. **Always validate workflows** before execution
2. **Use variables** for reusable workflows
3. **Add wait times** for UI elements to load
4. **Enable screenshots** for debugging
5. **Use retry logic** for unreliable actions
6. **Test incrementally** when building workflows
7. **Document workflows** with clear descriptions
8. **Handle errors** gracefully in production

---

## See Also

- [User Guide](USER_GUIDE.md)
- [LLM Integration Guide](LLM_INTEGRATION.md)
- [Example Workflows](../examples/)
