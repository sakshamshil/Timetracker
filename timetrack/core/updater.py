# project/timetrack/core/updater.py
"""Self-update functionality for the timetrack application."""

import shutil
import subprocess
from pathlib import Path
from typing import Tuple


class UpdateManager:
    """
    Manages self-update functionality.

    Handles git pull and reinstallation via pip/pipx,
    with detection of the original installation method.
    """

    def __init__(self):
        """Initialize the UpdateManager."""
        # Get the repo directory (parent of the timetrack package)
        self.repo_dir = Path(__file__).parent.parent.parent

    def _check_remote_exists(self) -> Tuple[bool, str]:
        """
        Check if git remote 'origin' exists.

        Returns:
            A tuple of (exists, remote_url).
        """
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
            )
            return result.returncode == 0, result.stdout.strip()
        except Exception:
            return False, ""

    def _add_remote(self, remote_url: str) -> Tuple[bool, str]:
        """
        Add git remote 'origin'.

        Args:
            remote_url: The URL of the remote repository.

        Returns:
            A tuple of (success, message).
        """
        try:
            result = subprocess.run(
                ["git", "remote", "add", "origin", remote_url],
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True, "Added remote origin."
            return False, f"Failed to add remote: {result.stderr}"
        except Exception as e:
            return False, f"Error adding remote: {e}"

    def _detect_installation_method(self) -> str:
        """
        Detect how track was originally installed.

        Returns:
            One of: 'pipx', 'pip', 'pip-editable'.
        """
        # Check if installed via pipx
        try:
            result = subprocess.run(
                ["pipx", "list"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and "timetrack-cli" in result.stdout:
                return "pipx"
            if result.returncode == 0 and "track" in result.stdout:
                return "pipx"
        except Exception:
            pass

        # Check if installed via pip (editable)
        try:
            pip_cmd = shutil.which("pip3") or shutil.which("pip")
            if pip_cmd:
                result = subprocess.run(
                    [pip_cmd, "show", "timetrack-cli"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    # Check if it's an editable install
                    if "Editable project location" in result.stdout:
                        return "pip-editable"
                    return "pip"
        except Exception:
            pass

        # Default to pipx if available
        if shutil.which("pipx"):
            return "pipx"

        return "pip"

    def update(self) -> Tuple[bool, str]:
        """
        Updates the application by pulling latest changes from git and reinstalling.

        Uses fail-closed error handling: stops at first error with a meaningful message.

        Returns:
            A tuple containing a success flag and a message.
        """
        # Step 1: Verify git is installed
        if not shutil.which("git"):
            # Offer alternative: pip install upgrade
            pip_cmd = shutil.which("pip3") or shutil.which("pip")
            if pip_cmd:
                try:
                    result = subprocess.run(
                        [pip_cmd, "install", "--upgrade", "timetrack-cli"],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        return (
                            True,
                            "Updated via pip (PyPI). Run 'track --version' to verify.",
                        )
                except Exception:
                    pass
            return (
                False,
                "Error: git is not installed or not in PATH.\nFor PyPI installs, run: pip install --upgrade timetrack-cli",
            )

        # Step 2: Verify this is a git repository
        git_dir = self.repo_dir / ".git"
        if not git_dir.exists():
            # This is likely a PyPI install, suggest pip upgrade
            return (
                False,
                "This appears to be a PyPI installation (not a git clone).\n"
                "To update, run: pip install --upgrade timetrack-cli\n"
                "Or reinstall with: pipx reinstall timetrack-cli",
            )

        # Step 3: Check for uncommitted changes that might cause conflicts
        try:
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
            )
            if status_result.returncode != 0:
                return (
                    False,
                    f"Error: Failed to check git status.\n{status_result.stderr}",
                )

            if status_result.stdout.strip():
                return (
                    False,
                    "Error: You have uncommitted changes. Please commit or stash them first.",
                )
        except Exception as e:
            return False, f"Error: Failed to run git status: {e}"

        # Step 4: Check if remote exists, add if missing
        remote_exists, remote_url = self._check_remote_exists()
        if not remote_exists:
            default_remote = "https://github.com/sakshamshil/Timetracker.git"
            success, msg = self._add_remote(default_remote)
            if not success:
                return (
                    False,
                    f"No git remote configured and failed to add default.\n{msg}",
                )

        # Step 5: Pull latest changes
        try:
            pull_result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
            )
            if pull_result.returncode != 0:
                return False, f"Error: git pull failed.\n{pull_result.stderr}"

            pull_output = pull_result.stdout.strip()
        except Exception as e:
            return False, f"Error: Failed to run git pull: {e}"

        # Step 6: Detect installation method and reinstall appropriately
        install_method = self._detect_installation_method()

        if install_method == "pipx":
            # Try both package names
            try:
                # First try timetrack-cli (PyPI name)
                reinstall_result = subprocess.run(
                    ["pipx", "reinstall", "timetrack-cli"],
                    cwd=self.repo_dir,
                    capture_output=True,
                    text=True,
                )
                if reinstall_result.returncode != 0:
                    # Fallback to local editable install
                    reinstall_result = subprocess.run(
                        ["pipx", "install", "-e", ".", "--force"],
                        cwd=self.repo_dir,
                        capture_output=True,
                        text=True,
                    )
                    if reinstall_result.returncode != 0:
                        return (
                            False,
                            f"Error: pipx reinstall failed.\n{reinstall_result.stderr}",
                        )
            except Exception as e:
                return False, f"Error: Failed to run pipx reinstall: {e}"
        elif install_method in ["pip", "pip-editable"]:
            pip_cmd = shutil.which("pip3") or shutil.which("pip")
            if not pip_cmd:
                return False, "Error: pip not found in PATH."

            try:
                reinstall_result = subprocess.run(
                    [pip_cmd, "install", "-e", "."],
                    cwd=self.repo_dir,
                    capture_output=True,
                    text=True,
                )
                if reinstall_result.returncode != 0:
                    return (
                        False,
                        f"Error: pip install failed.\n{reinstall_result.stderr}",
                    )
            except Exception as e:
                return False, f"Error: Failed to run pip install: {e}"
        else:
            return (
                False,
                "Error: Could not detect installation method.\nTry: pipx install -e . or pip install -e .",
            )

        # Success!
        if "Already up to date" in pull_output:
            return True, "Already up to date. No changes to pull."
        else:
            return True, f"Updated successfully!\n{pull_output}"
