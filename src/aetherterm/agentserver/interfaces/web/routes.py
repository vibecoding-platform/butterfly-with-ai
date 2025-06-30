"""
Main Routes Module - Simplified Route Management

This file now serves as the main entry point for all web routes,
using a modular structure for better organization and maintainability.
"""

import logging
from fastapi import APIRouter

# Import API routes
from aetherterm.agentserver.interfaces.api.inventory_api import inventory_router
from aetherterm.agentserver.interfaces.api.log_processing_api import router as log_processing_router

# Import modular web routes
from .routes import router as web_routes_router

# Initialize main router
router = APIRouter()
log = logging.getLogger("aetherterm.routes")

# Include API routes
router.include_router(inventory_router, prefix="/api")
router.include_router(log_processing_router, prefix="/api")

# Include web routes (main pages, themes, sessions, agents, specs)
router.include_router(web_routes_router)


