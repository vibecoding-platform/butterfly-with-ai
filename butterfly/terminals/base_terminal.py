# *-* coding: utf-8 *-*
# This file is part of butterfly
#
# butterfly Copyright(C) 2015-2017 Florian Mounier
# Licensed under the same terms as the original project

import io
import os
import signal
import struct
from typing import Any, Dict, Optional

import tornado.ioloop
import tornado.options

from butterfly import utils


class BaseTerminal:
    """
    Abstract base class for Terminal, defining the core interface 
    and ensuring all subclasses implement required methods.
    """
    sessions: Dict[str, 'BaseTerminal'] = {}

    def __init__(self, user, path, session, socket, uri, render_string, broadcast):
        """
        Initialize the base terminal with core session and context information.
        
        :raises NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement __init__")

    def send(self, message: Optional[str]) -> None:
        """
        Send a message to the terminal session.
        
        :raises NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement send")

    def pty(self) -> None:
        """
        Create a pseudo-terminal (PTY) for the session.
        
        :raises NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement pty")

    def determine_user(self) -> None:
        """
        Determine the user for the terminal session.
        
        :raises NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement determine_user")

    def shell(self) -> None:
        """
        Start the user's shell or specified command.
        
        :raises NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement shell")

    def communicate(self) -> None:
        """
        Set up communication channels for the terminal.
        
        :raises NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement communicate")

    def write(self, message: str) -> None:
        """
        Write a message to the terminal.
        
        :raises NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement write")

    def ctl(self, message: Dict[str, Any]) -> None:
        """
        Handle terminal control messages.
        
        :raises NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement ctl")

    def shell_handler(self, fd: int, events: int) -> None:
        """
        Handle shell I/O events.
        
        :raises NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement shell_handler")

    def close(self) -> None:
        """
        Close the terminal session and clean up resources.
        
        :raises NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement close")