# AI-Powered RPA System - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Core Concepts](#core-concepts)
5. [Usage Examples](#usage-examples)
6. [LLM Integration](#llm-integration)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)

## Introduction

The AI-Powered RPA System is a sophisticated automation framework that allows you to automate desktop activities using natural language prompts. It's designed to be:

- **LLM-Friendly**: All workflows are structured in JSON format that LLMs can easily parse and generate
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Flexible**: Record workflows manually or generate them from prompts
- **Repeatable**: Save workflows and replay them with different variables

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Install Dependencies

```bash
cd ai_rpa_system
pip install -r requirements.txt
```

### Platform-Specific Setup

**Windows:**
- No additional setup required

**macOS:**
- Grant accessibility permissions to Terminal/Python in System Preferences > Security & Privacy > Privacy > Accessibility

**Linux:**
- Install additional dependencies:
  ```bash
  sudo apt-get install python3-tk python3-dev
  ```

## Quick Start

### 1. Execute a Simple Prompt

```python
from ai_rpa_system import WorkflowExecutor

executor = WorkflowExecutor()

# Execute a natural language prompt
result = executor.execute_prompt("Open Chrome and navigate to https://example.com")

print(result.to_llm_summary())
```

### 2. Record a Workflow

```python
from ai_rpa_system import WorkflowRecorder, WorkflowManager

recorder = WorkflowRecorder()
manager = WorkflowManager()

# Start recording
recorder.start_recording("my_workflow", "Description of what this workflow does")

# Perform your desktop actions...
# (clicks, typing, etc.)

# Stop recording
workflow = recorder.stop_recording()

# Save the workflow
manager.save_workflow(workflow)
```

### 3. Execute a Saved Workflow

```python
from ai_rpa_system import WorkflowExecutor

executor = WorkflowExecutor()

# Execute with custom variables
result = executor.execute_workflow_by_name(
    "my_workflow",
    variables={
        "username": "john@example.com",
        "password": "secure_password"
    }
)

print(f"Success: {result.success}")
print(f"Steps completed: {result.steps_completed}/{result.total_steps}")
```

## Core Concepts

### Workflows

A workflow is a sequence of automation steps. Each workflow has:
- **Name**: Unique identifier
- **Description**: What the workflow accomplishes
- **Steps**: Ordered list of actions
- **Variables**: Placeholders for dynamic values

### Action Steps

Each step in a workflow represents a single action:

| Action | Description | Parameters |
|--------|-------------|------------|
| `click` | Click at coordinates or image | coordinates, image_path |
| `double_click` | Double-click at coordinates | coordinates |
| `right_click` | Right-click at coordinates | coordinates |
| `type` | Type text | text |
| `press_key` | Press a single key | key |
| `hotkey` | Press key combination | keys |
| `move_mouse` | Move mouse to position | coordinates |
| `scroll` | Scroll mouse wheel | notes (amount) |
| `wait` | Wait for duration | wait_after |
| `screenshot` | Take screenshot | notes (path) |

### Variables

Use `{{variable_name}}` syntax in text fields for dynamic substitution:

```python
workflow = Workflow(
    name="login",
    steps=[
        ActionStep(
            action="type",
            text="{{username}}"
        )
    ],
    variables={
        "username": "default@example.com"
    }
)

# Execute with different values
executor.execute_workflow(workflow, variables={"username": "custom@example.com"})
```

## Usage Examples

### Example 1: Browser Automation

```python
from ai_rpa_system import WorkflowExecutor

executor = WorkflowExecutor()

# Multi-step prompt
prompt = """
Open Chrome, then navigate to https://github.com, 
then click on the search box, then type 'AI automation'
"""

result = executor.execute_prompt(prompt, save_workflow=True)
```

### Example 2: Form Filling

```python
from ai_rpa_system import Workflow, ActionStep, WorkflowExecutor

workflow = Workflow(
    name="contact_form",
    description="Fill out contact form",
    steps=[
        ActionStep(action="click", coordinates=[400, 200], description="Click name field"),
        ActionStep(action="type", text="{{name}}", description="Enter name"),
        ActionStep(action="press_key", key="tab", description="Next field"),
        ActionStep(action="type", text="{{email}}", description="Enter email"),
        ActionStep(action="press_key", key="tab", description="Next field"),
        ActionStep(action="type", text="{{message}}", description="Enter message"),
        ActionStep(action="click", coordinates=[500, 400], description="Submit")
    ]
)

executor = WorkflowExecutor()
result = executor.execute_workflow(workflow, variables={
    "name": "John Doe",
    "email": "john@example.com",
    "message": "Hello from RPA!"
})
```

### Example 3: File Management

```python
prompt = """
Open file explorer, then navigate to C:\\Downloads, 
then select all files, then copy them
"""

executor = WorkflowExecutor()
result = executor.execute_prompt(prompt)
```

### Example 4: Data Extraction

```python
from ai_rpa_system import WorkflowExecutor

executor = WorkflowExecutor()

# Execute with screenshots for verification
result = executor.execute_workflow_by_name(
    "data_extraction",
    take_screenshots=True
)

# Review screenshots
for screenshot in result.screenshots:
    print(f"Screenshot saved: {screenshot}")
```

## LLM Integration

The system is designed to work seamlessly with LLMs. Here's how:

### 1. LLM-Friendly Workflow Format

Workflows are stored in structured JSON that LLMs can easily parse:

```json
{
  "name": "example_workflow",
  "description": "What this workflow does",
  "steps": [
    {
      "action": "click",
      "description": "Human-readable description",
      "coordinates": [100, 200],
      "wait_before": 0.5,
      "wait_after": 1.0
    }
  ],
  "variables": {
    "key": "value"
  }
}
```

### 2. Generate Workflows from LLM Output

```python
from ai_rpa_system import PromptParser

parser = PromptParser()

# LLM generates this prompt
llm_prompt = "Open notepad, type 'Hello World', then save the file"

# Convert to workflow JSON
workflow_json = parser.prompt_to_workflow_json(llm_prompt, "notepad_hello")

# Execute the workflow
import json
from ai_rpa_system import Workflow, WorkflowExecutor

workflow_data = json.loads(workflow_json)
workflow = Workflow(**workflow_data)

executor = WorkflowExecutor()
result = executor.execute_workflow(workflow)
```

### 3. LLM Feedback Loop

```python
from ai_rpa_system import WorkflowExecutor

executor = WorkflowExecutor()

# Execute workflow
result = executor.execute_workflow_by_name("my_workflow")

# Get LLM-friendly summary
summary = result.to_llm_summary()

# Send to LLM for analysis
# The LLM can then suggest improvements or modifications
print(summary)
```

### 4. Export Workflows for LLM Analysis

```python
from ai_rpa_system import WorkflowManager

manager = WorkflowManager()

# Export in detailed format
llm_format = manager.export_workflow_for_llm("my_workflow")

# Send to LLM for review, optimization, or modification
print(llm_format)
```

## Advanced Features

### Image-Based Element Detection

Instead of coordinates, use images to find elements:

```python
ActionStep(
    action="click",
    description="Click the login button",
    image_path="images/login_button.png",
    confidence=0.8
)
```

### Retry Logic

Workflows automatically retry failed steps:

```python
workflow = Workflow(
    name="resilient_workflow",
    retry_on_failure=True,
    max_retries=3,
    steps=[...]
)
```

### Screenshot Capture

Take screenshots during execution for debugging:

```python
result = executor.execute_workflow(
    workflow,
    take_screenshots=True
)

# Screenshots are saved in the screenshots/ directory
```

### Multi-Step Prompts

Parse complex multi-step instructions:

```python
prompt = """
First, open Chrome.
Then, navigate to example.com.
Next, click on the login button.
After that, enter the username.
Finally, click submit.
"""

executor.execute_prompt(prompt)
```

### Workflow Chaining

Execute multiple workflows in sequence:

```python
workflows = ["setup", "login", "process_data", "logout"]

for workflow_name in workflows:
    result = executor.execute_workflow_by_name(workflow_name)
    if not result.success:
        print(f"Failed at: {workflow_name}")
        break
```

## Troubleshooting

### Common Issues

**1. PyAutoGUI Failsafe Triggered**
- **Problem**: Mouse moved to screen corner, aborting execution
- **Solution**: Disable failsafe or avoid moving mouse to corners
  ```python
  import pyautogui
  pyautogui.FAILSAFE = False  # Use with caution
  ```

**2. Element Not Found**
- **Problem**: Image-based detection fails
- **Solution**: Lower confidence threshold or update image
  ```python
  ActionStep(
      action="click",
      image_path="button.png",
      confidence=0.7  # Lower threshold
  )
  ```

**3. Timing Issues**
- **Problem**: Actions execute too fast
- **Solution**: Increase wait times
  ```python
  ActionStep(
      action="click",
      coordinates=[100, 200],
      wait_before=1.0,  # Wait longer
      wait_after=2.0
  )
  ```

**4. Permission Errors (macOS)**
- **Problem**: Cannot control desktop
- **Solution**: Grant accessibility permissions in System Preferences

**5. Coordinates Don't Match**
- **Problem**: Different screen resolution
- **Solution**: Record workflows on the target machine or use image-based detection

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing Workflows

Test workflows step-by-step:

```python
from ai_rpa_system import AutomationEngine

engine = AutomationEngine()

# Test individual actions
engine.click(100, 200)
engine.type_text("test")
engine.press_key("enter")
```

## Best Practices

1. **Use Descriptive Names**: Name workflows and steps clearly
2. **Add Wait Times**: Allow time for UI elements to load
3. **Use Variables**: Make workflows reusable with variables
4. **Test Incrementally**: Test each step before recording full workflow
5. **Take Screenshots**: Enable screenshots for debugging
6. **Handle Errors**: Use retry logic for unreliable actions
7. **Document Workflows**: Add clear descriptions to all steps
8. **Version Control**: Save workflows to version control
9. **Use Image Detection**: Prefer image-based detection over coordinates when possible
10. **LLM Integration**: Structure workflows for easy LLM parsing and generation

## Next Steps

- Explore the [API Reference](API_REFERENCE.md)
- Check out [Example Workflows](../examples/example_workflows.py)
- Learn about [LLM Integration Patterns](LLM_INTEGRATION.md)
- Contribute to the project on GitHub
