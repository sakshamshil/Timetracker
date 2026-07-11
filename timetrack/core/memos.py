# project/timetrack/core/memos.py
"""Memo management for the timetrack application."""

import textwrap
from datetime import datetime
from typing import Tuple

from ..models import Memo
from .storage import Storage
from .utils import truncate_text

MEMO_NOTE_WIDTH = 45
MEMO_NOTE_INDENT = 27


class MemoManager:
    """
    Manages global memos/notes.

    Memos are standalone notes not attached to any specific task,
    useful for reminders or general notes during work.
    """

    def __init__(self, storage: Storage):
        """
        Initialize the MemoManager.

        Args:
            storage: The Storage instance for persistence.
        """
        self.storage = storage

    def add(self, text: str) -> Tuple[bool, str]:
        """
        Adds a new global memo.

        Args:
            text: The memo content.

        Returns:
            A tuple containing a success flag and a message.
        """
        memo = Memo(text=text, created_at=datetime.now())
        memos = self.storage.read_memos()
        memos.memos.append(memo)
        self.storage.write_memos(memos)

        return True, "Memo added."

    def list_all(self) -> str:
        """
        Lists all global memos.

        Returns:
            A formatted string of all memos.
        """
        memos = self.storage.read_memos()
        if not memos.memos:
            return "No memos found."

        output = ["--- Memos ---"]
        output.append("{:<5} {:<20} {}".format("ID", "Created", "Note"))
        output.append("-" * 70)

        for i, memo in enumerate(memos.memos):
            created_str = memo.created_at.strftime("%Y-%m-%d %H:%M")
            # Wrap long memos onto continuation lines aligned under the Note
            # column so the full text is shown without being cut off.
            lines = textwrap.wrap(memo.text, width=MEMO_NOTE_WIDTH) or [""]
            output.append(f"{i:<5} {created_str:<20} {lines[0]}")
            for cont in lines[1:]:
                output.append(f"{' ' * MEMO_NOTE_INDENT}{cont}")

        output.append("-" * 70)

        return "\n".join(output)

    def remove(self, memo_id: int) -> Tuple[bool, str]:
        """
        Removes a memo by its ID.

        Args:
            memo_id: The ID of the memo to remove.

        Returns:
            A tuple containing a success flag and a message.
        """
        memos = self.storage.read_memos()

        if not memos.memos:
            return False, "No memos found."

        if not (0 <= memo_id < len(memos.memos)):
            return (
                False,
                f"Invalid ID: {memo_id}. Valid IDs: 0-{len(memos.memos) - 1}.",
            )

        removed_memo = memos.memos.pop(memo_id)
        self.storage.write_memos(memos)

        # Truncate for display
        display_text = truncate_text(removed_memo.text, 30)
        return True, f"Memo removed: '{display_text}'"
