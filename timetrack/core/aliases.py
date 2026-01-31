# project/timetrack/core/aliases.py
"""Alias management for the timetrack application."""

from typing import Optional, Tuple

from .storage import Storage


class AliasManager:
    """
    Manages task aliases (e.g., @work -> "Working on project").

    Aliases provide shorthand for frequently used activity names,
    making it faster to start common tasks.
    """

    def __init__(self, storage: Storage):
        """
        Initialize the AliasManager.

        Args:
            storage: The Storage instance for persistence.
        """
        self.storage = storage

    def resolve_alias(self, activity: str) -> Optional[str]:
        """
        Resolves an alias to its full activity name.

        Args:
            activity: The activity string, possibly an alias (starting with @).

        Returns:
            The resolved activity name, or None if the alias doesn't exist.
            Returns the original activity unchanged if it's not an alias.
        """
        if not activity.startswith("@"):
            return activity

        config = self.storage.read_config()
        if activity in config.aliases:
            return config.aliases[activity]
        return None

    def add(self, alias: str, activity: str) -> Tuple[bool, str]:
        """
        Adds or updates an alias.

        Args:
            alias: The alias name (must start with '@').
            activity: The full activity name to map to.

        Returns:
            A tuple containing a success flag and a message.
        """
        if not alias.startswith("@"):
            return False, "Error: Alias must start with '@'."

        config = self.storage.read_config()
        config.aliases[alias] = activity
        self.storage.write_config(config)

        return True, f"Alias '{alias}' set to '{activity}'."

    def remove(self, alias: str) -> Tuple[bool, str]:
        """
        Removes an alias.

        Args:
            alias: The alias name to remove.

        Returns:
            A tuple containing a success flag and a message.
        """
        config = self.storage.read_config()
        if alias not in config.aliases:
            return False, f"Error: Alias '{alias}' not found."

        del config.aliases[alias]
        self.storage.write_config(config)

        return True, f"Alias '{alias}' removed."

    def list_all(self) -> str:
        """
        Lists all configured aliases.

        Returns:
            A formatted string of all aliases.
        """
        config = self.storage.read_config()
        if not config.aliases:
            return "No aliases defined."

        output = ["--- Configured Aliases ---"]
        for alias, activity in config.aliases.items():
            output.append(f"{alias} -> {activity}")

        return "\n".join(output)
