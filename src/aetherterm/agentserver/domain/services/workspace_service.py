"""
Workspace Management Service - Application Layer

Handles workspace and terminal lifecycle operations.
"""

import logging
from typing import Any, Dict, List
from uuid import uuid4

from aetherterm.agentserver.domain.entities.terminals.asyncio_terminal import AsyncioTerminal

log = logging.getLogger("aetherterm.application.workspace")


class WorkspaceService:
    """Manages workspace and terminal lifecycle operations."""

    def __init__(self):
        self.session_owners: Dict[str, str] = {}  # session_id -> client_sid
        self.client_sids: Dict[str, List[str]] = {}  # client_sid -> session_ids

    async def create_terminal(
        self,
        client_sid: str,
        session_id: str,
        tab_id: str,
        pane_id: str,
        sub_type: str = "terminal",
        pane_type: str = "terminal",
        cols: int = 80,
        rows: int = 24,
        user: str = "",
        path: str = "",
    ) -> Dict[str, Any]:
        """Create a new terminal session."""
        try:
            log.info(f"Creating terminal session {session_id} for client {client_sid}")

            terminal = AsyncioTerminal(
                session_id=session_id, cols=cols, rows=rows, user=user, path=path
            )

            terminal.client_sids.add(client_sid)

            # Track session ownership
            self.session_owners[session_id] = client_sid
            if client_sid not in self.client_sids:
                self.client_sids[client_sid] = []
            self.client_sids[client_sid].append(session_id)

            await terminal.start()

            return {
                "status": "success",
                "session_id": session_id,
                "tab_id": tab_id,
                "pane_id": pane_id,
                "type": pane_type,
                "sub_type": sub_type,
                "cols": cols,
                "rows": rows,
            }

        except Exception as e:
            log.error(f"Failed to create terminal {session_id}: {e}")
            return {"status": "error", "error": str(e), "session_id": session_id}

    async def resume_workspace(
        self, client_sid: str, workspace_id: str, tabs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Resume a workspace with multiple tabs and panes."""
        try:
            log.info(f"Resuming workspace {workspace_id} for client {client_sid}")

            resumed_tabs = []
            created_tabs = []

            for tab in tabs:
                tab_id = tab.get("tabId")
                tab_title = tab.get("title", f"Tab {tab_id}")
                tab_layout = tab.get("layout", {})
                panes = tab.get("panes", [])

                resumed_panes = []
                created_panes = []

                for pane in panes:
                    pane_result = await self._process_pane(client_sid, tab_id, pane)

                    if pane_result["status"] == "resumed":
                        resumed_panes.append(pane_result)
                    else:
                        created_panes.append(pane_result)

                if resumed_panes:
                    resumed_tabs.append(
                        {
                            "tabId": tab_id,
                            "title": tab_title,
                            "layout": tab_layout,
                            "panes": resumed_panes,
                            "status": "resumed",
                        }
                    )

                if created_panes:
                    created_tabs.append(
                        {
                            "tabId": tab_id,
                            "title": tab_title,
                            "layout": tab_layout,
                            "panes": created_panes,
                            "status": "created",
                        }
                    )

            return {
                "workspaceId": workspace_id,
                "status": "success",
                "resumedTabs": resumed_tabs,
                "createdTabs": created_tabs,
                "totalTabs": len(tabs),
                "totalPanes": sum(len(tab.get("panes", [])) for tab in resumed_tabs + created_tabs),
                "message": f"Workspace resumed with {len(resumed_tabs)} existing and {len(created_tabs)} new tab configurations",
            }

        except Exception as e:
            log.error(f"Failed to resume workspace {workspace_id}: {e}")
            return {"workspaceId": workspace_id, "status": "error", "error": str(e)}

    async def _process_pane(
        self, client_sid: str, tab_id: str, pane: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process individual pane - resume or create new."""
        pane_id = pane.get("paneId")
        session_id = pane.get("sessionId")
        pane_type = pane.get("type", "terminal")
        sub_type = pane.get("subType", "terminal")
        pane_title = pane.get("title", f"Pane {pane_id}")
        position = pane.get("position", {})

        # Check if session exists and is active
        if session_id and session_id in AsyncioTerminal.sessions:
            existing_terminal = AsyncioTerminal.sessions[session_id]
            if not existing_terminal.closed:
                log.info(f"Resuming existing terminal session {session_id} for pane {pane_id}")
                existing_terminal.client_sids.add(client_sid)

                return {
                    "paneId": pane_id,
                    "sessionId": session_id,
                    "status": "resumed",
                    "type": pane_type,
                    "subType": sub_type,
                    "title": pane_title,
                    "position": position,
                    "history": existing_terminal.history,
                }

        # Create new terminal session
        new_session_id = session_id or f"terminal_{pane_id}_{uuid4().hex[:8]}"

        result = await self.create_terminal(
            client_sid=client_sid,
            session_id=new_session_id,
            tab_id=tab_id,
            pane_id=pane_id,
            sub_type=sub_type,
            pane_type=pane_type,
            cols=80,
            rows=24,
        )

        return {
            "paneId": pane_id,
            "sessionId": new_session_id,
            "status": "created",
            "type": pane_type,
            "subType": sub_type,
            "title": pane_title,
            "position": position,
        }

    async def terminal_input(self, session_id: str, data: str) -> bool:
        """Send input to terminal session."""
        try:
            if session_id in AsyncioTerminal.sessions:
                terminal = AsyncioTerminal.sessions[session_id]
                if not terminal.closed:
                    await terminal.write(data)
                    return True
            return False
        except Exception as e:
            log.error(f"Failed to send input to terminal {session_id}: {e}")
            return False

    async def terminal_resize(self, session_id: str, cols: int, rows: int) -> bool:
        """Resize terminal session."""
        try:
            if session_id in AsyncioTerminal.sessions:
                terminal = AsyncioTerminal.sessions[session_id]
                if not terminal.closed:
                    await terminal.resize(cols, rows)
                    return True
            return False
        except Exception as e:
            log.error(f"Failed to resize terminal {session_id}: {e}")
            return False

    def cleanup_client_sessions(self, client_sid: str):
        """Clean up sessions when client disconnects."""
        if client_sid in self.client_sids:
            session_ids = self.client_sids[client_sid]
            for session_id in session_ids:
                if session_id in self.session_owners:
                    del self.session_owners[session_id]
                if session_id in AsyncioTerminal.sessions:
                    terminal = AsyncioTerminal.sessions[session_id]
                    terminal.client_sids.discard(client_sid)
            del self.client_sids[client_sid]
