"""Unit tests for SessionLogger."""

import json
from pathlib import Path

from freespec.llm.session_logger import SessionLogger


class TestSessionLogger:
    """Tests for SessionLogger."""

    def test_creates_log_files(self, tmp_path: Path) -> None:
        """Should create both text and JSON log files."""
        logger = SessionLogger(
            log_dir=tmp_path,
            project_name="test-project",
            language="python",
        )

        text_log, json_log = logger.get_log_paths()

        assert text_log.exists()
        assert text_log.suffix == ".log"
        assert "_session.log" in text_log.name

        # JSON log should exist after logging something
        logger.log_interaction(
            interaction_type="generate",
            prompt="test prompt",
            output="test output",
            success=True,
            error=None,
            duration_seconds=1.5,
            session_id="test-session",
        )

        assert json_log.exists()
        assert json_log.suffix == ".json"

    def test_logs_interaction(self, tmp_path: Path) -> None:
        """Should log interactions to both files."""
        logger = SessionLogger(
            log_dir=tmp_path,
            project_name="test-project",
            language="python",
        )
        logger.set_current_spec("entities/student")
        logger.set_current_phase("impl")

        logger.log_interaction(
            interaction_type="generate",
            prompt="Generate code for student",
            output="class Student: pass",
            success=True,
            error=None,
            duration_seconds=2.5,
            session_id="abc123",
            attempt=1,
        )

        # Check text log
        text_log, json_log = logger.get_log_paths()
        text_content = text_log.read_text()
        assert "INTERACTION #1" in text_content
        assert "entities/student" in text_content
        assert "impl" in text_content
        assert "Generate code for student" in text_content
        assert "class Student: pass" in text_content

        # Check JSON log
        json_content = json.loads(json_log.read_text())
        assert len(json_content["interactions"]) == 1
        interaction = json_content["interactions"][0]
        assert interaction["spec_id"] == "entities/student"
        assert interaction["phase"] == "impl"
        assert interaction["success"] is True
        assert interaction["duration_seconds"] == 2.5

    def test_logs_multiple_interactions(self, tmp_path: Path) -> None:
        """Should log multiple interactions in order."""
        logger = SessionLogger(
            log_dir=tmp_path,
            project_name="test-project",
            language="python",
        )

        logger.log_interaction(
            interaction_type="generate",
            prompt="first",
            output="output1",
            success=True,
            error=None,
            duration_seconds=1.0,
            session_id="s1",
        )

        logger.log_interaction(
            interaction_type="fork",
            prompt="second",
            output="output2",
            success=False,
            error="Some error",
            duration_seconds=2.0,
            session_id="s2",
            parent_session_id="s1",
        )

        _, json_log = logger.get_log_paths()
        json_content = json.loads(json_log.read_text())

        assert len(json_content["interactions"]) == 2
        assert json_content["interactions"][0]["prompt"] == "first"
        assert json_content["interactions"][1]["prompt"] == "second"
        assert json_content["interactions"][1]["parent_session_id"] == "s1"
        assert json_content["interactions"][1]["error"] == "Some error"

    def test_logs_summary(self, tmp_path: Path) -> None:
        """Should log session summary."""
        logger = SessionLogger(
            log_dir=tmp_path,
            project_name="test-project",
            language="python",
        )

        logger.log_interaction(
            interaction_type="generate",
            prompt="test",
            output="test",
            success=True,
            error=None,
            duration_seconds=1.0,
            session_id="s1",
        )

        logger.log_summary(
            total_specs=5,
            successful_specs=4,
            failed_specs=1,
            total_duration_seconds=120.5,
            extra={"custom_field": "value"},
        )

        # Check text log
        text_log, json_log = logger.get_log_paths()
        text_content = text_log.read_text()
        assert "SESSION SUMMARY" in text_content
        assert "Total Specs:        5" in text_content
        assert "Successful:         4" in text_content
        assert "Failed:             1" in text_content

        # Check JSON log
        json_content = json.loads(json_log.read_text())
        assert json_content["summary"]["total_specs"] == 5
        assert json_content["summary"]["successful_specs"] == 4
        assert json_content["summary"]["failed_specs"] == 1
        assert json_content["summary"]["total_duration_seconds"] == 120.5
        assert json_content["summary"]["custom_field"] == "value"

    def test_header_includes_project_info(self, tmp_path: Path) -> None:
        """Should include project info in the header."""
        logger = SessionLogger(
            log_dir=tmp_path,
            project_name="my-project",
            language="cpp",
        )

        text_log, _ = logger.get_log_paths()
        text_content = text_log.read_text()

        assert "my-project" in text_content
        assert "cpp" in text_content
        assert "FREESPEC COMPILATION SESSION LOG" in text_content
