#!/usr/bin/env python

"""
AetherTerm Server Package

This package contains the main server components for AetherTerm,
including the FastAPI server, Socket.IO handlers, and terminal management.
"""

from .interfaces.web.server import create_app, start_server

__all__ = ["create_app", "start_server"]
