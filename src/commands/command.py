#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Command Pattern for Undo/Redo in NextPDF Pro
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


class Command(ABC):
    """Base class for all commands supporting undo/redo."""
    
    @abstractmethod
    def execute(self) -> bool:
        """Execute the command."""
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """Undo the command."""
        pass
    
    @abstractmethod
    def redo(self) -> bool:
        """Redo the command."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the command."""
        pass


class CommandStack:
    """Manages command history for undo/redo."""
    
    def __init__(self, max_size: int = 100):
        self._undo_stack: list = []
        self._redo_stack: list = []
        self._max_size = max_size
    
    def push(self, command: Command) -> None:
        """Push a command onto the undo stack and execute it."""
        if command.execute():
            self._undo_stack.append(command)
            # Clear redo stack on new command
            self._redo_stack.clear()
            
            # Limit stack size
            if len(self._undo_stack) > self._max_size:
                self._undo_stack.pop(0)
    
    def undo(self) -> Optional[Command]:
        """Undo the last command."""
        if not self._undo_stack:
            return None
        
        command = self._undo_stack.pop()
        if command.undo():
            self._redo_stack.append(command)
            return command
        else:
            # Put it back if undo failed
            self._undo_stack.append(command)
            return None
    
    def redo(self) -> Optional[Command]:
        """Redo the last undone command."""
        if not self._redo_stack:
            return None
        
        command = self._redo_stack.pop()
        if command.redo():
            self._undo_stack.append(command)
            return command
        else:
            self._redo_stack.append(command)
            return None
    
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0
    
    def clear(self):
        """Clear all command history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
    
    def get_undo_description(self) -> Optional[str]:
        if self._undo_stack:
            return self._undo_stack[-1].description
        return None
    
    def get_redo_description(self) -> Optional[str]:
        if self._redo_stack:
            return self._redo_stack[-1].description
        return None


class EditTextCommand(Command):
    """Command for editing text runs."""
    
    def __init__(self, text_editor, run_id: str, new_text: str,
                 old_text: str, new_props: Dict, old_props: Dict):
        self._editor = text_editor
        self._run_id = run_id
        self._new_text = new_text
        self._old_text = old_text
        self._new_props = new_props
        self._old_props = old_props
        self._executed = False
    
    def execute(self) -> bool:
        result = self._editor.edit_text_run(
            self._run_id, self._new_text,
            font_name=self._new_props.get("font_name"),
            font_size=self._new_props.get("font_size"),
            color=self._new_props.get("color"),
            bold=self._new_props.get("bold"),
            italic=self._new_props.get("italic"),
            underline=self._new_props.get("underline"),
            alignment=self._new_props.get("alignment"),
            direction=self._new_props.get("direction"),
        )
        self._executed = result.success
        return result.success
    
    def undo(self) -> bool:
        result = self._editor.edit_text_run(
            self._run_id, self._old_text,
            font_name=self._old_props.get("font_name"),
            font_size=self._old_props.get("font_size"),
            color=self._old_props.get("color"),
            bold=self._old_props.get("bold"),
            italic=self._old_props.get("italic"),
            underline=self._old_props.get("underline"),
            alignment=self._old_props.get("alignment"),
            direction=self._old_props.get("direction"),
        )
        return result.success
    
    def redo(self) -> bool:
        return self.execute()
    
    @property
    def description(self) -> str:
        return f"Edit text: {self._new_text[:30]}"


class InsertTextCommand(Command):
    """Command for inserting a new text box."""
    
    def __init__(self, text_editor, page_number: int, x: float, y: float,
                 text: str, **kwargs):
        self._editor = text_editor
        self._page_number = page_number
        self._x = x
        self._y = y
        self._text = text
        self._kwargs = kwargs
        self._run_id = None
        self._executed = False
    
    def execute(self) -> bool:
        result = self._editor.add_text_box(
            self._page_number, self._x, self._y,
            self._text, **self._kwargs
        )
        if result.success:
            self._run_id = result.run_id
            self._executed = True
        return result.success
    
    def undo(self) -> bool:
        if self._run_id:
            return self._editor.delete_text_run(self._run_id)
        return False
    
    def redo(self) -> bool:
        return self.execute()
    
    @property
    def description(self) -> str:
        return f"Insert text: {self._text[:30]}"


class DeleteTextCommand(Command):
    """Command for deleting a text run."""

    def __init__(self, text_editor, run_id: str, run_data: dict):
        self._editor = text_editor
        self._run_id = run_id
        self._run_data = run_data
        self._executed = False

    def execute(self) -> bool:
        result = self._editor.delete_text_run(self._run_id)
        self._executed = result
        return result

    def undo(self) -> bool:
        # Re-insert the deleted text
        result = self._editor.add_text_box(
            self._run_data.get("page_number", 1),
            self._run_data.get("x", 0),
            self._run_data.get("y", 0),
            self._run_data.get("text", ""),
            font_name=self._run_data.get("font_name", "Helvetica"),
            font_size=self._run_data.get("font_size", 12),
            color=tuple(self._run_data.get("color", [0, 0, 0])),
            direction=self._run_data.get("direction", "LTR"),
        )
        # Set the original run_id back
        if result.success and result.run_id:
            # We can't easily set the original ID, but the text is restored
            pass
        return result.success

    def redo(self) -> bool:
        return self.execute()

    @property
    def description(self) -> str:
        return "Delete text"


class PDFSnapshotCommand(Command):
    """
    Generic command that snapshots the real PDF bytes before and after an
    operation.  Undo/redo restores actual page content, not just UI state.

    The callable may return a value; it is available as ``command.result``
    after ``execute()`` so callers can inspect an engine result.
    """

    def __init__(self, document, description: str, action):
        self._document = document
        self._description = description
        self._action = action
        self._before = document.to_bytes()
        self._after = None
        self.result = None

    def execute(self) -> bool:
        self.result = self._action()
        if self.result is False:
            return False
        if getattr(self.result, "success", True) is False:
            # Engine refused the operation; keep the undo stack clean.
            return False
        self._after = self._document.to_bytes()
        return True

    def undo(self) -> bool:
        return bool(self._before) and self._document.restore_from_bytes(self._before)

    def redo(self) -> bool:
        return bool(self._after) and self._document.restore_from_bytes(self._after)

    @property
    def description(self) -> str:
        return self._description
