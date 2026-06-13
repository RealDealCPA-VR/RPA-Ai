"""
Desktop automation engine with cross-platform support.
Executes low-level desktop actions.

The heavy ``pyautogui`` dependency is imported lazily so that the rest of the
package (models, parser, manager, executor wiring, tests) can be imported and
used on machines that do not have a display or the GUI extras installed.
Install the optional desktop dependencies with ``pip install ai-rpa-system[gui]``
(or ``pip install pyautogui``) to enable real automation.
"""

import os
import time
import platform
import shutil
import subprocess
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Cached, lazily-imported pyautogui module.
_pyautogui = None


def _get_pyautogui():
    """Import and configure pyautogui on first use.

    Raises a clear, actionable error if the optional dependency is missing
    instead of failing at package-import time.
    """
    global _pyautogui
    if _pyautogui is None:
        try:
            import pyautogui  # noqa: WPS433 (intentional lazy import)
        except Exception as exc:  # pragma: no cover - environment dependent
            raise ImportError(
                "pyautogui is required for desktop automation but is not "
                "installed. Install the GUI extras with "
                "'pip install ai-rpa-system[gui]' or 'pip install pyautogui'."
            ) from exc
        # Configure PyAutoGUI safety features once.
        pyautogui.FAILSAFE = True  # Move mouse to a corner to abort.
        pyautogui.PAUSE = 0.5  # Default pause between actions.
        _pyautogui = pyautogui
    return _pyautogui


class AutomationEngine:
    """
    Low-level automation engine for desktop interactions.
    Cross-platform support for Windows, macOS, and Linux.

    pyautogui is loaded lazily, so constructing the engine never requires a
    display. Screen dimensions are resolved on first access.
    """

    def __init__(self):
        self.platform = platform.system()
        self._screen_width: Optional[int] = None
        self._screen_height: Optional[int] = None
        logger.info(f"Automation Engine initialized on {self.platform}")

    def _ensure_screen_size(self) -> None:
        if self._screen_width is None or self._screen_height is None:
            size = _get_pyautogui().size()
            self._screen_width, self._screen_height = int(size[0]), int(size[1])
            logger.info(
                f"Screen resolution: {self._screen_width}x{self._screen_height}"
            )

    @property
    def screen_width(self) -> int:
        self._ensure_screen_size()
        return self._screen_width

    @property
    def screen_height(self) -> int:
        self._ensure_screen_size()
        return self._screen_height

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> bool:
        """
        Click at specified coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button ('left', 'right', 'middle')
            clicks: Number of clicks (1 for single, 2 for double)

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Clicking at ({x}, {y}) with {button} button, {clicks} time(s)")
            _get_pyautogui().click(x, y, clicks=clicks, button=button)
            return True
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return False

    def double_click(self, x: int, y: int) -> bool:
        """Double-click at specified coordinates."""
        return self.click(x, y, clicks=2)

    def right_click(self, x: int, y: int) -> bool:
        """Right-click at specified coordinates."""
        return self.click(x, y, button="right")

    def type_text(self, text: str, interval: float = 0.05, sensitive: bool = False) -> bool:
        """
        Type text with specified interval between keystrokes.

        Args:
            text: Text to type
            interval: Seconds between each keystroke
            sensitive: If True, never log the raw text (logs a redacted
                placeholder with the length only). The raw text is also
                redacted automatically when it is long.

        Returns:
            True if successful, False otherwise
        """
        try:
            # SECURITY: never log secrets. Redact when explicitly sensitive
            # or when the text is long enough to risk leaking credentials.
            if sensitive or len(text) > 50:
                logger.info(f"Typing text: [REDACTED] ({len(text)} chars)")
            else:
                logger.info(f"Typing text: {text}")
            _get_pyautogui().write(text, interval=interval)
            return True
        except Exception as e:
            logger.error(f"Type text failed: {e}")
            return False

    def press_key(self, key: str) -> bool:
        """
        Press a single key.

        Args:
            key: Key name (e.g., 'enter', 'tab', 'escape', 'a', 'space')

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Pressing key: {key}")
            _get_pyautogui().press(key)
            return True
        except Exception as e:
            logger.error(f"Press key failed: {e}")
            return False

    def hotkey(self, *keys: str) -> bool:
        """
        Press a combination of keys (hotkey).

        Args:
            *keys: Keys to press together (e.g., 'ctrl', 'c')

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Pressing hotkey: {'+'.join(keys)}")
            _get_pyautogui().hotkey(*keys)
            return True
        except Exception as e:
            logger.error(f"Hotkey failed: {e}")
            return False

    def move_mouse(self, x: int, y: int, duration: float = 0.5) -> bool:
        """
        Move mouse to specified coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Time to take for the movement (seconds)

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Moving mouse to ({x}, {y})")
            _get_pyautogui().moveTo(x, y, duration=duration)
            return True
        except Exception as e:
            logger.error(f"Move mouse failed: {e}")
            return False

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """
        Scroll the mouse wheel.

        Args:
            clicks: Number of "clicks" to scroll (positive = up, negative = down)
            x: Optional X coordinate to scroll at
            y: Optional Y coordinate to scroll at

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Scrolling {clicks} clicks")
            pg = _get_pyautogui()
            if x is not None and y is not None:
                pg.scroll(clicks, x=x, y=y)
            else:
                pg.scroll(clicks)
            return True
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return False

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int,
             duration: float = 0.5, button: str = "left") -> bool:
        """
        Drag from one point to another.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            duration: Time to take for the drag (seconds)
            button: Mouse button to use

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Dragging from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            pg = _get_pyautogui()
            pg.moveTo(start_x, start_y)
            pg.dragTo(end_x, end_y, duration=duration, button=button)
            return True
        except Exception as e:
            logger.error(f"Drag failed: {e}")
            return False

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None,
                   save_path: Optional[str] = None) -> Optional[str]:
        """
        Take a screenshot.

        Args:
            region: Optional (x, y, width, height) tuple for partial screenshot
            save_path: Optional path to save the screenshot

        Returns:
            Path to saved screenshot, or None if failed
        """
        try:
            logger.info("Taking screenshot")
            pg = _get_pyautogui()
            if region:
                screenshot = pg.screenshot(region=region)
            else:
                screenshot = pg.screenshot()

            if not save_path:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                save_path = f"screenshot_{timestamp}.png"

            screenshot.save(save_path)
            logger.info(f"Screenshot saved to {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None

    def find_image_on_screen(self, image_path: str, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
        """
        Find an image on the screen using template matching.

        Args:
            image_path: Path to the image to find
            confidence: Confidence threshold (0.0-1.0)

        Returns:
            (x, y) coordinates of the center of the found image, or None if not found
        """
        try:
            logger.info(f"Searching for image: {image_path}")
            location = _get_pyautogui().locateCenterOnScreen(image_path, confidence=confidence)
            if location:
                logger.info(f"Image found at {location}")
                return int(location[0]), int(location[1])
            logger.warning(f"Image not found: {image_path}")
            return None
        except Exception as e:
            logger.error(f"Image search failed: {e}")
            return None

    def wait_for_image(self, image_path: str, timeout: float = 10.0,
                       interval: float = 0.5, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
        """
        Poll the screen for an image until it appears or the timeout elapses.

        Repeatedly calls :meth:`find_image_on_screen`, sleeping ``interval``
        seconds between attempts, until a location is found or ``timeout``
        seconds have passed (measured against a ``time.time()`` deadline).

        Args:
            image_path: Path to the image to wait for
            timeout: Maximum seconds to wait before giving up
            interval: Seconds to sleep between polls
            confidence: Confidence threshold (0.0-1.0) for template matching

        Returns:
            (x, y) coordinates of the center of the found image, or None if it
            did not appear within the timeout
        """
        logger.info(
            f"Waiting up to {timeout}s for image: {image_path}"
        )
        deadline = time.time() + timeout
        while True:
            location = self.find_image_on_screen(image_path, confidence=confidence)
            if location is not None:
                return location
            if time.time() >= deadline:
                logger.warning(
                    f"Timed out after {timeout}s waiting for image: {image_path}"
                )
                return None
            time.sleep(interval)

    def open_application(self, name: str) -> bool:
        """
        Launch an application by name, using the host platform's launcher.

        Windows: ``start``; macOS: ``open -a``; Linux: the executable on PATH.

        Args:
            name: Application name or executable (e.g., 'notepad', 'Google Chrome')

        Returns:
            True if the launch command was issued successfully, False otherwise
        """
        try:
            logger.info(f"Opening application: {name}")
            if self.platform == "Windows":
                # SECURITY: never use a shell. os.startfile launches the
                # app/document via the OS shell-association without exposing
                # the name to a command interpreter (no command injection).
                try:
                    os.startfile(name)  # type: ignore[attr-defined]
                except Exception as exc:
                    logger.error(f"Open application failed: {exc}")
                    return False
            elif self.platform == "Darwin":
                subprocess.Popen(["open", "-a", name])
            else:  # Linux / other POSIX
                executable = shutil.which(name) or name
                subprocess.Popen([executable])
            return True
        except Exception as e:
            logger.error(f"Open application failed: {e}")
            return False

    def close_application(self, name: str) -> bool:
        """
        Close/terminate an application by name.

        Windows: ``taskkill``; macOS/Linux: ``pkill``.

        Args:
            name: Application/process name to close

        Returns:
            True if the close command was issued successfully, False otherwise
        """
        try:
            logger.info(f"Closing application: {name}")
            if self.platform == "Windows":
                image = name if name.lower().endswith(".exe") else f"{name}.exe"
                subprocess.run(["taskkill", "/IM", image, "/F"], check=False)
            else:
                subprocess.run(["pkill", "-f", name], check=False)
            return True
        except Exception as e:
            logger.error(f"Close application failed: {e}")
            return False

    def wait(self, seconds: float) -> bool:
        """
        Wait for specified duration.

        Args:
            seconds: Number of seconds to wait

        Returns:
            True (always successful)
        """
        logger.info(f"Waiting for {seconds} seconds")
        time.sleep(seconds)
        return True

    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        pos = _get_pyautogui().position()
        return int(pos[0]), int(pos[1])

    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        return self.screen_width, self.screen_height

    def is_point_on_screen(self, x: int, y: int) -> bool:
        """Check if coordinates are within screen bounds."""
        return 0 <= x < self.screen_width and 0 <= y < self.screen_height
