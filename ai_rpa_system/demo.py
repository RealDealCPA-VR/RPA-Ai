"""
Interactive demo interface for AI-Powered RPA System.
Provides a command-line interface to test all features.
"""

import sys
import json
from pathlib import Path

# Make the package importable when running this file directly as a script
# (adds the project root, i.e. the parent of the ai_rpa_system package).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_rpa_system.models import Workflow, ActionStep
from ai_rpa_system.automation_engine import AutomationEngine
from ai_rpa_system.prompt_parser import PromptParser
from ai_rpa_system.workflow_manager import WorkflowRecorder, WorkflowManager
from ai_rpa_system.executor import WorkflowExecutor


class RPADemo:
    """
    Interactive demo interface for the RPA system.
    """
    
    def __init__(self):
        self.engine = AutomationEngine()
        self.parser = PromptParser()
        self.recorder = WorkflowRecorder()
        self.manager = WorkflowManager()
        self.executor = WorkflowExecutor(self.manager)
        
        print("=" * 70)
        print("AI-Powered RPA System - Interactive Demo")
        print("=" * 70)
        print(f"Platform: {self.engine.platform}")
        print(f"Screen: {self.engine.screen_width}x{self.engine.screen_height}")
        print("=" * 70)
    
    def show_menu(self):
        """Display main menu."""
        print("\n" + "=" * 70)
        print("MAIN MENU")
        print("=" * 70)
        print("1. Execute Natural Language Prompt")
        print("2. Record New Workflow")
        print("3. Execute Saved Workflow")
        print("4. List All Workflows")
        print("5. View Workflow Details")
        print("6. Parse Prompt (Preview)")
        print("7. Test Individual Actions")
        print("8. Create Example Workflows")
        print("9. Export Workflow for LLM")
        print("0. Exit")
        print("=" * 70)
    
    def run(self):
        """Run the interactive demo."""
        while True:
            self.show_menu()
            choice = input("\nEnter your choice (0-9): ").strip()
            
            if choice == "1":
                self.execute_prompt()
            elif choice == "2":
                self.record_workflow()
            elif choice == "3":
                self.execute_workflow()
            elif choice == "4":
                self.list_workflows()
            elif choice == "5":
                self.view_workflow()
            elif choice == "6":
                self.parse_prompt()
            elif choice == "7":
                self.test_actions()
            elif choice == "8":
                self.create_examples()
            elif choice == "9":
                self.export_workflow()
            elif choice == "0":
                print("\nThank you for using AI-Powered RPA System!")
                break
            else:
                print("\n❌ Invalid choice. Please try again.")
    
    def execute_prompt(self):
        """Execute a natural language prompt."""
        print("\n" + "-" * 70)
        print("EXECUTE NATURAL LANGUAGE PROMPT")
        print("-" * 70)
        print("Enter a natural language description of what you want to automate.")
        print("Examples:")
        print("  - Open Chrome and navigate to https://example.com")
        print("  - Click at coordinates 500, 300 then type 'Hello World'")
        print("  - Press Ctrl+C then wait 2 seconds")
        print("-" * 70)
        
        prompt = input("\nEnter your prompt (or 'back' to return): ").strip()
        if prompt.lower() == 'back':
            return
        
        save = input("Save this workflow? (y/n): ").strip().lower() == 'y'
        screenshots = input("Take screenshots during execution? (y/n): ").strip().lower() == 'y'
        
        print("\n⏳ Executing prompt...")
        print(f"Prompt: {prompt}")
        
        try:
            result = self.executor.execute_prompt(prompt, save_workflow=save)
            
            print("\n" + "=" * 70)
            print("EXECUTION RESULT")
            print("=" * 70)
            print(result.to_llm_summary())
            
            if result.screenshots:
                print(f"\n📸 Screenshots saved:")
                for screenshot in result.screenshots:
                    print(f"  - {screenshot}")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        input("\nPress Enter to continue...")
    
    def record_workflow(self):
        """Record a new workflow."""
        print("\n" + "-" * 70)
        print("RECORD NEW WORKFLOW")
        print("-" * 70)
        print("⚠️  WARNING: Recording will capture all mouse and keyboard actions.")
        print("Make sure you're ready before starting.")
        print("-" * 70)
        
        name = input("\nWorkflow name: ").strip()
        if not name:
            print("❌ Name cannot be empty.")
            return
        
        description = input("Description: ").strip()
        
        input("\n✓ Press Enter to START recording (perform your actions after this)...")
        
        self.recorder.start_recording(name, description)
        
        input("\n🔴 RECORDING... Press Enter to STOP recording...")
        
        workflow = self.recorder.stop_recording()
        
        if workflow:
            self.manager.save_workflow(workflow)
            print(f"\n✓ Workflow '{name}' recorded and saved!")
            print(f"  Steps captured: {len(workflow.steps)}")
        else:
            print("\n❌ Recording failed.")
        
        input("\nPress Enter to continue...")
    
    def execute_workflow(self):
        """Execute a saved workflow."""
        print("\n" + "-" * 70)
        print("EXECUTE SAVED WORKFLOW")
        print("-" * 70)
        
        workflows = self.manager.list_workflows()
        if not workflows:
            print("No workflows found. Create one first!")
            input("\nPress Enter to continue...")
            return
        
        print("\nAvailable workflows:")
        for i, wf in enumerate(workflows, 1):
            print(f"{i}. {wf['name']} - {wf['description']}")
        
        choice = input("\nEnter workflow number (or name): ").strip()
        
        # Get workflow name
        if choice.isdigit() and 1 <= int(choice) <= len(workflows):
            workflow_name = workflows[int(choice) - 1]['name']
        else:
            workflow_name = choice
        
        # Get variables
        workflow = self.manager.load_workflow(workflow_name)
        if not workflow:
            print(f"❌ Workflow '{workflow_name}' not found.")
            input("\nPress Enter to continue...")
            return
        
        variables = {}
        if workflow.variables:
            print(f"\nWorkflow has {len(workflow.variables)} variables:")
            for key, default_value in workflow.variables.items():
                value = input(f"  {key} (default: {default_value}): ").strip()
                variables[key] = value if value else default_value
        
        screenshots = input("\nTake screenshots during execution? (y/n): ").strip().lower() == 'y'
        
        print("\n⏳ Executing workflow...")
        
        try:
            result = self.executor.execute_workflow_by_name(
                workflow_name,
                variables=variables,
                take_screenshots=screenshots
            )
            
            print("\n" + "=" * 70)
            print("EXECUTION RESULT")
            print("=" * 70)
            print(result.to_llm_summary())
            
            if result.screenshots:
                print(f"\n📸 Screenshots saved:")
                for screenshot in result.screenshots:
                    print(f"  - {screenshot}")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        input("\nPress Enter to continue...")
    
    def list_workflows(self):
        """List all available workflows."""
        print("\n" + "-" * 70)
        print("ALL WORKFLOWS")
        print("-" * 70)
        
        workflows = self.manager.list_workflows()
        
        if not workflows:
            print("No workflows found.")
        else:
            for i, wf in enumerate(workflows, 1):
                print(f"\n{i}. {wf['name']}")
                print(f"   Description: {wf['description']}")
                print(f"   Steps: {wf['steps']}")
                print(f"   Tags: {', '.join(wf['tags']) if wf['tags'] else 'None'}")
                print(f"   Created: {wf.get('created_at', 'Unknown')}")
        
        input("\nPress Enter to continue...")
    
    def view_workflow(self):
        """View detailed workflow information."""
        print("\n" + "-" * 70)
        print("VIEW WORKFLOW DETAILS")
        print("-" * 70)
        
        workflows = self.manager.list_workflows()
        if not workflows:
            print("No workflows found.")
            input("\nPress Enter to continue...")
            return
        
        print("\nAvailable workflows:")
        for i, wf in enumerate(workflows, 1):
            print(f"{i}. {wf['name']}")
        
        choice = input("\nEnter workflow number (or name): ").strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(workflows):
            workflow_name = workflows[int(choice) - 1]['name']
        else:
            workflow_name = choice
        
        workflow = self.manager.load_workflow(workflow_name)
        if not workflow:
            print(f"❌ Workflow '{workflow_name}' not found.")
            input("\nPress Enter to continue...")
            return
        
        print("\n" + "=" * 70)
        print(f"WORKFLOW: {workflow.name}")
        print("=" * 70)
        print(f"Description: {workflow.description}")
        print(f"Total Steps: {len(workflow.steps)}")
        
        if workflow.variables:
            print(f"\nVariables:")
            for key, value in workflow.variables.items():
                print(f"  - {key}: {value}")
        
        print(f"\nSteps:")
        for i, step in enumerate(workflow.steps, 1):
            print(f"\n{i}. {step.action.upper()}")
            print(f"   Description: {step.description}")
            if step.coordinates:
                print(f"   Coordinates: {step.coordinates}")
            if step.text:
                print(f"   Text: {step.text}")
            if step.key:
                print(f"   Key: {step.key}")
            if step.keys:
                print(f"   Keys: {step.keys}")
            print(f"   Wait before: {step.wait_before}s")
            print(f"   Wait after: {step.wait_after}s")
        
        input("\nPress Enter to continue...")
    
    def parse_prompt(self):
        """Parse a prompt and preview the generated actions."""
        print("\n" + "-" * 70)
        print("PARSE PROMPT (PREVIEW)")
        print("-" * 70)
        
        prompt = input("\nEnter prompt to parse: ").strip()
        if not prompt:
            return
        
        print("\n⏳ Parsing prompt...")
        
        try:
            if any(sep in prompt.lower() for sep in ["then", "and then", "next"]):
                actions = self.parser.parse_multi_step(prompt)
            else:
                actions = [self.parser.parse(prompt)]
            
            print("\n" + "=" * 70)
            print("PARSED ACTIONS")
            print("=" * 70)
            
            for i, action in enumerate(actions, 1):
                print(f"\nAction {i}:")
                print(f"  Intent: {action.intent}")
                print(f"  Confidence: {action.confidence:.2%}")
                print(f"  Entities: {action.entities}")
                print(f"  Suggested Steps: {len(action.suggested_steps)}")
                
                if action.suggested_steps:
                    print("\n  Steps:")
                    for j, step in enumerate(action.suggested_steps, 1):
                        print(f"    {j}. {step.action}: {step.description}")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        input("\nPress Enter to continue...")
    
    def test_actions(self):
        """Test individual automation actions."""
        print("\n" + "-" * 70)
        print("TEST INDIVIDUAL ACTIONS")
        print("-" * 70)
        print("1. Get mouse position")
        print("2. Click at coordinates")
        print("3. Type text")
        print("4. Press key")
        print("5. Take screenshot")
        print("6. Back to main menu")
        print("-" * 70)
        
        choice = input("\nEnter choice: ").strip()
        
        try:
            if choice == "1":
                pos = self.engine.get_mouse_position()
                print(f"\n✓ Current mouse position: {pos}")
            
            elif choice == "2":
                x = int(input("X coordinate: "))
                y = int(input("Y coordinate: "))
                print(f"\n⏳ Clicking at ({x}, {y})...")
                self.engine.click(x, y)
                print("✓ Click executed")
            
            elif choice == "3":
                text = input("Text to type: ")
                print(f"\n⏳ Typing: {text}")
                self.engine.type_text(text)
                print("✓ Text typed")
            
            elif choice == "4":
                key = input("Key to press: ")
                print(f"\n⏳ Pressing key: {key}")
                self.engine.press_key(key)
                print("✓ Key pressed")
            
            elif choice == "5":
                print("\n⏳ Taking screenshot...")
                path = self.engine.screenshot()
                print(f"✓ Screenshot saved: {path}")
            
            elif choice == "6":
                return
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        input("\nPress Enter to continue...")
    
    def create_examples(self):
        """Create example workflows."""
        print("\n" + "-" * 70)
        print("CREATE EXAMPLE WORKFLOWS")
        print("-" * 70)
        
        from ai_rpa_system.examples.example_workflows import (
            create_browser_navigation_workflow,
            create_form_filling_workflow,
            create_file_management_workflow,
            create_data_extraction_workflow,
            create_email_automation_workflow
        )
        
        workflows = [
            create_browser_navigation_workflow(),
            create_form_filling_workflow(),
            create_file_management_workflow(),
            create_data_extraction_workflow(),
            create_email_automation_workflow()
        ]
        
        print("\n⏳ Creating example workflows...")
        
        for workflow in workflows:
            self.manager.save_workflow(workflow)
            print(f"✓ Created: {workflow.name}")
        
        print(f"\n✓ All {len(workflows)} example workflows created!")
        
        input("\nPress Enter to continue...")
    
    def export_workflow(self):
        """Export workflow in LLM-friendly format."""
        print("\n" + "-" * 70)
        print("EXPORT WORKFLOW FOR LLM")
        print("-" * 70)
        
        workflows = self.manager.list_workflows()
        if not workflows:
            print("No workflows found.")
            input("\nPress Enter to continue...")
            return
        
        print("\nAvailable workflows:")
        for i, wf in enumerate(workflows, 1):
            print(f"{i}. {wf['name']}")
        
        choice = input("\nEnter workflow number (or name): ").strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(workflows):
            workflow_name = workflows[int(choice) - 1]['name']
        else:
            workflow_name = choice
        
        print("\n" + "=" * 70)
        print("LLM-FRIENDLY EXPORT")
        print("=" * 70)
        
        export = self.manager.export_workflow_for_llm(workflow_name)
        print(export)
        
        # Option to save to file
        save = input("\nSave to file? (y/n): ").strip().lower() == 'y'
        if save:
            filename = f"{workflow_name}_llm_export.txt"
            with open(filename, 'w') as f:
                f.write(export)
            print(f"✓ Exported to: {filename}")
        
        input("\nPress Enter to continue...")


def main():
    """Main entry point."""
    try:
        demo = RPADemo()
        demo.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
