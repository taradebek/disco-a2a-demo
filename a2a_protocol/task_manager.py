import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from shared.models import Task, TaskStatus, AgentEvent
from .event_broadcaster import event_broadcaster

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.task_history: List[Task] = []
        self.task_dependencies: Dict[str, List[str]] = {}  # task_id -> list of dependent task_ids
    
    async def create_task(self, 
                         name: str, 
                         description: str, 
                         assigned_agent: Optional[str] = None,
                         data: Dict[str, Any] = None,
                         parent_task_id: Optional[str] = None) -> Task:
        """Create a new task with optional parent relationship"""
        task_id = str(uuid.uuid4())
        
        task = Task(
            task_id=task_id,
            name=name,
            description=description,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_agent=assigned_agent,
            data=data or {}
        )
        
        self.tasks[task_id] = task
        
        # Handle parent-child relationship
        if parent_task_id and parent_task_id in self.tasks:
            if parent_task_id not in self.task_dependencies:
                self.task_dependencies[parent_task_id] = []
            self.task_dependencies[parent_task_id].append(task_id)
            task.data['parent_task_id'] = parent_task_id
        
        await event_broadcaster.broadcast_event({
            "agent_id": assigned_agent or "system",
            "event_type": "task_created",
            "timestamp": datetime.now(),
            "data": {
                "task_id": task_id,
                "task_name": name,
                "assigned_agent": assigned_agent,
                "parent_task_id": parent_task_id
            },
            "step_number": 0,
            "description": f"Task '{name}' created with ID: {task_id}",
            "success": True
        })
        
        return task
    
    async def update_task_status(self, 
                                task_id: str, 
                                status: TaskStatus, 
                                data: Dict[str, Any] = None,
                                result: Dict[str, Any] = None) -> bool:
        """Update task status and optionally add data/result"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        old_status = task.status
        task.status = status
        task.updated_at = datetime.now()
        
        if data:
            task.data.update(data)
        
        if result:
            task.result = result
        
        # Check if task is completed and trigger dependent tasks
        if status == TaskStatus.COMPLETED:
            await self._trigger_dependent_tasks(task_id)
        
        await event_broadcaster.broadcast_event({
            "agent_id": task.assigned_agent or "system",
            "event_type": "status_update",
            "timestamp": datetime.now(),
            "data": {
                "task_id": task_id,
                "old_status": old_status,
                "new_status": status,
                "data": data or {},
                "result": result or {}
            },
            "step_number": 0,
            "description": f"Task {task_id} status changed from {old_status} to {status}",
            "success": True
        })
        
        return True
    
    async def _trigger_dependent_tasks(self, parent_task_id: str):
        """Trigger dependent tasks when parent task completes"""
        if parent_task_id in self.task_dependencies:
            for dependent_task_id in self.task_dependencies[parent_task_id]:
                if dependent_task_id in self.tasks:
                    dependent_task = self.tasks[dependent_task_id]
                    if dependent_task.status == TaskStatus.PENDING:
                        await self.update_task_status(
                            dependent_task_id, 
                            TaskStatus.IN_PROGRESS,
                            {"triggered_by": parent_task_id}
                        )
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task by ID"""
        return self.tasks.get(task_id)
    
    async def get_agent_tasks(self, agent_id: str, status: Optional[TaskStatus] = None) -> List[Task]:
        """Get all tasks for a specific agent, optionally filtered by status"""
        tasks = [task for task in self.tasks.values() if task.assigned_agent == agent_id]
        
        if status:
            tasks = [task for task in tasks if task.status == status]
        
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)
    
    async def get_task_hierarchy(self, root_task_id: str) -> Dict[str, Any]:
        """Get the complete task hierarchy starting from a root task"""
        def build_hierarchy(task_id: str, visited: set = None) -> Dict[str, Any]:
            if visited is None:
                visited = set()
            
            if task_id in visited or task_id not in self.tasks:
                return None
            
            visited.add(task_id)
            task = self.tasks[task_id]
            
            hierarchy = {
                "task_id": task_id,
                "name": task.name,
                "description": task.description,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "assigned_agent": task.assigned_agent,
                "data": task.data,
                "result": task.result,
                "children": []
            }
            
            # Add child tasks
            if task_id in self.task_dependencies:
                for child_task_id in self.task_dependencies[task_id]:
                    child_hierarchy = build_hierarchy(child_task_id, visited.copy())
                    if child_hierarchy:
                        hierarchy["children"].append(child_hierarchy)
            
            return hierarchy
        
        return build_hierarchy(root_task_id)
    
    async def cancel_task(self, task_id: str, reason: str = "Cancelled by user") -> bool:
        """Cancel a task and all its dependent tasks"""
        if task_id not in self.tasks:
            return False
        
        # Cancel the main task
        await self.update_task_status(task_id, TaskStatus.CANCELLED, {"cancellation_reason": reason})
        
        # Cancel all dependent tasks recursively
        if task_id in self.task_dependencies:
            for dependent_task_id in self.task_dependencies[task_id]:
                await self.cancel_task(dependent_task_id, f"Cancelled due to parent task {task_id} cancellation")
        
        return True
    
    async def get_task_statistics(self) -> Dict[str, Any]:
        """Get statistics about all tasks"""
        total_tasks = len(self.tasks)
        status_counts = {}
        
        for task in self.tasks.values():
            status = task.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Calculate completion rate
        completed_tasks = status_counts.get(TaskStatus.COMPLETED, 0)
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "status_breakdown": status_counts,
            "completion_rate": round(completion_rate, 2),
            "active_tasks": status_counts.get(TaskStatus.IN_PROGRESS, 0),
            "pending_tasks": status_counts.get(TaskStatus.PENDING, 0)
        }

# Global task manager instance
task_manager = TaskManager()
