# src/aetherterm/agentserver/services/hierarchical_agent_manager.py

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentType(Enum):
    PARENT = "parent"
    CHILD = "child"

class AgentStatus(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    ERROR = "error"

@dataclass
class AgentSpec:
    agent_id: str
    agent_type: AgentType
    parent_id: Optional[str]
    specialization: str
    tools: List[str]
    terminal_id: Optional[str]
    capabilities: Dict[str, bool]
    status: AgentStatus = AgentStatus.IDLE
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class TaskAssignment:
    task_id: str
    parent_id: str
    target_agent: str
    task_type: str
    parameters: Dict[str, Any]
    priority: str
    dependencies: List[str]
    status: str = "pending"
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class HierarchicalAgentManager:
    def __init__(self):
        self.agents: Dict[str, AgentSpec] = {}
        self.hierarchies: Dict[str, List[str]] = {}  # parent_id -> [child_ids]
        self.task_assignments: Dict[str, TaskAssignment] = {}
        self.agent_communications: Dict[str, List[Dict[str, Any]]] = {}  # agent_id -> messages

    async def create_parent_agent(
        self, 
        task_type: str, 
        project_config: Dict[str, Any],
        child_specs: List[Dict[str, Any]]
    ) -> tuple[AgentSpec, List[AgentSpec]]:
        """Create parent agent and associated child agents"""
        
        # Create parent agent
        parent_id = f"parent-{uuid.uuid4().hex[:11]}"
        parent_agent = AgentSpec(
            agent_id=parent_id,
            agent_type=AgentType.PARENT,
            parent_id=None,
            specialization=f"{task_type}_coordinator",
            tools=["orchestration", "decision_making", "reporting"],
            terminal_id=None,
            capabilities={
                "taskDecomposition": True,
                "agentOrchestration": True,
                "decisionMaking": True,
                "errorRecovery": True,
                "progressReporting": True
            }
        )
        
        # Create child agents
        child_agents = []
        for child_spec in child_specs:
            child_id = f"child-{child_spec['type']}-{uuid.uuid4().hex[:8]}"
            terminal_id = f"terminal-{child_spec['type']}-{uuid.uuid4().hex[:8]}"
            
            # Define specialization-specific capabilities
            specialization_capabilities = self._get_specialization_capabilities(child_spec['type'])
            
            child_agent = AgentSpec(
                agent_id=child_id,
                agent_type=AgentType.CHILD,
                parent_id=parent_id,
                specialization=child_spec['type'],
                tools=child_spec.get('tools', []),
                terminal_id=terminal_id,
                capabilities={
                    **specialization_capabilities,
                    **child_spec.get('capabilities', {})
                }
            )
            child_agents.append(child_agent)
            
        # Store hierarchy
        self.agents[parent_id] = parent_agent
        child_ids = []
        for child in child_agents:
            self.agents[child.agent_id] = child
            child_ids.append(child.agent_id)
            # Initialize communication queue
            self.agent_communications[child.agent_id] = []
            
        self.hierarchies[parent_id] = child_ids
        self.agent_communications[parent_id] = []
        
        logger.info(f"Created hierarchical agent structure: parent {parent_id} with {len(child_agents)} children")
        
        return parent_agent, child_agents

    def _get_specialization_capabilities(self, specialization: str) -> Dict[str, bool]:
        """Get default capabilities for each specialization"""
        capabilities_map = {
            "build": {
                "codeCompilation": True,
                "dependencyManagement": True,
                "artifactGeneration": True,
                "buildOptimization": True
            },
            "test": {
                "testExecution": True,
                "coverageAnalysis": True,
                "performanceTesting": True,
                "testReportGeneration": True
            },
            "deploy": {
                "environmentManagement": True,
                "containerDeployment": True,
                "configurationManagement": True,
                "rollbackCapability": True
            },
            "monitor": {
                "realTimeMonitoring": True,
                "anomalyDetection": True,
                "alertGeneration": True,
                "performanceAnalysis": True,
                "logAnalysis": True
            },
            "operations": {
                "infrastructureManagement": True,
                "autoscaling": True,
                "emergencyResponse": True,
                "maintenanceAutomation": True
            }
        }
        return capabilities_map.get(specialization, {})
        
    async def distribute_tasks(
        self, 
        parent_id: str, 
        tasks: List[Dict[str, Any]]
    ) -> List[TaskAssignment]:
        """Distribute tasks from parent to child agents"""
        
        if parent_id not in self.agents:
            raise ValueError(f"Parent agent {parent_id} not found")
            
        task_assignments = []
        
        for task in tasks:
            task_id = f"task-{uuid.uuid4().hex[:11]}"
            target_agent = task['targetAgent']
            
            if target_agent not in self.agents:
                logger.warning(f"Target agent {target_agent} not found, skipping task")
                continue
                
            assignment = TaskAssignment(
                task_id=task_id,
                parent_id=parent_id,
                target_agent=target_agent,
                task_type=task.get('task', 'general'),
                parameters=task.get('parameters', {}),
                priority=task.get('priority', 'normal'),
                dependencies=task.get('dependencies', [])
            )
            
            self.task_assignments[task_id] = assignment
            task_assignments.append(assignment)
            
        logger.info(f"Distributed {len(task_assignments)} tasks from parent {parent_id}")
        return task_assignments
        
    async def update_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update agent status"""
        if agent_id not in self.agents:
            return False
            
        self.agents[agent_id].status = status
        
        # Store status update metadata
        if metadata:
            if agent_id not in self.agent_communications:
                self.agent_communications[agent_id] = []
            
            self.agent_communications[agent_id].append({
                "type": "status_update",
                "status": status.value,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            })
        
        logger.info(f"Updated agent {agent_id} status to {status.value}")
        return True

    async def agent_communicate(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        message: Dict[str, Any]
    ) -> bool:
        """Handle communication between agents"""
        
        if from_agent not in self.agents or to_agent not in self.agents:
            logger.error(f"Communication failed: invalid agent IDs {from_agent} -> {to_agent}")
            return False
        
        # Store message for recipient
        if to_agent not in self.agent_communications:
            self.agent_communications[to_agent] = []
            
        communication = {
            "type": "agent_message",
            "from": from_agent,
            "messageType": message_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        self.agent_communications[to_agent].append(communication)
        
        # Handle special communication types
        if message_type == "deployment_notification":
            await self._handle_deployment_notification(from_agent, to_agent, message)
        elif message_type == "monitoring_request":
            await self._handle_monitoring_request(from_agent, to_agent, message)
        elif message_type == "incident_alert":
            await self._handle_incident_alert(from_agent, to_agent, message)
            
        logger.info(f"Communication: {from_agent} -> {to_agent}: {message_type}")
        return True

    async def _handle_deployment_notification(
        self,
        from_agent: str,
        to_agent: str,
        message: Dict[str, Any]
    ):
        """Handle deployment notification from deploy agent to monitor agent"""
        if self.agents[to_agent].specialization == "monitor":
            # Auto-start monitoring for the deployed service
            await self.update_agent_status(
                to_agent, 
                AgentStatus.MONITORING,
                {
                    "monitoring_target": message.get("deploymentId"),
                    "endpoints": message.get("endpoints", []),
                    "auto_started": True
                }
            )

    async def _handle_monitoring_request(
        self,
        from_agent: str,
        to_agent: str,
        message: Dict[str, Any]
    ):
        """Handle monitoring request"""
        if self.agents[to_agent].specialization == "monitor":
            # Set up monitoring based on request
            await self.update_agent_status(
                to_agent,
                AgentStatus.MONITORING,
                {
                    "requested_by": from_agent,
                    "monitoring_config": message
                }
            )

    async def _handle_incident_alert(
        self,
        from_agent: str,
        to_agent: str,
        message: Dict[str, Any]
    ):
        """Handle incident alert from monitor to operations agent"""
        if self.agents[to_agent].specialization == "operations":
            # Trigger automated response
            await self.update_agent_status(
                to_agent,
                AgentStatus.EXECUTING,
                {
                    "incident": message,
                    "response_mode": "automated"
                }
            )

    async def get_hierarchy_status(self, parent_id: str) -> Dict[str, Any]:
        """Get status of entire agent hierarchy"""
        
        parent_agent = self.agents.get(parent_id)
        if not parent_agent:
            return {"error": "Parent agent not found"}
            
        child_ids = self.hierarchies.get(parent_id, [])
        child_statuses = []
        
        for child_id in child_ids:
            child_agent = self.agents.get(child_id)
            if child_agent:
                # Get recent communications
                recent_comms = self.agent_communications.get(child_id, [])[-5:]  # Last 5 messages
                
                child_status = {
                    "agentId": child_id,
                    "specialization": child_agent.specialization,
                    "terminalId": child_agent.terminal_id,
                    "status": child_agent.status.value,
                    "capabilities": child_agent.capabilities,
                    "tools": child_agent.tools,
                    "recentCommunications": len(recent_comms),
                    "lastActivity": recent_comms[-1]["timestamp"] if recent_comms else None
                }
                child_statuses.append(child_status)
                
        return {
            "parentAgent": {
                "agentId": parent_id,
                "specialization": parent_agent.specialization,
                "status": parent_agent.status.value,
                "childCount": len(child_ids),
                "capabilities": parent_agent.capabilities
            },
            "childAgents": child_statuses,
            "totalCommunications": sum(len(self.agent_communications.get(cid, [])) for cid in child_ids)
        }

    async def get_agent_communications(
        self,
        agent_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent communications for an agent"""
        if agent_id not in self.agent_communications:
            return []
        
        communications = self.agent_communications[agent_id]
        return communications[-limit:] if limit else communications

    async def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """Clean up old completed task assignments"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        completed_tasks = []
        for task_id, assignment in self.task_assignments.items():
            if (assignment.status == "completed" and 
                assignment.created_at.timestamp() < cutoff_time):
                completed_tasks.append(task_id)
        
        for task_id in completed_tasks:
            del self.task_assignments[task_id]
            
        logger.info(f"Cleaned up {len(completed_tasks)} completed tasks")

    async def get_parent_children_mapping(self) -> Dict[str, List[str]]:
        """Get mapping of parent agents to their children"""
        return self.hierarchies.copy()

    async def get_specialization_agents(self, specialization: str) -> List[AgentSpec]:
        """Get all agents with a specific specialization"""
        return [
            agent for agent in self.agents.values()
            if agent.specialization == specialization
        ]

# Global instance
_hierarchical_agent_manager_instance = None

def get_hierarchical_agent_manager() -> HierarchicalAgentManager:
    """Get global HierarchicalAgentManager instance"""
    global _hierarchical_agent_manager_instance
    if _hierarchical_agent_manager_instance is None:
        _hierarchical_agent_manager_instance = HierarchicalAgentManager()
    return _hierarchical_agent_manager_instance