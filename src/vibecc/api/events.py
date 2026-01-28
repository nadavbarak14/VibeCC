"""Event manager for Server-Sent Events (SSE)."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class EventType(str, Enum):
    """Types of events that can be emitted."""

    PIPELINE_CREATED = "pipeline_created"
    PIPELINE_UPDATED = "pipeline_updated"
    PIPELINE_COMPLETED = "pipeline_completed"
    AUTOPILOT_STARTED = "autopilot_started"
    AUTOPILOT_STOPPED = "autopilot_stopped"
    LOG = "log"
    HEARTBEAT = "heartbeat"


@dataclass
class Event:
    """An event to be sent via SSE."""

    event_type: EventType
    data: dict[str, Any]
    project_id: str | None = None

    def to_sse(self) -> str:
        """Convert to SSE format."""
        return f"event: {self.event_type.value}\ndata: {json.dumps(self.data)}\n\n"


@dataclass
class Subscriber:
    """A subscriber to the event stream."""

    id: str
    queue: asyncio.Queue[Event]
    project_id: str | None = None  # None means subscribe to all projects

    @classmethod
    def create(cls, project_id: str | None = None) -> Subscriber:
        """Create a new subscriber."""
        return cls(id=str(uuid4()), queue=asyncio.Queue(), project_id=project_id)


@dataclass
class EventManager:
    """Manager for SSE events."""

    _subscribers: dict[str, Subscriber] = field(default_factory=dict)
    _heartbeat_interval: int = 30  # seconds

    def subscribe(self, project_id: str | None = None) -> Subscriber:
        """Subscribe a client to events.

        Args:
            project_id: Optional project ID to filter events. None means all projects.

        Returns:
            Subscriber instance for receiving events.
        """
        subscriber = Subscriber.create(project_id)
        self._subscribers[subscriber.id] = subscriber
        return subscriber

    def unsubscribe(self, subscriber_id: str) -> None:
        """Unsubscribe a client from events.

        Args:
            subscriber_id: ID of the subscriber to remove.
        """
        self._subscribers.pop(subscriber_id, None)

    async def emit(self, event: Event) -> None:
        """Emit an event to all matching subscribers.

        Args:
            event: Event to emit.
        """
        for subscriber in self._subscribers.values():
            # Check if subscriber should receive this event
            if subscriber.project_id is None or subscriber.project_id == event.project_id:
                await subscriber.queue.put(event)

    def emit_sync(self, event: Event) -> None:
        """Emit an event synchronously (for use in non-async contexts).

        Args:
            event: Event to emit.
        """
        for subscriber in self._subscribers.values():
            if subscriber.project_id is None or subscriber.project_id == event.project_id:
                subscriber.queue.put_nowait(event)

    @property
    def subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return len(self._subscribers)

    # Convenience methods for emitting specific event types

    def emit_pipeline_created(
        self,
        pipeline_id: str,
        project_id: str,
        ticket_id: str,
        state: str,
    ) -> None:
        """Emit a pipeline_created event."""
        event = Event(
            event_type=EventType.PIPELINE_CREATED,
            project_id=project_id,
            data={
                "pipeline_id": pipeline_id,
                "project_id": project_id,
                "ticket_id": ticket_id,
                "state": state,
            },
        )
        self.emit_sync(event)

    def emit_pipeline_updated(
        self,
        pipeline_id: str,
        project_id: str,
        state: str,
        previous_state: str,
    ) -> None:
        """Emit a pipeline_updated event."""
        event = Event(
            event_type=EventType.PIPELINE_UPDATED,
            project_id=project_id,
            data={
                "pipeline_id": pipeline_id,
                "state": state,
                "previous_state": previous_state,
            },
        )
        self.emit_sync(event)

    def emit_pipeline_completed(
        self,
        pipeline_id: str,
        project_id: str,
        final_state: str,
    ) -> None:
        """Emit a pipeline_completed event."""
        event = Event(
            event_type=EventType.PIPELINE_COMPLETED,
            project_id=project_id,
            data={
                "pipeline_id": pipeline_id,
                "final_state": final_state,
            },
        )
        self.emit_sync(event)

    def emit_autopilot_started(self, project_id: str) -> None:
        """Emit an autopilot_started event."""
        event = Event(
            event_type=EventType.AUTOPILOT_STARTED,
            project_id=project_id,
            data={"project_id": project_id},
        )
        self.emit_sync(event)

    def emit_autopilot_stopped(self, project_id: str, reason: str = "manual") -> None:
        """Emit an autopilot_stopped event."""
        event = Event(
            event_type=EventType.AUTOPILOT_STOPPED,
            project_id=project_id,
            data={"project_id": project_id, "reason": reason},
        )
        self.emit_sync(event)

    def emit_log(
        self,
        pipeline_id: str,
        project_id: str,
        level: str,
        message: str,
    ) -> None:
        """Emit a log event."""
        event = Event(
            event_type=EventType.LOG,
            project_id=project_id,
            data={
                "pipeline_id": pipeline_id,
                "level": level,
                "message": message,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        )
        self.emit_sync(event)

    def create_heartbeat_event(self) -> Event:
        """Create a heartbeat event."""
        return Event(
            event_type=EventType.HEARTBEAT,
            project_id=None,  # Heartbeat goes to all subscribers
            data={"timestamp": datetime.utcnow().isoformat() + "Z"},
        )
