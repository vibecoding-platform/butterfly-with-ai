#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AetherTerm Server Package

This package contains the main server components for AetherTerm,
including the FastAPI server, Socket.IO handlers, and terminal management.
"""

from .server import create_app, start_server

__all__ = ["start_server", "create_app"]
