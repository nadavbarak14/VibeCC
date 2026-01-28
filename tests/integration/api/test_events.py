"""Integration tests for SSE events endpoint."""

import tempfile
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn

from vibecc.api.app import create_app
from vibecc.api.dependencies import (
    get_event_manager,
    init_event_manager,
    init_state_store,
)
from vibecc.api.events import EventManager


@pytest.fixture
def db_path():
    """Create a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield f.name
    # Cleanup
    Path(f.name).unlink(missing_ok=True)
    Path(f"{f.name}-wal").unlink(missing_ok=True)
    Path(f"{f.name}-shm").unlink(missing_ok=True)


@pytest.fixture
def event_manager():
    """Create and initialize an EventManager."""
    em = init_event_manager()
    # Set shorter heartbeat for testing
    em._heartbeat_interval = 2
    return em


@pytest.fixture
def app(db_path: str, event_manager: EventManager):
    """Create the FastAPI app."""
    init_state_store(db_path)
    app = create_app(db_path)

    # Override event manager to use the test instance
    def override_get_event_manager():
        yield event_manager

    app.dependency_overrides[get_event_manager] = override_get_event_manager
    return app


@pytest.fixture
def server(app):
    """Start the app in a background thread."""
    config = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="error")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run)
    thread.daemon = True
    thread.start()

    # Wait for server to start
    time.sleep(0.5)
    yield "http://127.0.0.1:8765"

    server.should_exit = True
    thread.join(timeout=2)


@pytest.mark.integration
class TestSSEConnection:
    """Tests for SSE connection."""

    def test_sse_connection_opens(self, server: str) -> None:
        """Client can connect to /events/stream."""
        with (
            httpx.Client(timeout=5.0) as client,
            client.stream("GET", f"{server}/api/v1/events/stream") as response,
        ):
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


@pytest.mark.integration
class TestSSEHeartbeat:
    """Tests for SSE heartbeat."""

    def test_sse_receives_heartbeat(self, server: str, event_manager: EventManager) -> None:
        """Heartbeat received within interval."""
        # Set very short heartbeat for test
        event_manager._heartbeat_interval = 1

        received_heartbeat = False
        with (
            httpx.Client(timeout=5.0) as client,
            client.stream("GET", f"{server}/api/v1/events/stream") as response,
        ):
            for line in response.iter_lines():
                if "event: heartbeat" in line:
                    received_heartbeat = True
                    break

        assert received_heartbeat


@pytest.mark.integration
class TestSSEEvents:
    """Tests for SSE events."""

    def test_sse_receives_emitted_event(self, server: str, event_manager: EventManager) -> None:
        """Emitted event reaches client."""
        received_events = []

        def emit_after_delay():
            time.sleep(0.3)
            event_manager.emit_pipeline_created(
                pipeline_id="pipe-123",
                project_id="project-456",
                ticket_id="42",
                state="queued",
            )

        # Start emitter in background
        emitter = threading.Thread(target=emit_after_delay)
        emitter.start()

        with (
            httpx.Client(timeout=5.0) as client,
            client.stream("GET", f"{server}/api/v1/events/stream") as response,
        ):
            for line in response.iter_lines():
                if "event: pipeline_created" in line:
                    received_events.append(line)
                    break

        emitter.join()
        assert len(received_events) == 1
        assert "pipeline_created" in received_events[0]

    def test_sse_filter_by_project(self, server: str, event_manager: EventManager) -> None:
        """Only filtered events received."""
        received_events = []
        event_count = 0

        def emit_events():
            time.sleep(0.3)
            # Emit for project-123 (should be received)
            event_manager.emit_pipeline_created(
                pipeline_id="pipe-1",
                project_id="project-123",
                ticket_id="1",
                state="queued",
            )
            # Emit for project-456 (should NOT be received)
            event_manager.emit_pipeline_created(
                pipeline_id="pipe-2",
                project_id="project-456",
                ticket_id="2",
                state="queued",
            )
            time.sleep(0.2)

        emitter = threading.Thread(target=emit_events)
        emitter.start()

        # Subscribe only to project-123
        url = f"{server}/api/v1/events/stream?project_id=project-123"
        with (
            httpx.Client(timeout=5.0) as client,
            client.stream("GET", url) as response,
        ):
            start = time.time()
            for line in response.iter_lines():
                received_events.append(line)
                if "event: pipeline_created" in line:
                    event_count += 1
                # Only wait for a short time
                if time.time() - start > 1.0:
                    break

        emitter.join()

        # Should only receive one pipeline_created event (for project-123)
        assert event_count == 1
        # The data line should contain pipe-1 or project-123
        all_text = " ".join(received_events)
        assert "pipe-1" in all_text or "project-123" in all_text

    def test_sse_multiple_clients(self, server: str, event_manager: EventManager) -> None:
        """Multiple clients receive same event."""
        results = {"client1": [], "client2": []}

        def client_listener(client_name: str):
            with (
                httpx.Client(timeout=5.0) as client,
                client.stream("GET", f"{server}/api/v1/events/stream") as response,
            ):
                start = time.time()
                for line in response.iter_lines():
                    if "event: pipeline_created" in line:
                        results[client_name].append(line)
                    if time.time() - start > 1.5:
                        break

        def emit_event():
            time.sleep(0.5)
            event_manager.emit_pipeline_created(
                pipeline_id="pipe-123",
                project_id="project-456",
                ticket_id="42",
                state="queued",
            )

        # Start two clients
        t1 = threading.Thread(target=client_listener, args=("client1",))
        t2 = threading.Thread(target=client_listener, args=("client2",))
        emitter = threading.Thread(target=emit_event)

        t1.start()
        t2.start()
        time.sleep(0.2)  # Let clients connect
        emitter.start()

        t1.join(timeout=3)
        t2.join(timeout=3)
        emitter.join()

        # Both clients should have received the event
        assert len(results["client1"]) >= 1
        assert len(results["client2"]) >= 1


@pytest.mark.integration
class TestSSEDisconnect:
    """Tests for SSE client disconnect."""

    def test_sse_client_disconnect(self, server: str, event_manager: EventManager) -> None:
        """Cleanup on disconnect."""
        initial_count = event_manager.subscriber_count

        with (
            httpx.Client(timeout=5.0) as client,
            client.stream("GET", f"{server}/api/v1/events/stream"),
        ):
            # Client connected
            time.sleep(0.2)
            # Should have one more subscriber
            assert event_manager.subscriber_count == initial_count + 1

        # After disconnect, give it a moment to clean up
        time.sleep(0.3)
        # Subscriber count should be back to initial
        assert event_manager.subscriber_count == initial_count
