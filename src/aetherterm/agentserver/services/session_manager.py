"""
Session Management Service for AgentServer
Handles multi-session lifecycle, state management, and coordination
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from collections import defaultdict

from aetherterm.agentserver.models.session import (
    Session,
    User,
    BaseTab,
    TerminalTab,
    AIAssistantTab,
    TerminalPane,
    SessionSettings,
    SessionMessage,
    UserPermission,
    TabType,
    MessageType,
)

log = logging.getLogger(__name__)


class SessionManager:
    """
    Central session management service
    - Manages session lifecycle (create, update, delete)
    - Handles user permissions and access control
    - Coordinates tab and pane operations
    - Manages inter-session communication
    - Provides auto-creation logic for external integrations
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, Set[str]] = defaultdict(set)  # user_id -> session_ids
        self._session_messages: Dict[str, List[SessionMessage]] = defaultdict(list)
        self._event_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._auto_cleanup_task: Optional[asyncio.Task] = None

        # Start background cleanup task
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start background task for session cleanup"""

        async def cleanup_sessions():
            while True:
                try:
                    await asyncio.sleep(60)  # Check every minute
                    await self._cleanup_expired_sessions()
                except Exception as e:
                    log.error(f"Error in session cleanup task: {e}")

        self._auto_cleanup_task = asyncio.create_task(cleanup_sessions())

    async def _cleanup_expired_sessions(self):
        """Clean up expired or inactive sessions"""
        current_time = datetime.now()
        expired_sessions = []

        for session_id, session in self._sessions.items():
            # Check if session has expired
            if session.settings.session_timeout > 0:
                timeout_minutes = session.settings.session_timeout
                if current_time - session.last_accessed_at > timedelta(minutes=timeout_minutes):
                    # Check if session should auto-close
                    if session.settings.auto_close_on_owner_disconnect:
                        owner_connected = any(
                            u.id == session.owner.id for u in session.connected_users
                        )
                        if not owner_connected:
                            expired_sessions.append(session_id)
                    elif not session.connected_users:  # No users connected
                        expired_sessions.append(session_id)

        # Clean up expired sessions
        for session_id in expired_sessions:
            log.info(f"Auto-cleaning expired session: {session_id}")
            await self.delete_session(session_id, reason="expired")

    def on_event(self, event_type: str, callback: Callable):
        """Register event callback"""
        self._event_callbacks[event_type].append(callback)

    async def _emit_event(self, event_type: str, data: Any):
        """Emit event to registered callbacks"""
        for callback in self._event_callbacks[event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                log.error(f"Error in event callback {event_type}: {e}")

    # Session lifecycle methods

    async def create_session(
        self,
        name: str,
        owner: User,
        description: str = "",
        settings: Optional[SessionSettings] = None,
        auto_created: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """Create a new session"""
        session = Session.create(name, owner, description, settings)

        self._sessions[session.id] = session
        self._user_sessions[owner.id].add(session.id)

        log.info(f"Session created: {session.id} by {owner.name} (auto: {auto_created})")

        # Emit session created event
        await self._emit_event(
            "session_created",
            {"session": session, "auto_created": auto_created, "metadata": metadata},
        )

        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self._sessions.get(session_id)

    async def list_sessions(self, user_id: Optional[str] = None) -> List[Session]:
        """List sessions, optionally filtered by user"""
        if user_id:
            session_ids = self._user_sessions.get(user_id, set())
            return [self._sessions[sid] for sid in session_ids if sid in self._sessions]
        return list(self._sessions.values())

    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session properties"""
        session = self._sessions.get(session_id)
        if not session:
            return False

        # Apply updates
        if "name" in updates:
            session.name = updates["name"]
        if "description" in updates:
            session.description = updates["description"]
        if "settings" in updates:
            # Update settings
            settings_data = updates["settings"]
            for key, value in settings_data.items():
                if hasattr(session.settings, key):
                    setattr(session.settings, key, value)

        session.last_accessed_at = datetime.now()

        # Emit session updated event
        await self._emit_event(
            "session_updated", {"session_id": session_id, "session": session, "updates": updates}
        )

        return True

    async def delete_session(self, session_id: str, reason: str = "manual") -> bool:
        """Delete session and clean up resources"""
        session = self._sessions.get(session_id)
        if not session:
            return False

        # Remove from user mappings
        for user in session.connected_users:
            self._user_sessions[user.id].discard(session_id)

        # Clean up messages
        if session_id in self._session_messages:
            del self._session_messages[session_id]

        # Remove session
        del self._sessions[session_id]

        log.info(f"Session deleted: {session_id} (reason: {reason})")

        # Emit session deleted event
        await self._emit_event(
            "session_deleted", {"session_id": session_id, "session": session, "reason": reason}
        )

        return True

    # User management methods

    async def join_session(
        self, session_id: str, user: User, permission: Optional[UserPermission] = None
    ) -> bool:
        """Add user to session"""
        session = self._sessions.get(session_id)
        if not session:
            return False

        # Check permissions
        if not session.settings.allow_observers and permission == UserPermission.OBSERVER:
            return False
        if not session.settings.allow_collaborators and permission == UserPermission.COLLABORATOR:
            return False

        # Set default permission
        if permission is None:
            permission = UserPermission.OBSERVER

        user.permission = permission

        # Add user to session
        if session.add_user(user):
            self._user_sessions[user.id].add(session_id)

            log.info(f"User {user.name} joined session {session_id} as {permission.value}")

            # Emit user joined event
            await self._emit_event(
                "user_joined", {"session_id": session_id, "user": user, "session": session}
            )

            return True

        return False

    async def leave_session(self, session_id: str, user_id: str) -> bool:
        """Remove user from session"""
        session = self._sessions.get(session_id)
        if not session:
            return False

        if session.remove_user(user_id):
            self._user_sessions[user_id].discard(session_id)

            log.info(f"User {user_id} left session {session_id}")

            # Emit user left event
            await self._emit_event(
                "user_left", {"session_id": session_id, "user_id": user_id, "session": session}
            )

            # Auto-delete session if no users and owner left
            if not session.connected_users:
                await self.delete_session(session_id, reason="empty")

            return True

        return False

    # Tab management methods

    async def create_tab(
        self, session_id: str, tab_type: TabType, title: str, user_id: str, **kwargs
    ) -> Optional[BaseTab]:
        """Create new tab in session"""
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Check user permissions
        if not self._check_user_permission(session, user_id, "create_tab"):
            return None

        # Create appropriate tab type
        if tab_type == TabType.TERMINAL:
            tab = TerminalTab.create(title)
        elif tab_type == TabType.AI_ASSISTANT:
            assistant_type = kwargs.get("assistant_type", "general")
            context_session_id = kwargs.get("context_session_id")
            tab = AIAssistantTab.create(title, assistant_type, context_session_id)
        else:
            return None

        session.add_tab(tab)

        log.info(f"Tab created: {tab.id} in session {session_id}")

        # Emit tab created event
        await self._emit_event(
            "tab_created", {"session_id": session_id, "tab": tab, "session": session}
        )

        return tab

    async def delete_tab(self, session_id: str, tab_id: str, user_id: str) -> bool:
        """Delete tab from session"""
        session = self._sessions.get(session_id)
        if not session:
            return False

        # Check user permissions
        if not self._check_user_permission(session, user_id, "delete_tab"):
            return False

        # Don't allow deleting the last tab
        if len(session.tabs) <= 1:
            return False

        if session.remove_tab(tab_id):
            log.info(f"Tab deleted: {tab_id} from session {session_id}")

            # Emit tab deleted event
            await self._emit_event(
                "tab_deleted", {"session_id": session_id, "tab_id": tab_id, "session": session}
            )

            return True

        return False

    async def switch_tab(self, session_id: str, tab_id: str, user_id: str) -> bool:
        """Switch active tab in session"""
        session = self._sessions.get(session_id)
        if not session:
            return False

        if session.switch_tab(tab_id):
            # Emit tab switched event
            await self._emit_event(
                "tab_switched",
                {
                    "session_id": session_id,
                    "tab_id": tab_id,
                    "user_id": user_id,
                    "session": session,
                },
            )

            return True

        return False

    # Pane management methods (for terminal tabs)

    async def split_pane(
        self, session_id: str, tab_id: str, pane_id: str, direction: str, user_id: str
    ) -> Optional[TerminalPane]:
        """Split pane in terminal tab"""
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Check user permissions
        if not self._check_user_permission(session, user_id, "split_pane"):
            return None

        tab = session.get_tab(tab_id)
        if not isinstance(tab, TerminalTab):
            return None

        # Find source pane
        source_pane = None
        for pane in tab.panes:
            if pane.id == pane_id:
                source_pane = pane
                break

        if not source_pane:
            return None

        # Create new pane
        new_pane = TerminalPane.create(f"Split {len(tab.panes) + 1}")

        # Calculate positions based on direction
        if direction == "horizontal":
            source_pane.position["width"] = 50
            new_pane.position = {
                "x": 50,
                "y": source_pane.position["y"],
                "width": 50,
                "height": source_pane.position["height"],
            }
            tab.layout = "horizontal"
        elif direction == "vertical":
            source_pane.position["height"] = 50
            new_pane.position = {
                "x": source_pane.position["x"],
                "y": 50,
                "width": source_pane.position["width"],
                "height": 50,
            }
            tab.layout = "vertical"

        tab.panes.append(new_pane)
        tab.active_pane_id = new_pane.id

        log.info(f"Pane split: {new_pane.id} in tab {tab_id}")

        # Emit pane created event
        await self._emit_event(
            "pane_created",
            {
                "session_id": session_id,
                "tab_id": tab_id,
                "pane": new_pane,
                "direction": direction,
                "session": session,
            },
        )

        return new_pane

    async def close_pane(self, session_id: str, tab_id: str, pane_id: str, user_id: str) -> bool:
        """Close pane in terminal tab"""
        session = self._sessions.get(session_id)
        if not session:
            return False

        # Check user permissions
        if not self._check_user_permission(session, user_id, "close_pane"):
            return False

        tab = session.get_tab(tab_id)
        if not isinstance(tab, TerminalTab):
            return False

        # Don't allow closing the last pane
        if len(tab.panes) <= 1:
            return False

        # Remove pane
        for i, pane in enumerate(tab.panes):
            if pane.id == pane_id:
                tab.panes.pop(i)
                # Switch to another pane if this was active
                if tab.active_pane_id == pane_id:
                    tab.active_pane_id = tab.panes[0].id if tab.panes else None

                log.info(f"Pane closed: {pane_id} in tab {tab_id}")

                # Emit pane deleted event
                await self._emit_event(
                    "pane_deleted",
                    {
                        "session_id": session_id,
                        "tab_id": tab_id,
                        "pane_id": pane_id,
                        "session": session,
                    },
                )

                return True

        return False

    # Communication methods

    async def send_message(self, message: SessionMessage) -> bool:
        """Send message to session"""
        if message.session_id not in self._sessions:
            return False

        self._session_messages[message.session_id].append(message)

        # Emit message event
        await self._emit_event(
            "message_sent", {"message": message, "session": self._sessions[message.session_id]}
        )

        return True

    async def get_messages(self, session_id: str, limit: int = 100) -> List[SessionMessage]:
        """Get recent messages for session"""
        messages = self._session_messages.get(session_id, [])
        return messages[-limit:] if limit > 0 else messages

    # Auto-creation methods (for external integrations)

    async def auto_create_session_for_shell(
        self, shell_pid: int, shell_type: str = "bash", user_info: Optional[Dict[str, str]] = None
    ) -> Session:
        """Auto-create session when AgentShell connects"""
        # Create user for shell
        user = User.create(
            user_id=f"shell-{shell_pid}",
            name=user_info.get("name", f"Shell User {shell_pid}"),
            remote_addr=user_info.get("remote_addr", "localhost"),
            permission=UserPermission.OWNER,
        )

        # Create session
        session = await self.create_session(
            name=f"Shell Session {shell_pid}",
            owner=user,
            description=f"Auto-created for {shell_type} shell (PID: {shell_pid})",
            auto_created=True,
            metadata={"shell_pid": shell_pid, "shell_type": shell_type, "created_by": "agentshell"},
        )

        log.info(f"Auto-created session {session.id} for shell PID {shell_pid}")
        return session

    async def auto_create_session_for_ssh(
        self, ssh_connection_id: str, remote_user: str, remote_host: str
    ) -> Session:
        """Auto-create session for SSH connection"""
        # Create user for SSH connection
        user = User.create(
            user_id=f"ssh-{ssh_connection_id}",
            name=f"{remote_user}@{remote_host}",
            remote_addr=remote_host,
            permission=UserPermission.OWNER,
        )

        # Create session
        session = await self.create_session(
            name=f"SSH {remote_user}@{remote_host}",
            owner=user,
            description=f"Auto-created for SSH connection",
            auto_created=True,
            metadata={
                "ssh_connection_id": ssh_connection_id,
                "remote_user": remote_user,
                "remote_host": remote_host,
                "created_by": "ssh_integration",
            },
        )

        log.info(f"Auto-created session {session.id} for SSH {remote_user}@{remote_host}")
        return session

    # Utility methods

    def _check_user_permission(self, session: Session, user_id: str, action: str) -> bool:
        """Check if user has permission to perform action"""
        user = None
        for u in session.connected_users:
            if u.id == user_id:
                user = u
                break

        if not user:
            return False

        # Permission mapping
        permission_actions = {
            UserPermission.OWNER: [
                "create_tab",
                "delete_tab",
                "split_pane",
                "close_pane",
                "manage_users",
            ],
            UserPermission.COLLABORATOR: ["create_tab", "split_pane", "close_pane"],
            UserPermission.OBSERVER: [],
        }

        allowed_actions = permission_actions.get(user.permission, [])
        return action in allowed_actions

    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        total_sessions = len(self._sessions)
        total_users = len(self._user_sessions)
        total_tabs = sum(len(session.tabs) for session in self._sessions.values())
        total_panes = sum(
            len(tab.panes)
            for session in self._sessions.values()
            for tab in session.tabs
            if isinstance(tab, TerminalTab)
        )

        return {
            "total_sessions": total_sessions,
            "total_users": total_users,
            "total_tabs": total_tabs,
            "total_panes": total_panes,
            "active_sessions": len([s for s in self._sessions.values() if s.is_active]),
        }


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
