"""
Example workflows demonstrating AI-powered RPA capabilities.
"""

import sys
from pathlib import Path

# Make the package importable when running this file directly as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai_rpa_system.models import Workflow, ActionStep


def create_browser_navigation_workflow() -> Workflow:
    """
    Example: Open browser and navigate to a website.
    """
    return Workflow(
        name="browser_navigation",
        description="Opens Chrome browser and navigates to a specified URL",
        steps=[
            ActionStep(
                action="hotkey",
                description="Open application launcher (Windows key)",
                keys=["win"],
                wait_after=1.0
            ),
            ActionStep(
                action="type",
                description="Type 'Chrome' to search for browser",
                text="Chrome",
                wait_after=0.5
            ),
            ActionStep(
                action="press_key",
                description="Press Enter to launch Chrome",
                key="enter",
                wait_after=3.0
            ),
            ActionStep(
                action="hotkey",
                description="Focus address bar",
                keys=["ctrl", "l"],
                wait_after=0.5
            ),
            ActionStep(
                action="type",
                description="Type URL",
                text="{{url}}",
                wait_after=0.5
            ),
            ActionStep(
                action="press_key",
                description="Navigate to URL",
                key="enter",
                wait_after=2.0
            )
        ],
        variables={
            "url": "https://www.example.com"
        },
        tags=["browser", "navigation", "web"]
    )


def create_form_filling_workflow() -> Workflow:
    """
    Example: Fill out a form with user data.
    """
    return Workflow(
        name="form_filling",
        description="Fills out a web form with provided user information",
        steps=[
            ActionStep(
                action="click",
                description="Click on first name field",
                target="First Name input",
                coordinates=[400, 200],
                wait_after=0.5
            ),
            ActionStep(
                action="type",
                description="Enter first name",
                text="{{first_name}}",
                wait_after=0.3
            ),
            ActionStep(
                action="press_key",
                description="Move to next field",
                key="tab",
                wait_after=0.3
            ),
            ActionStep(
                action="type",
                description="Enter last name",
                text="{{last_name}}",
                wait_after=0.3
            ),
            ActionStep(
                action="press_key",
                description="Move to email field",
                key="tab",
                wait_after=0.3
            ),
            ActionStep(
                action="type",
                description="Enter email",
                text="{{email}}",
                wait_after=0.3
            ),
            ActionStep(
                action="click",
                description="Click submit button",
                target="Submit button",
                coordinates=[500, 400],
                wait_after=1.0
            )
        ],
        variables={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com"
        },
        tags=["form", "data-entry", "web"]
    )


def create_file_management_workflow() -> Workflow:
    """
    Example: Organize files in a directory.
    """
    return Workflow(
        name="file_organization",
        description="Opens file explorer and organizes files by type",
        steps=[
            ActionStep(
                action="hotkey",
                description="Open file explorer",
                keys=["win", "e"],
                wait_after=1.5
            ),
            ActionStep(
                action="hotkey",
                description="Focus address bar",
                keys=["ctrl", "l"],
                wait_after=0.5
            ),
            ActionStep(
                action="type",
                description="Navigate to target directory",
                text="{{directory_path}}",
                wait_after=0.5
            ),
            ActionStep(
                action="press_key",
                description="Navigate to directory",
                key="enter",
                wait_after=1.0
            ),
            ActionStep(
                action="hotkey",
                description="Select all files",
                keys=["ctrl", "a"],
                wait_after=0.5
            ),
            ActionStep(
                action="right_click",
                description="Open context menu",
                coordinates=[500, 300],
                wait_after=0.5
            )
        ],
        variables={
            "directory_path": "C:\\Users\\Documents\\Downloads"
        },
        tags=["files", "organization", "system"]
    )


def create_data_extraction_workflow() -> Workflow:
    """
    Example: Extract data from a table and copy to clipboard.
    """
    return Workflow(
        name="data_extraction",
        description="Selects and copies data from a table",
        steps=[
            ActionStep(
                action="click",
                description="Click on first cell of table",
                target="Table cell (1,1)",
                coordinates=[300, 250],
                wait_after=0.3
            ),
            ActionStep(
                action="drag",
                description="Select table range",
                coordinates=[300, 250],
                end_coordinates=[600, 450],
                notes="Drag to [600, 450]",
                wait_after=0.5
            ),
            ActionStep(
                action="hotkey",
                description="Copy selected data",
                keys=["ctrl", "c"],
                wait_after=0.5
            ),
            ActionStep(
                action="hotkey",
                description="Open notepad",
                keys=["win"],
                wait_after=0.5
            ),
            ActionStep(
                action="type",
                description="Search for notepad",
                text="notepad",
                wait_after=0.3
            ),
            ActionStep(
                action="press_key",
                description="Open notepad",
                key="enter",
                wait_after=1.5
            ),
            ActionStep(
                action="hotkey",
                description="Paste data",
                keys=["ctrl", "v"],
                wait_after=0.5
            )
        ],
        tags=["data", "extraction", "clipboard"]
    )


def create_email_automation_workflow() -> Workflow:
    """
    Example: Compose and send an email.
    """
    return Workflow(
        name="email_automation",
        description="Composes and sends an email with provided content",
        steps=[
            ActionStep(
                action="hotkey",
                description="Open email client or browser",
                keys=["win"],
                wait_after=0.5
            ),
            ActionStep(
                action="type",
                description="Search for email application",
                text="{{email_app}}",
                wait_after=0.5
            ),
            ActionStep(
                action="press_key",
                description="Open email application",
                key="enter",
                wait_after=3.0
            ),
            ActionStep(
                action="hotkey",
                description="Compose new email",
                keys=["ctrl", "n"],
                wait_after=1.0
            ),
            ActionStep(
                action="type",
                description="Enter recipient email",
                text="{{recipient}}",
                wait_after=0.5
            ),
            ActionStep(
                action="press_key",
                description="Move to subject field",
                key="tab",
                wait_after=0.3
            ),
            ActionStep(
                action="type",
                description="Enter email subject",
                text="{{subject}}",
                wait_after=0.5
            ),
            ActionStep(
                action="press_key",
                description="Move to body field",
                key="tab",
                wait_after=0.3
            ),
            ActionStep(
                action="type",
                description="Enter email body",
                text="{{body}}",
                wait_after=0.5
            ),
            ActionStep(
                action="hotkey",
                description="Send email",
                keys=["ctrl", "enter"],
                wait_after=1.0
            )
        ],
        variables={
            "email_app": "Outlook",
            "recipient": "recipient@example.com",
            "subject": "Automated Email",
            "body": "This email was sent using AI-powered RPA automation."
        },
        tags=["email", "communication", "automation"]
    )


if __name__ == "__main__":
    # Create and save example workflows
    from ai_rpa_system.workflow_manager import WorkflowManager
    
    manager = WorkflowManager("example_workflows")
    
    workflows = [
        create_browser_navigation_workflow(),
        create_form_filling_workflow(),
        create_file_management_workflow(),
        create_data_extraction_workflow(),
        create_email_automation_workflow()
    ]
    
    print("Creating example workflows...\n")
    for workflow in workflows:
        manager.save_workflow(workflow)
        print(f"✓ Created: {workflow.name}")
        print(f"  Description: {workflow.description}")
        print(f"  Steps: {len(workflow.steps)}")
        print(f"  Tags: {', '.join(workflow.tags)}")
        print()
    
    print(f"\nAll example workflows saved to: {manager.storage_dir}")
