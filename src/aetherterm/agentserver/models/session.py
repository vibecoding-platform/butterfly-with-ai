"""
Session management models for multi-session support
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from uuid import uuid4


class UserPermission(Enum):
    """User permissions within a session"""

    OWNER = "owner"
    COLLABORATOR = "collaborator"
    OBSERVER = "observer"


class TabType(Enum):
    """Types of tabs in a session"""

    TERMINAL = "terminal"
    AI_ASSISTANT = "ai_assistant"


class MessageType(Enum):
    """Types of session messages"""

    TEXT = "text"
    COMMAND = "command"
    FILE = "file"
    NOTIFICATION = "notification"


@dataclass
class User:
    """User information"""

    id: str
    name: str
    remote_addr: str
    joined_at: datetime
    permission: UserPermission

    @classmethod
    def create(
        cls,
        user_id: str,
        name: str,
        remote_addr: str,
        permission: UserPermission = UserPermission.OBSERVER,
    ):
        return cls(
            id=user_id,
            name=name,
            remote_addr=remote_addr,
            joined_at=datetime.now(),
            permission=permission,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "remote_addr": self.remote_addr,
            "joined_at": self.joined_at.isoformat(),
            "permission": self.permission.value,
        }


@dataclass
class TerminalPane:
    """Terminal pane within a tab"""

    id: str
    terminal_id: str
    title: str
    shell_type: str = "bash"
    working_directory: str = "~"
    position: Dict[str, float] = field(
        default_factory=lambda: {"x": 0, "y": 0, "width": 100, "height": 100}
    )
    is_active: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(cls, title: str, shell_type: str = "bash", working_directory: str = "~"):
        return cls(
            id=f"pane-{uuid4().hex[:11]}",
            terminal_id=f"term-{uuid4().hex[:11]}",
            title=title,
            shell_type=shell_type,
            working_directory=working_directory,
            is_active=True,
        )


@dataclass
class BaseTab:
    """Base tab class"""

    id: str
    title: str
    type: TabType
    is_active: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed_at: datetime = field(default_factory=datetime.now)


@dataclass
class TerminalTab(BaseTab):
    """Terminal tab with multiple panes"""

    panes: List[TerminalPane] = field(default_factory=list)
    active_pane_id: Optional[str] = None
    layout: str = "horizontal"  # horizontal, vertical, grid, custom
    is_shared: bool = True
    connected_users: List[User] = field(default_factory=list)

    @classmethod
    def create(cls, title: str):
        tab_id = f"terminal-{uuid4().hex[:11]}"
        default_pane = TerminalPane.create("Main")

        return cls(
            id=tab_id,
            title=title,
            type=TabType.TERMINAL,
            panes=[default_pane],
            active_pane_id=default_pane.id,
            is_active=True,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert terminal tab to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type.value,
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat(),
            "lastAccessedAt": self.last_accessed_at.isoformat(),
            "panes": [
                {
                    "id": pane.id,
                    "terminalId": pane.terminal_id,
                    "title": pane.title,
                    "shellType": pane.shell_type,
                    "workingDirectory": pane.working_directory,
                    "position": pane.position,
                    "isActive": pane.is_active,
                    "createdAt": pane.created_at.isoformat(),
                    "lastAccessedAt": pane.last_accessed_at.isoformat(),
                }
                for pane in self.panes
            ],
            "activePaneId": self.active_pane_id,
            "layout": self.layout,
            "isShared": self.is_shared,
            "connectedUsers": [user.to_dict() for user in self.connected_users],
        }


@dataclass
class AIAssistantTab(BaseTab):
    """AI Assistant tab"""

    assistant_type: str = "general"  # code, operations, general
    context_session_id: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(
        cls, title: str, assistant_type: str = "general", context_session_id: Optional[str] = None
    ):
        return cls(
            id=f"ai-{uuid4().hex[:11]}",
            title=title,
            type=TabType.AI_ASSISTANT,
            assistant_type=assistant_type,
            context_session_id=context_session_id,
            is_active=True,
        )


@dataclass
class SessionSettings:
    """Session configuration settings"""

    allow_observers: bool = True
    allow_collaborators: bool = True
    require_approval_for_join: bool = False
    auto_close_on_owner_disconnect: bool = True
    session_timeout: int = 60  # minutes


@dataclass
class SessionMessage:
    """Inter-session communication message"""

    id: str
    session_id: str
    from_user_id: str
    from_user_name: str
    type: MessageType
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        session_id: str,
        user: User,
        message_type: MessageType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        return cls(
            id=f"msg-{uuid4().hex[:11]}",
            session_id=session_id,
            from_user_id=user.id,
            from_user_name=user.name,
            type=message_type,
            content=content,
            metadata=metadata,
        )


@dataclass
class Session:
    """Multi-session container"""

    id: str
    name: str
    description: str = ""
    is_active: bool = True
    owner: User = field(
        default_factory=lambda: User("", "", "", datetime.now(), UserPermission.OWNER)
    )
    connected_users: List[User] = field(default_factory=list)
    tabs: List[BaseTab] = field(default_factory=list)
    active_tab_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed_at: datetime = field(default_factory=datetime.now)
    is_shared: bool = True
    max_users: int = 10
    settings: SessionSettings = field(default_factory=SessionSettings)

    @classmethod
    def create(
        cls,
        name: str,
        owner: User,
        description: str = "",
        settings: Optional[SessionSettings] = None,
    ):
        session_id = f"session-{uuid4().hex[:11]}"
        default_tab = TerminalTab.create("Terminal 1")

        return cls(
            id=session_id,
            name=name,
            description=description,
            owner=owner,
            connected_users=[owner],
            tabs=[default_tab],
            active_tab_id=default_tab.id,
            settings=settings or SessionSettings(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "isActive": self.is_active,
            "owner": {
                "id": self.owner.id,
                "name": self.owner.name,
                "remoteAddr": self.owner.remote_addr,
                "joinedAt": self.owner.joined_at.isoformat(),
                "permission": self.owner.permission.value,
            },
            "connectedUsers": [
                {
                    "id": user.id,
                    "name": user.name,
                    "remoteAddr": user.remote_addr,
                    "joinedAt": user.joined_at.isoformat(),
                    "permission": user.permission.value,
                }
                for user in self.connected_users
            ],
            "tabs": [self._tab_to_dict(tab) for tab in self.tabs],
            "activeTabId": self.active_tab_id,
            "createdAt": self.created_at.isoformat(),
            "lastAccessedAt": self.last_accessed_at.isoformat(),
            "isShared": self.is_shared,
            "maxUsers": self.max_users,
            "settings": {
                "allowObservers": self.settings.allow_observers,
                "allowCollaborators": self.settings.allow_collaborators,
                "requireApprovalForJoin": self.settings.require_approval_for_join,
                "autoCloseOnOwnerDisconnect": self.settings.auto_close_on_owner_disconnect,
                "sessionTimeout": self.settings.session_timeout,
            },
        }

    def _tab_to_dict(self, tab: BaseTab) -> Dict[str, Any]:
        """Convert tab to dictionary"""
        base_dict = {
            "id": tab.id,
            "title": tab.title,
            "type": tab.type.value,
            "isActive": tab.is_active,
            "createdAt": tab.created_at.isoformat(),
            "lastAccessedAt": tab.last_accessed_at.isoformat(),
        }

        if isinstance(tab, TerminalTab):
            base_dict.update(
                {
                    "panes": [
                        {
                            "id": pane.id,
                            "terminalId": pane.terminal_id,
                            "title": pane.title,
                            "shellType": pane.shell_type,
                            "workingDirectory": pane.working_directory,
                            "position": pane.position,
                            "isActive": pane.is_active,
                            "createdAt": pane.created_at.isoformat(),
                            "lastAccessedAt": pane.last_accessed_at.isoformat(),
                        }
                        for pane in tab.panes
                    ],
                    "activePaneId": tab.active_pane_id,
                    "layout": tab.layout,
                    "isShared": tab.is_shared,
                    "connectedUsers": [
                        {
                            "id": user.id,
                            "name": user.name,
                            "remoteAddr": user.remote_addr,
                            "joinedAt": user.joined_at.isoformat(),
                            "permission": user.permission.value,
                        }
                        for user in tab.connected_users
                    ],
                }
            )
        elif isinstance(tab, AIAssistantTab):
            base_dict.update(
                {
                    "assistantType": tab.assistant_type,
                    "contextSessionId": tab.context_session_id,
                    "conversationHistory": tab.conversation_history,
                }
            )

        return base_dict

    def add_user(self, user: User) -> bool:
        """Add user to session"""
        if len(self.connected_users) >= self.max_users:
            return False

        # Check if user already exists
        if any(u.id == user.id for u in self.connected_users):
            return True

        self.connected_users.append(user)
        self.last_accessed_at = datetime.now()
        return True

    def remove_user(self, user_id: str) -> bool:
        """Remove user from session"""
        for i, user in enumerate(self.connected_users):
            if user.id == user_id:
                self.connected_users.pop(i)
                return True
        return False

    def add_tab(self, tab: BaseTab) -> None:
        """Add tab to session"""
        self.tabs.append(tab)
        if not self.active_tab_id:
            self.active_tab_id = tab.id
        self.last_accessed_at = datetime.now()

    def remove_tab(self, tab_id: str) -> bool:
        """Remove tab from session"""
        for i, tab in enumerate(self.tabs):
            if tab.id == tab_id:
                self.tabs.pop(i)
                if self.active_tab_id == tab_id:
                    self.active_tab_id = self.tabs[0].id if self.tabs else None
                return True
        return False

    def get_tab(self, tab_id: str) -> Optional[BaseTab]:
        """Get tab by ID"""
        for tab in self.tabs:
            if tab.id == tab_id:
                return tab
        return None

    def switch_tab(self, tab_id: str) -> bool:
        """Switch active tab"""
        if self.get_tab(tab_id):
            self.active_tab_id = tab_id
            self.last_accessed_at = datetime.now()
            return True
        return False
