# Quick Start Guide

Get started with AI-Powered RPA in 5 minutes!

## Installation

```bash
# Navigate to the project directory
cd ai_rpa_system

# Install dependencies
pip install -r requirements.txt
```

## 1. Run the Interactive Demo

The easiest way to explore the system:

```bash
python demo.py
```

This launches an interactive menu where you can:
- Execute natural language prompts
- Record workflows
- Execute saved workflows
- View workflow details
- Test individual actions

## 2. Execute Your First Prompt

Create a file `test_rpa.py`:

```python
from ai_rpa_system import WorkflowExecutor

# Create executor
executor = WorkflowExecutor()

# Execute a simple prompt
result = executor.execute_prompt("Wait 2 seconds then take a screenshot")

# View results
print(result.to_llm_summary())
```

Run it:
```bash
python test_rpa.py
```

## 3. Create a Simple Workflow

```python
from ai_rpa_system import Workflow, ActionStep, WorkflowExecutor

# Define workflow
workflow = Workflow(
    name="hello_world",
    description="Types Hello World",
    steps=[
        ActionStep(
            action="type",
            description="Type greeting",
            text="Hello World!",
            wait_after=1.0
        )
    ]
)

# Execute it
executor = WorkflowExecutor()
result = executor.execute_workflow(workflow)

print(f"Success: {result.success}")
print(f"Steps completed: {result.steps_completed}/{result.total_steps}")
```

## 4. Use Variables for Reusability

```python
from ai_rpa_system import Workflow, ActionStep, WorkflowExecutor

workflow = Workflow(
    name="personalized_greeting",
    description="Types a personalized message",
    steps=[
        ActionStep(
            action="type",
            text="Hello {{name}}! Welcome to {{app}}.",
            description="Type personalized greeting"
        )
    ],
    variables={
        "name": "User",
        "app": "RPA System"
    }
)

executor = WorkflowExecutor()

# Execute with custom variables
result = executor.execute_workflow(
    workflow,
    variables={
        "name": "Alice",
        "app": "AI Automation"
    }
)
```

## 5. Save and Load Workflows

```python
from ai_rpa_system import WorkflowManager

manager = WorkflowManager()

# Save workflow
manager.save_workflow(workflow)

# Load it later
loaded_workflow = manager.load_workflow("personalized_greeting")

# List all workflows
workflows = manager.list_workflows()
for wf in workflows:
    print(f"{wf['name']}: {wf['description']}")
```

## 6. Record Your Own Workflow

```python
from ai_rpa_system import WorkflowRecorder, WorkflowManager

recorder = WorkflowRecorder()
manager = WorkflowManager()

# Start recording
recorder.start_recording("my_workflow", "My custom automation")

# Perform your desktop actions here...
# (clicks, typing, etc.)

input("Press Enter when done...")

# Stop and save
workflow = recorder.stop_recording()
manager.save_workflow(workflow)

print(f"Recorded {len(workflow.steps)} steps!")
```

## 7. LLM Integration Example

```python
import json
from ai_rpa_system import Workflow, WorkflowExecutor

# Simulate LLM generating a workflow
llm_output = '''
{
  "name": "search_workflow",
  "description": "Search for something",
  "steps": [
    {
      "action": "type",
      "description": "Type search query",
      "text": "AI automation tools",
      "wait_after": 1.0
    },
    {
      "action": "press_key",
      "description": "Submit search",
      "key": "enter",
      "wait_after": 2.0
    }
  ]
}
'''

# Parse and execute
workflow = Workflow(**json.loads(llm_output))
executor = WorkflowExecutor()
result = executor.execute_workflow(workflow)

print(result.to_llm_summary())
```

## Common Use Cases

### Browser Automation
```python
prompt = "Open Chrome then navigate to https://github.com"
result = executor.execute_prompt(prompt)
```

### Form Filling
```python
workflow = Workflow(
    name="fill_form",
    steps=[
        ActionStep(action="click", coordinates=[400, 200]),
        ActionStep(action="type", text="{{name}}"),
        ActionStep(action="press_key", key="tab"),
        ActionStep(action="type", text="{{email}}"),
    ],
    variables={"name": "John", "email": "john@example.com"}
)
```

### Data Entry
```python
prompt = "Type 'Hello World' then press Enter then wait 1 second"
result = executor.execute_prompt(prompt)
```

### Screenshot Capture
```python
result = executor.execute_workflow(
    workflow,
    take_screenshots=True
)
# Screenshots saved in screenshots/ directory
```

## Next Steps

1. **Explore Examples**: Check out `examples/simple_usage.py` for more examples
2. **Read Documentation**: See `docs/USER_GUIDE.md` for comprehensive guide
3. **LLM Integration**: Read `docs/LLM_INTEGRATION.md` for advanced patterns
4. **API Reference**: Check `docs/API_REFERENCE.md` for complete API docs
5. **Create Workflows**: Use the demo to create and test your own workflows

## Tips

- **Start Simple**: Begin with basic actions before complex workflows
- **Use Wait Times**: Add appropriate wait times for UI elements to load
- **Test Incrementally**: Test each step before building full workflows
- **Use Variables**: Make workflows reusable with variable substitution
- **Enable Screenshots**: Use screenshots for debugging
- **Handle Errors**: Enable retry logic for unreliable actions

## Troubleshooting

**Mouse moves to corner and stops?**
- This is PyAutoGUI's failsafe feature. Move mouse away from corners.

**Actions too fast?**
- Increase `wait_before` and `wait_after` times in ActionSteps

**Can't find elements?**
- Use image-based detection instead of coordinates
- Lower confidence threshold for image matching

**Permission errors (macOS)?**
- Grant accessibility permissions in System Preferences

## Support

- Check the [User Guide](docs/USER_GUIDE.md) for detailed information
- Review [Example Workflows](examples/) for inspiration
- Read [API Reference](docs/API_REFERENCE.md) for technical details

Happy Automating! 🤖
