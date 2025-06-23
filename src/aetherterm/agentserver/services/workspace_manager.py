"""
Workspace Management Service for Tab and Pane structure
Handles multi-window synchronization and state management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from collections import defaultdict

from aetherterm.agentserver.models.session import (
    TerminalTab,
    TerminalPane,
    User,
    UserPermission,
    TabType,
)

log = logging.getLogger(__name__)


class UIState:
    """UI state for multi-window synchronization"""

    def __init__(self):
        self.active_tab_id: Optional[str] = None
        self.panel_width: int = 320
        self.is_panel_visible: bool = True
        self.panel_position: Dict[str, int] = {"x": 20, "y": 60}
        self.last_updated: datetime = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "activeTabId": self.active_tab_id,
            "panelWidth": self.panel_width,
            "isPanelVisible": self.is_panel_visible,
            "panelPosition": self.panel_position,
            "lastUpdated": self.last_updated.isoformat(),
        }

    def update_from_dict(self, data: Dict[str, Any]):
        """Update UI state from dictionary data"""
        if "activeTabId" in data:
            self.active_tab_id = data["activeTabId"]
        if "panelWidth" in data:
            self.panel_width = data["panelWidth"]
        if "isPanelVisible" in data:
            self.is_panel_visible = data["isPanelVisible"]
        if "panelPosition" in data:
            self.panel_position = data["panelPosition"]
        self.last_updated = datetime.now()


class WorkspaceManager:
    """
    Workspace management service for tab and pane structure
    - Manages tab lifecycle (create, update, delete)
    - Handles pane operations within tabs
    - Maintains global UI state for multi-window sync
    - Coordinates real-time synchronization between clients
    """

    def __init__(self):
        # Core state
        self._tabs: Dict[str, TerminalTab] = {}  # tab_id -> TerminalTab
        self._panes: Dict[str, TerminalPane] = {}  # pane_id -> TerminalPane
        self._ui_state = UIState()

        # Client management
        self._connected_clients: Set[str] = set()  # socket_ids
        self._client_users: Dict[str, User] = {}  # socket_id -> User

        # Event callbacks for real-time sync
        self._event_callbacks: List[Callable] = []

        # Initialize with default tab if none exist
        self._ensure_default_tab()

    def add_event_callback(self, callback: Callable):
        """Add callback for workspace events"""
        self._event_callbacks.append(callback)

    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit event to all callbacks"""
        for callback in self._event_callbacks:
            try:
                await callback(event_type, data)
            except Exception as e:
                log.error(f"Error in event callback: {e}")

    def _ensure_default_tab(self):
        """Ensure at least one tab exists"""
        if not self._tabs:
            log.info(f"🔧 Creating default tab (current tabs: {len(self._tabs)})")
            default_tab = self._create_default_tab()
            self._tabs[default_tab.id] = default_tab
            self._ui_state.active_tab_id = default_tab.id
            log.info(f"✅ Created default tab {default_tab.id} (total tabs: {len(self._tabs)})")
        else:
            log.info(f"📋 Default tab already exists (total tabs: {len(self._tabs)})")

    def _create_default_tab(self) -> TerminalTab:
        """Create default terminal tab with one pane"""
        from uuid import uuid4

        tab_id = f"terminal-{uuid4().hex[:11]}"
        pane_id = f"pane-{uuid4().hex[:11]}"
        terminal_id = f"term-{uuid4().hex[:11]}"

        # Create main pane
        main_pane = TerminalPane(
            id=pane_id,
            terminal_id=terminal_id,
            title="Main",
            shell_type="bash",
            working_directory="~",
            position={"x": 0, "y": 0, "width": 100, "height": 100},
            is_active=True,
        )

        # Create tab with pane
        tab = TerminalTab(
            id=tab_id,
            title="Terminal 1",
            type=TabType.TERMINAL,
            panes=[main_pane],
            active_pane_id=pane_id,
            layout="horizontal",
        )

        # Register pane
        self._panes[pane_id] = main_pane

        return tab

    # Client Management

    async def add_client(self, socket_id: str, user: User) -> Dict[str, Any]:
        """Add new client and return current workspace state"""
        self._connected_clients.add(socket_id)
        self._client_users[socket_id] = user

        log.info(f"Client {socket_id} connected as {user.name}")

        # Return full workspace state for initialization
        full_state = await self.get_full_workspace_state()

        await self._emit_event(
            "client_connected",
            {
                "socket_id": socket_id,
                "user": user.to_dict() if hasattr(user, "to_dict") else str(user),
                "client_count": len(self._connected_clients),
            },
        )

        return full_state

    async def remove_client(self, socket_id: str):
        """Remove client from workspace"""
        if socket_id in self._connected_clients:
            self._connected_clients.remove(socket_id)
            user = self._client_users.pop(socket_id, None)

            log.info(f"Client {socket_id} disconnected")

            await self._emit_event(
                "client_disconnected",
                {
                    "socket_id": socket_id,
                    "user": user.to_dict() if user and hasattr(user, "to_dict") else str(user),
                    "client_count": len(self._connected_clients),
                },
            )

    async def get_full_workspace_state(self) -> Dict[str, Any]:
        """Get complete workspace state for client initialization"""
        return {
            "tabs": [tab.to_dict() for tab in self._tabs.values()],
            "uiState": self._ui_state.to_dict(),
            "connectedClients": len(self._connected_clients),
            "timestamp": datetime.now().isoformat(),
        }

    # Tab Management

    async def create_tab(self, title: str = None, tab_type: str = "terminal") -> TerminalTab:
        """Create new terminal tab"""
        log.info(f"🔧 Creating new tab '{title}' (current tabs: {len(self._tabs)})")
        from uuid import uuid4

        tab_id = f"terminal-{uuid4().hex[:11]}"
        pane_id = f"pane-{uuid4().hex[:11]}"
        terminal_id = f"term-{uuid4().hex[:11]}"

        # Create main pane for new tab
        main_pane = TerminalPane(
            id=pane_id,
            terminal_id=terminal_id,
            title="Main",
            shell_type="bash",
            working_directory="~",
            position={"x": 0, "y": 0, "width": 100, "height": 100},
            is_active=True,
        )

        # Create tab
        tab = TerminalTab(
            id=tab_id,
            title=title or f"Terminal {len(self._tabs) + 1}",
            type=TabType.TERMINAL,
            panes=[main_pane],
            active_pane_id=pane_id,
            layout="horizontal",
        )

        # Register tab and pane
        self._tabs[tab_id] = tab
        self._panes[pane_id] = main_pane

        # Emit event for real-time sync
        await self._emit_event("tab_created", {"tab": tab.to_dict()})

        log.info(f"Created tab {tab_id}: {tab.title}")
        return tab

    async def switch_tab(self, tab_id: str) -> bool:
        """Switch to specified tab"""
        if tab_id not in self._tabs:
            return False

        # Update internal state but do not broadcast to maintain per-window active tab
        old_tab_id = self._ui_state.active_tab_id
        self._ui_state.active_tab_id = tab_id
        self._ui_state.last_updated = datetime.now()

        # Do not emit tab_switched event - each window should maintain its own active tab
        # await self._emit_event("tab_switched", {
        #     "oldTabId": old_tab_id,
        #     "newTabId": tab_id,
        #     "uiState": self._ui_state.to_dict()
        # })

        log.debug(f"Switched to tab {tab_id} (no broadcast)")
        return True

    async def close_tab(self, tab_id: str) -> bool:
        """Close specified tab"""
        if tab_id not in self._tabs:
            return False

        tab = self._tabs[tab_id]

        # Remove all panes in this tab
        for pane in tab.panes:
            if pane.id in self._panes:
                del self._panes[pane.id]

        # Remove tab
        del self._tabs[tab_id]

        # Update active tab if necessary
        if self._ui_state.active_tab_id == tab_id:
            if self._tabs:
                # Switch to first available tab
                self._ui_state.active_tab_id = next(iter(self._tabs.keys()))
            else:
                # Create new default tab if no tabs left
                default_tab = self._create_default_tab()
                self._tabs[default_tab.id] = default_tab
                self._ui_state.active_tab_id = default_tab.id

        await self._emit_event("tab_closed", {"tabId": tab_id, "uiState": self._ui_state.to_dict()})

        log.info(f"Closed tab {tab_id}")
        return True

    # Pane Management

    async def split_pane(
        self, tab_id: str, pane_id: str, direction: str = "horizontal"
    ) -> Optional[TerminalPane]:
        """Split pane in specified direction"""
        if tab_id not in self._tabs or pane_id not in self._panes:
            return None

        tab = self._tabs[tab_id]
        source_pane = self._panes[pane_id]

        # Create new pane
        from uuid import uuid4

        new_pane_id = f"pane-{uuid4().hex[:11]}"
        new_terminal_id = f"term-{uuid4().hex[:11]}"

        # Calculate new positions based on split direction
        if direction == "horizontal":
            # Split horizontally (side by side)
            source_pane.position["width"] = 50
            new_position = {
                "x": 50,
                "y": source_pane.position["y"],
                "width": 50,
                "height": source_pane.position["height"],
            }
        else:
            # Split vertically (top and bottom)
            source_pane.position["height"] = 50
            new_position = {
                "x": source_pane.position["x"],
                "y": 50,
                "width": source_pane.position["width"],
                "height": 50,
            }

        # Create new pane
        new_pane = TerminalPane(
            id=new_pane_id,
            terminal_id=new_terminal_id,
            title=f"Split {len(tab.panes) + 1}",
            shell_type="bash",
            working_directory="~",
            position=new_position,
            is_active=True,
        )

        # Add to tab and register
        tab.panes.append(new_pane)
        tab.active_pane_id = new_pane_id
        self._panes[new_pane_id] = new_pane

        # Deactivate source pane
        source_pane.is_active = False

        await self._emit_event(
            "pane_created",
            {"tabId": tab_id, "pane": new_pane.to_dict(), "sourcePane": source_pane.to_dict()},
        )

        log.info(f"Split pane {pane_id} {direction}ly in tab {tab_id}")
        return new_pane

    async def close_pane(self, tab_id: str, pane_id: str) -> bool:
        """Close specified pane"""
        if tab_id not in self._tabs or pane_id not in self._panes:
            return False

        tab = self._tabs[tab_id]

        # Don't close if it's the only pane
        if len(tab.panes) <= 1:
            return False

        # Remove pane from tab
        tab.panes = [p for p in tab.panes if p.id != pane_id]
        del self._panes[pane_id]

        # Update active pane if necessary
        if tab.active_pane_id == pane_id:
            tab.active_pane_id = tab.panes[0].id if tab.panes else None
            if tab.panes:
                tab.panes[0].is_active = True

        await self._emit_event(
            "pane_closed", {"tabId": tab_id, "paneId": pane_id, "tab": tab.to_dict()}
        )

        log.info(f"Closed pane {pane_id} in tab {tab_id}")
        return True

    # UI State Management

    async def update_ui_state(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update UI state and sync to all clients"""
        self._ui_state.update_from_dict(updates)

        ui_state_dict = self._ui_state.to_dict()

        await self._emit_event("ui_state_updated", {"uiState": ui_state_dict, "updates": updates})

        log.debug(f"Updated UI state: {updates}")
        return ui_state_dict

    # Data Access

    def get_tab(self, tab_id: str) -> Optional[TerminalTab]:
        """Get tab by ID"""
        return self._tabs.get(tab_id)

    def get_pane(self, pane_id: str) -> Optional[TerminalPane]:
        """Get pane by ID"""
        return self._panes.get(pane_id)

    def get_all_tabs(self) -> List[TerminalTab]:
        """Get all tabs"""
        return list(self._tabs.values())

    def get_ui_state(self) -> Dict[str, Any]:
        """Get current UI state"""
        return self._ui_state.to_dict()

    async def get_statistics(self) -> Dict[str, Any]:
        """Get workspace statistics"""
        total_panes = sum(len(tab.panes) for tab in self._tabs.values())

        return {
            "total_tabs": len(self._tabs),
            "total_panes": total_panes,
            "connected_clients": len(self._connected_clients),
            "active_tab": self._ui_state.active_tab_id,
            "last_updated": self._ui_state.last_updated.isoformat(),
        }


# Global workspace manager instance
_workspace_manager: Optional[WorkspaceManager] = None


def get_workspace_manager() -> WorkspaceManager:
    """Get global workspace manager instance"""
    global _workspace_manager
    if _workspace_manager is None:
        log.info("🔧 Creating new WorkspaceManager instance")
        _workspace_manager = WorkspaceManager()
        log.info(f"✅ WorkspaceManager created with {len(_workspace_manager._tabs)} tabs")
    else:
        log.debug(f"📋 Using existing WorkspaceManager with {len(_workspace_manager._tabs)} tabs")
    return _workspace_manager
