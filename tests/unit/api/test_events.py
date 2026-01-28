"""Unit tests for EventManager and events."""

import asyncio
import json

import pytest

from vibecc.api.events import Event, EventManager, EventType


@pytest.fixture
def event_manager():
    """Create an EventManager instance."""
    return EventManager()


@pytest.mark.unit
class TestEventManagerSubscribe:
    """Tests for EventManager.subscribe."""

    def test_event_manager_subscribe(self, event_manager: EventManager) -> None:
        """Client can subscribe."""
        subscriber = event_manager.subscribe()

        assert subscriber.id is not None
        assert subscriber.queue is not None
        assert event_manager.subscriber_count == 1

    def test_event_manager_subscribe_with_project_filter(self, event_manager: EventManager) -> None:
        """Client can subscribe with project filter."""
        subscriber = event_manager.subscribe(project_id="project-123")

        assert subscriber.project_id == "project-123"
        assert event_manager.subscriber_count == 1


@pytest.mark.unit
class TestEventManagerUnsubscribe:
    """Tests for EventManager.unsubscribe."""

    def test_event_manager_unsubscribe(self, event_manager: EventManager) -> None:
        """Client can unsubscribe."""
        subscriber = event_manager.subscribe()
        assert event_manager.subscriber_count == 1

        event_manager.unsubscribe(subscriber.id)

        assert event_manager.subscriber_count == 0

    def test_event_manager_unsubscribe_nonexistent(self, event_manager: EventManager) -> None:
        """Unsubscribing nonexistent client doesn't fail."""
        event_manager.unsubscribe("nonexistent-id")

        assert event_manager.subscriber_count == 0


@pytest.mark.unit
class TestEventManagerEmit:
    """Tests for EventManager.emit."""

    @pytest.mark.asyncio
    async def test_event_manager_emit_to_all(self, event_manager: EventManager) -> None:
        """Event reaches all subscribers."""
        sub1 = event_manager.subscribe()
        sub2 = event_manager.subscribe()

        event = Event(
            event_type=EventType.PIPELINE_CREATED,
            project_id="project-123",
            data={"pipeline_id": "pipe-1"},
        )
        await event_manager.emit(event)

        # Both subscribers should receive the event
        event1 = await asyncio.wait_for(sub1.queue.get(), timeout=1.0)
        event2 = await asyncio.wait_for(sub2.queue.get(), timeout=1.0)

        assert event1.event_type == EventType.PIPELINE_CREATED
        assert event2.event_type == EventType.PIPELINE_CREATED

    @pytest.mark.asyncio
    async def test_event_manager_filter_by_project(self, event_manager: EventManager) -> None:
        """Only matching events sent to filtered subscribers."""
        sub_all = event_manager.subscribe()  # Receives all
        sub_filtered = event_manager.subscribe(project_id="project-123")

        # Emit event for project-123
        event1 = Event(
            event_type=EventType.PIPELINE_CREATED,
            project_id="project-123",
            data={"pipeline_id": "pipe-1"},
        )
        await event_manager.emit(event1)

        # Emit event for different project
        event2 = Event(
            event_type=EventType.PIPELINE_CREATED,
            project_id="project-456",
            data={"pipeline_id": "pipe-2"},
        )
        await event_manager.emit(event2)

        # sub_all should have both events
        received1 = await asyncio.wait_for(sub_all.queue.get(), timeout=1.0)
        received2 = await asyncio.wait_for(sub_all.queue.get(), timeout=1.0)
        assert received1.data["pipeline_id"] == "pipe-1"
        assert received2.data["pipeline_id"] == "pipe-2"

        # sub_filtered should only have the matching event
        received = await asyncio.wait_for(sub_filtered.queue.get(), timeout=1.0)
        assert received.data["pipeline_id"] == "pipe-1"

        # Queue should be empty now
        assert sub_filtered.queue.empty()

    def test_event_manager_no_subscribers(self, event_manager: EventManager) -> None:
        """Emit doesn't fail with no subscribers."""
        event = Event(
            event_type=EventType.PIPELINE_CREATED,
            project_id="project-123",
            data={"pipeline_id": "pipe-1"},
        )
        # Should not raise
        event_manager.emit_sync(event)


@pytest.mark.unit
class TestEventFormat:
    """Tests for event formatting."""

    def test_event_format_pipeline_created(self, event_manager: EventManager) -> None:
        """Correct event structure for pipeline_created."""
        sub = event_manager.subscribe()

        event_manager.emit_pipeline_created(
            pipeline_id="pipe-123",
            project_id="project-456",
            ticket_id="42",
            state="queued",
        )

        event = sub.queue.get_nowait()
        assert event.event_type == EventType.PIPELINE_CREATED
        assert event.data["pipeline_id"] == "pipe-123"
        assert event.data["project_id"] == "project-456"
        assert event.data["ticket_id"] == "42"
        assert event.data["state"] == "queued"

        # Check SSE format
        sse = event.to_sse()
        assert sse.startswith("event: pipeline_created\n")
        assert "data: " in sse
        data = json.loads(sse.split("data: ")[1].strip())
        assert data["pipeline_id"] == "pipe-123"

    def test_event_format_pipeline_updated(self, event_manager: EventManager) -> None:
        """Correct event structure for pipeline_updated."""
        sub = event_manager.subscribe()

        event_manager.emit_pipeline_updated(
            pipeline_id="pipe-123",
            project_id="project-456",
            state="coding",
            previous_state="queued",
        )

        event = sub.queue.get_nowait()
        assert event.event_type == EventType.PIPELINE_UPDATED
        assert event.data["pipeline_id"] == "pipe-123"
        assert event.data["state"] == "coding"
        assert event.data["previous_state"] == "queued"

    def test_event_format_pipeline_completed(self, event_manager: EventManager) -> None:
        """Correct event structure for pipeline_completed."""
        sub = event_manager.subscribe()

        event_manager.emit_pipeline_completed(
            pipeline_id="pipe-123",
            project_id="project-456",
            final_state="merged",
        )

        event = sub.queue.get_nowait()
        assert event.event_type == EventType.PIPELINE_COMPLETED
        assert event.data["pipeline_id"] == "pipe-123"
        assert event.data["final_state"] == "merged"

    def test_event_format_log(self, event_manager: EventManager) -> None:
        """Correct event structure for log."""
        sub = event_manager.subscribe()

        event_manager.emit_log(
            pipeline_id="pipe-123",
            project_id="project-456",
            level="info",
            message="Starting Claude Code...",
        )

        event = sub.queue.get_nowait()
        assert event.event_type == EventType.LOG
        assert event.data["pipeline_id"] == "pipe-123"
        assert event.data["level"] == "info"
        assert event.data["message"] == "Starting Claude Code..."
        assert "timestamp" in event.data

    def test_event_format_autopilot_started(self, event_manager: EventManager) -> None:
        """Correct event structure for autopilot_started."""
        sub = event_manager.subscribe()

        event_manager.emit_autopilot_started(project_id="project-456")

        event = sub.queue.get_nowait()
        assert event.event_type == EventType.AUTOPILOT_STARTED
        assert event.data["project_id"] == "project-456"

    def test_event_format_autopilot_stopped(self, event_manager: EventManager) -> None:
        """Correct event structure for autopilot_stopped."""
        sub = event_manager.subscribe()

        event_manager.emit_autopilot_stopped(project_id="project-456", reason="error")

        event = sub.queue.get_nowait()
        assert event.event_type == EventType.AUTOPILOT_STOPPED
        assert event.data["project_id"] == "project-456"
        assert event.data["reason"] == "error"

    def test_event_format_heartbeat(self, event_manager: EventManager) -> None:
        """Correct event structure for heartbeat."""
        heartbeat = event_manager.create_heartbeat_event()

        assert heartbeat.event_type == EventType.HEARTBEAT
        assert "timestamp" in heartbeat.data
        assert heartbeat.project_id is None  # Heartbeat goes to all

        # Check SSE format
        sse = heartbeat.to_sse()
        assert sse.startswith("event: heartbeat\n")
