"""
Natural language prompt parser for RPA automation.
Converts human-readable prompts into structured action sequences.
"""

import re
from typing import List, Dict, Any, Optional
from .models import ActionStep, PromptAction
import logging

logger = logging.getLogger(__name__)


class PromptParser:
    """
    Parses natural language prompts into structured automation actions.
    Designed to work with LLM-generated or human-written prompts.
    """

    def __init__(self):
        # Action patterns for common automation tasks.
        #
        # IMPORTANT: intent detection iterates these in order and returns the
        # first match, so more specific intents (screenshot, double/right click,
        # hotkey, press_key) MUST come before the generic 'click'/'type'
        # patterns, which would otherwise swallow phrases like "press Ctrl+C".
        self.action_patterns = {
            "screenshot": [
                r"(?:take|capture|grab|snap) (?:a |another )?screenshot",
                r"\bscreenshot\b",
            ],
            "double_click": [
                r"double[-\s]?click (?:on |the )?(.+)",
            ],
            "right_click": [
                r"right[-\s]?click (?:on |the )?(.+)",
            ],
            "hotkey": [
                r"(?:press|hit|use)\s+(?:hotkey\s+)?(ctrl|cmd|command|alt|option|shift|win)\s*\+\s*(\w+)",
            ],
            "press_key": [
                r"(?:press|hit)\s+(?:the\s+)?(\w+)\s+key",
            ],
            "navigate": [
                r"(?:go to|navigate to|visit) (.+)",
                r"browse to (.+)",
            ],
            "open": [
                r"open (.+)",
                r"launch (.+)",
                r"start (.+)",
            ],
            "close": [
                r"close (?:the )?(.+)",
                r"quit (?:the )?(.+)",
                r"exit (?:the )?(.+)",
            ],
            "wait": [
                r"wait (?:for )?(\d+\.?\d*) (?:seconds?|secs?)",
                r"pause (?:for )?(\d+\.?\d*) (?:seconds?|secs?)",
            ],
            "scroll": [
                r"scroll (up|down)(?:\s+(\d+))?",
                r"scroll (\d+) (?:times|clicks)",
                r"scroll (\d+)",
            ],
            "type": [
                r"type (.+)",
                r"enter (.+)",
                r"input (.+)",
                r"write (.+)",
            ],
            "click": [
                r"click (?:on |the )?(.+)",
                r"press (?:on |the )?(.+)",
                r"tap (?:on |the )?(.+)",
            ],
        }

        # Common application mappings
        self.app_mappings = {
            "chrome": ["chrome", "google chrome", "browser"],
            "firefox": ["firefox", "mozilla"],
            "notepad": ["notepad", "text editor"],
            "calculator": ["calculator", "calc"],
            "terminal": ["terminal", "command prompt", "cmd", "powershell"],
        }

    def parse(self, prompt: str) -> PromptAction:
        """
        Parse a natural language prompt into structured actions.

        Args:
            prompt: Natural language description of automation task

        Returns:
            PromptAction with intent, entities, and suggested steps
        """
        logger.info(f"Parsing prompt: {prompt}")

        prompt_lower = prompt.lower().strip()

        # Detect intent and extract entities
        intent = self._detect_intent(prompt_lower)
        entities = self._extract_entities(prompt_lower)

        # Generate suggested action steps
        suggested_steps = self._generate_steps(prompt_lower, intent, entities)

        # Calculate confidence based on pattern matches
        confidence = self._calculate_confidence(prompt_lower, suggested_steps)

        return PromptAction(
            intent=intent,
            entities=entities,
            confidence=confidence,
            suggested_steps=suggested_steps
        )

    def parse_multi_step(self, prompt: str) -> List[PromptAction]:
        """
        Parse a multi-step prompt (separated by 'then', 'and then', 'next', etc.)

        Args:
            prompt: Multi-step natural language prompt

        Returns:
            List of PromptActions, one for each step
        """
        # Split on common separators
        separators = [r"\bthen\b", r"\band then\b", r"\bnext\b", r"\bafter that\b", r"\bfinally\b"]
        pattern = "|".join(separators)

        steps = re.split(pattern, prompt, flags=re.IGNORECASE)
        steps = [s.strip(" ,.") for s in steps if s.strip(" ,.")]

        logger.info(f"Parsed {len(steps)} steps from multi-step prompt")

        return [self.parse(step) for step in steps]

    def _detect_intent(self, prompt: str) -> str:
        """Detect the primary intent of the prompt."""
        # Check for compound intents first (open + navigate in one breath).
        if any(word in prompt for word in ["open", "launch", "start"]) and \
           any(phrase in prompt for phrase in ["navigate", "go to", "visit"]):
            return "open_and_navigate"

        if any(word in prompt for word in ["fill", "complete"]) and \
           any(word in prompt for word in ["form", "fields"]):
            return "fill_form"

        # Check for specific action patterns (ordered most- to least-specific).
        for action_type, patterns in self.action_patterns.items():
            for pattern in patterns:
                if re.search(pattern, prompt, re.IGNORECASE):
                    return action_type

        return "unknown"

    def _extract_entities(self, prompt: str) -> Dict[str, Any]:
        """Extract entities (applications, URLs, text, etc.) from prompt."""
        entities = {}

        # Extract URLs
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, prompt)
        if urls:
            entities["url"] = urls[0]

        # Extract quoted text (for typing)
        quoted_pattern = r'["\']([^"\']+)["\']'
        quoted_text = re.findall(quoted_pattern, prompt)
        if quoted_text:
            entities["text"] = quoted_text[0]

        # Extract numbers (for coordinates, wait times, etc.)
        number_pattern = r'\b(\d+\.?\d*)\b'
        numbers = re.findall(number_pattern, prompt)
        if numbers:
            entities["numbers"] = [float(n) for n in numbers]

        # Extract application names
        for app_name, aliases in self.app_mappings.items():
            if any(alias in prompt for alias in aliases):
                entities["application"] = app_name
                break

        return entities

    def _extract_target(self, prompt: str, intent: str) -> str:
        """Extract the target element text for a (double/right) click intent."""
        for pattern in self.action_patterns.get(intent, []):
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match and match.groups():
                return match.group(1).strip()
        return "element"

    def _generate_steps(self, prompt: str, intent: str, entities: Dict[str, Any]) -> List[ActionStep]:
        """Generate suggested action steps based on intent and entities."""
        steps = []

        if intent == "open":
            app = entities.get("application", "application")
            steps.append(ActionStep(
                action="open_application",
                description=f"Open {app}",
                target=app,
                wait_after=2.0
            ))

        elif intent == "close":
            app = entities.get("application")
            if not app:
                match = re.search(self.action_patterns["close"][0], prompt, re.IGNORECASE)
                app = match.group(1).strip() if match else "application"
            steps.append(ActionStep(
                action="close_application",
                description=f"Close {app}",
                target=app,
                wait_after=1.0
            ))

        elif intent == "navigate":
            url = entities.get("url", "")
            steps.append(ActionStep(
                action="type",
                description=f"Navigate to {url}",
                text=url,
                wait_after=1.0
            ))
            steps.append(ActionStep(
                action="press_key",
                description="Press Enter to navigate",
                key="enter",
                wait_after=2.0
            ))

        elif intent == "open_and_navigate":
            app = entities.get("application", "browser")
            url = entities.get("url", "")

            steps.append(ActionStep(
                action="open_application",
                description=f"Open {app}",
                target=app,
                wait_after=2.0
            ))
            steps.append(ActionStep(
                action="hotkey",
                description="Focus address bar",
                keys=["ctrl", "l"],
                wait_after=0.5
            ))
            steps.append(ActionStep(
                action="type",
                description=f"Type URL: {url}",
                text=url,
                wait_after=0.5
            ))
            steps.append(ActionStep(
                action="press_key",
                description="Navigate to URL",
                key="enter",
                wait_after=2.0
            ))

        elif intent == "type":
            text = entities.get("text", "")
            steps.append(ActionStep(
                action="type",
                description=f"Type: {text}",
                text=text
            ))

        elif intent == "screenshot":
            steps.append(ActionStep(
                action="screenshot",
                description="Take a screenshot"
            ))

        elif intent in ("click", "double_click", "right_click"):
            target = self._extract_target(prompt, intent)
            verb = {"click": "Click", "double_click": "Double-click", "right_click": "Right-click"}[intent]
            steps.append(ActionStep(
                action=intent,
                description=f"{verb} on {target}",
                target=target
            ))

        elif intent == "wait":
            numbers = entities.get("numbers", [1.0])
            wait_time = numbers[0] if numbers else 1.0
            steps.append(ActionStep(
                action="wait",
                description=f"Wait for {wait_time} seconds",
                wait_before=0.0,
                wait_after=wait_time
            ))

        elif intent == "scroll":
            # Determine scroll direction and amount. Positive = up, negative = down.
            numbers = entities.get("numbers", [])
            amount = int(numbers[0]) if numbers else 5
            if "up" in prompt:
                clicks = abs(amount)
            elif "down" in prompt:
                clicks = -abs(amount)
            else:
                clicks = -abs(amount)  # default to scrolling down

            steps.append(ActionStep(
                action="scroll",
                description=f"Scroll {'up' if clicks > 0 else 'down'} {abs(clicks)} clicks",
                notes=f"Scroll amount: {clicks}"
            ))

        elif intent == "press_key":
            # Extract key name (covers both 'press ... key' and 'hit ... key').
            match = re.search(self.action_patterns["press_key"][0], prompt, re.IGNORECASE)
            key = match.group(1) if match else "enter"

            steps.append(ActionStep(
                action="press_key",
                description=f"Press {key} key",
                key=key.lower()
            ))

        elif intent == "hotkey":
            # Extract hotkey combination
            match = re.search(self.action_patterns["hotkey"][0], prompt, re.IGNORECASE)
            if match:
                modifier = match.group(1).lower()
                # Normalize common aliases to pyautogui key names.
                modifier = {"command": "cmd", "option": "alt"}.get(modifier, modifier)
                key = match.group(2).lower()
                steps.append(ActionStep(
                    action="hotkey",
                    description=f"Press {modifier}+{key}",
                    keys=[modifier, key]
                ))

        return steps

    def _calculate_confidence(self, prompt: str, steps: List[ActionStep]) -> float:
        """Calculate confidence score based on pattern matches and step generation."""
        if not steps:
            return 0.0

        # Base confidence on number of matched patterns
        matched_patterns = 0
        total_patterns = sum(len(patterns) for patterns in self.action_patterns.values())

        for patterns in self.action_patterns.values():
            for pattern in patterns:
                if re.search(pattern, prompt, re.IGNORECASE):
                    matched_patterns += 1

        pattern_confidence = matched_patterns / max(total_patterns, 1)

        # Boost confidence if we generated steps
        step_confidence = min(len(steps) * 0.2, 0.8)

        # Combine confidences
        final_confidence = (pattern_confidence * 0.4) + (step_confidence * 0.6)

        return min(final_confidence, 1.0)

    def prompt_to_workflow_json(self, prompt: str, workflow_name: str = "generated_workflow") -> str:
        """
        Convert a prompt directly to workflow JSON format.
        Useful for LLM integration.

        Args:
            prompt: Natural language prompt
            workflow_name: Name for the generated workflow

        Returns:
            JSON string representation of the workflow
        """
        from .models import Workflow

        # Parse the prompt
        if any(sep in prompt.lower() for sep in ["then", "and then", "next", "after that"]):
            prompt_actions = self.parse_multi_step(prompt)
        else:
            prompt_actions = [self.parse(prompt)]

        # Combine all steps
        all_steps = []
        for action in prompt_actions:
            all_steps.extend(action.suggested_steps)

        # Create workflow
        workflow = Workflow(
            name=workflow_name,
            description=prompt,
            steps=all_steps
        )

        return workflow.model_dump_json(indent=2)
