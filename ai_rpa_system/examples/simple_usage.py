"""
Simple usage examples for AI-Powered RPA System.
Quick start guide with practical examples.
"""

import sys
from pathlib import Path

# Make the package importable when running this file directly as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai_rpa_system.executor import WorkflowExecutor
from ai_rpa_system.workflow_manager import WorkflowManager
from ai_rpa_system.models import Workflow, ActionStep


def example_1_execute_prompt():
    """
    Example 1: Execute a simple natural language prompt.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Execute Natural Language Prompt")
    print("=" * 70)
    
    executor = WorkflowExecutor()
    
    # Simple prompt
    prompt = "Wait 2 seconds then take a screenshot"
    
    print(f"Executing: {prompt}")
    result = executor.execute_prompt(prompt)
    
    print(f"\nResult: {result.to_llm_summary()}")


def example_2_create_and_execute_workflow():
    """
    Example 2: Create a workflow programmatically and execute it.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Create and Execute Workflow")
    print("=" * 70)
    
    # Create a simple workflow
    workflow = Workflow(
        name="hello_world",
        description="Types 'Hello World' and takes a screenshot",
        steps=[
            ActionStep(
                action="type",
                description="Type greeting",
                text="Hello World!",
                wait_after=1.0
            ),
            ActionStep(
                action="screenshot",
                description="Capture result",
                notes="hello_world_screenshot.png"
            )
        ]
    )
    
    # Execute it
    executor = WorkflowExecutor()
    result = executor.execute_workflow(workflow)
    
    print(f"Result: {result.to_llm_summary()}")


def example_3_workflow_with_variables():
    """
    Example 3: Use variables in workflows for reusability.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Workflow with Variables")
    print("=" * 70)
    
    workflow = Workflow(
        name="personalized_greeting",
        description="Types a personalized greeting",
        steps=[
            ActionStep(
                action="type",
                description="Type greeting",
                text="Hello {{name}}! Welcome to {{app_name}}.",
                wait_after=0.5
            )
        ],
        variables={
            "name": "User",
            "app_name": "RPA System"
        }
    )
    
    executor = WorkflowExecutor()
    
    # Execute with default variables
    print("\nExecution 1 (default variables):")
    result1 = executor.execute_workflow(workflow)
    print(f"Result: {result1.to_llm_summary()}")
    
    # Execute with custom variables
    print("\nExecution 2 (custom variables):")
    result2 = executor.execute_workflow(
        workflow,
        variables={
            "name": "Alice",
            "app_name": "AI Automation"
        }
    )
    print(f"Result: {result2.to_llm_summary()}")


def example_4_save_and_load_workflow():
    """
    Example 4: Save workflow to disk and load it later.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Save and Load Workflow")
    print("=" * 70)
    
    manager = WorkflowManager()
    
    # Create workflow
    workflow = Workflow(
        name="test_workflow",
        description="A test workflow for demonstration",
        steps=[
            ActionStep(
                action="wait",
                description="Wait 1 second",
                wait_after=1.0
            )
        ],
        tags=["test", "demo"]
    )
    
    # Save it
    path = manager.save_workflow(workflow)
    print(f"Workflow saved to: {path}")
    
    # Load it back
    loaded_workflow = manager.load_workflow("test_workflow")
    print(f"\nLoaded workflow: {loaded_workflow.name}")
    print(f"Description: {loaded_workflow.description}")
    print(f"Steps: {len(loaded_workflow.steps)}")
    print(f"Tags: {loaded_workflow.tags}")


def example_5_multi_step_prompt():
    """
    Example 5: Execute a multi-step prompt.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Multi-Step Prompt")
    print("=" * 70)
    
    executor = WorkflowExecutor()
    
    # Multi-step prompt with separators
    prompt = """
    First, wait 1 second.
    Then, type 'Step 1 complete'.
    Next, wait 1 second.
    Finally, type 'All done!'.
    """
    
    print(f"Executing multi-step prompt...")
    result = executor.execute_prompt(prompt)
    
    print(f"\nResult: {result.to_llm_summary()}")


def example_6_error_handling():
    """
    Example 6: Demonstrate error handling and retry logic.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Error Handling and Retry")
    print("=" * 70)
    
    workflow = Workflow(
        name="resilient_workflow",
        description="Workflow with retry logic",
        retry_on_failure=True,
        max_retries=3,
        steps=[
            ActionStep(
                action="type",
                description="Type some text",
                text="Testing retry logic",
                wait_after=0.5
            )
        ]
    )
    
    executor = WorkflowExecutor()
    result = executor.execute_workflow(workflow)
    
    print(f"Result: {result.to_llm_summary()}")
    
    if result.errors:
        print("\nErrors encountered:")
        for error in result.errors:
            print(f"  - {error}")


def example_7_list_workflows():
    """
    Example 7: List all available workflows.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 7: List All Workflows")
    print("=" * 70)
    
    manager = WorkflowManager()
    workflows = manager.list_workflows()
    
    if workflows:
        print(f"\nFound {len(workflows)} workflow(s):\n")
        for i, wf in enumerate(workflows, 1):
            print(f"{i}. {wf['name']}")
            print(f"   Description: {wf['description']}")
            print(f"   Steps: {wf['steps']}")
            print(f"   Tags: {', '.join(wf['tags']) if wf['tags'] else 'None'}")
            print()
    else:
        print("\nNo workflows found.")


def example_8_llm_integration():
    """
    Example 8: Demonstrate LLM integration pattern.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 8: LLM Integration Pattern")
    print("=" * 70)
    
    from ai_rpa_system.prompt_parser import PromptParser
    import json
    
    parser = PromptParser()
    
    # Simulate LLM generating a prompt
    user_request = "Open notepad and type 'Hello from AI'"
    
    print(f"User request: {user_request}")
    
    # Convert to workflow JSON (LLM-friendly format)
    workflow_json = parser.prompt_to_workflow_json(user_request, "llm_generated")
    
    print("\nGenerated workflow JSON:")
    print(workflow_json)
    
    # Parse and execute
    workflow_data = json.loads(workflow_json)
    workflow = Workflow(**workflow_data)
    
    executor = WorkflowExecutor()
    result = executor.execute_workflow(workflow)
    
    print(f"\nExecution result: {result.to_llm_summary()}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("AI-POWERED RPA SYSTEM - SIMPLE USAGE EXAMPLES")
    print("=" * 70)
    
    examples = [
        ("Execute Natural Language Prompt", example_1_execute_prompt),
        ("Create and Execute Workflow", example_2_create_and_execute_workflow),
        ("Workflow with Variables", example_3_workflow_with_variables),
        ("Save and Load Workflow", example_4_save_and_load_workflow),
        ("Multi-Step Prompt", example_5_multi_step_prompt),
        ("Error Handling and Retry", example_6_error_handling),
        ("List All Workflows", example_7_list_workflows),
        ("LLM Integration Pattern", example_8_llm_integration),
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    print("0. Run all examples")
    
    choice = input("\nEnter example number (0-8): ").strip()
    
    if choice == "0":
        for name, func in examples:
            try:
                func()
                input("\nPress Enter to continue to next example...")
            except Exception as e:
                print(f"\n❌ Error in {name}: {e}")
                input("\nPress Enter to continue...")
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        try:
            examples[int(choice) - 1][1]()
        except Exception as e:
            print(f"\n❌ Error: {e}")
    else:
        print("Invalid choice.")


if __name__ == "__main__":
    main()
