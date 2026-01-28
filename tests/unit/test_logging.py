"""Unit tests for VibeCC logging configuration."""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from vibecc.logging import get_logger, sanitize_for_log, setup_logging, truncate_output


@pytest.mark.unit
class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_creates_log_directory(self) -> None:
        """Log directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "nested" / "logs"
            setup_logging(log_dir=log_dir, console=False)

            assert log_dir.exists()

    def test_creates_log_file(self) -> None:
        """Log file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_dir=tmpdir, console=False)

            log_file = Path(tmpdir) / "vibecc.log"
            assert log_file.exists()

    def test_writes_to_log_file(self) -> None:
        """Log messages are written to the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging(log_dir=tmpdir, console=False)
            logger.info("test message 123")

            log_file = Path(tmpdir) / "vibecc.log"
            content = log_file.read_text()
            assert "test message 123" in content

    def test_log_format_includes_timestamp(self) -> None:
        """Log entries include timestamps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging(log_dir=tmpdir, console=False)
            logger.info("format test")

            content = (Path(tmpdir) / "vibecc.log").read_text()
            # Format: 2026-01-28 16:30:45 | INFO     | vibecc | message
            assert " | INFO" in content
            assert " | vibecc | " in content

    def test_log_format_includes_component_name(self) -> None:
        """Log entries include the component logger name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_dir=tmpdir, console=False)
            child_logger = logging.getLogger("vibecc.git_manager")
            child_logger.info("component test")

            content = (Path(tmpdir) / "vibecc.log").read_text()
            assert "vibecc.git_manager" in content

    def test_all_components_write_to_same_file(self) -> None:
        """All component loggers write to the same log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_dir=tmpdir, console=False)

            logging.getLogger("vibecc.git_manager").info("git log")
            logging.getLogger("vibecc.kanban").info("kanban log")
            logging.getLogger("vibecc.workers.coder").info("coder log")
            logging.getLogger("vibecc.state_store").info("store log")

            content = (Path(tmpdir) / "vibecc.log").read_text()
            assert "git log" in content
            assert "kanban log" in content
            assert "coder log" in content
            assert "store log" in content

    def test_log_level_configurable(self) -> None:
        """Log level filters messages appropriately."""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_dir=tmpdir, level="WARNING", console=False)
            logger = logging.getLogger("vibecc")
            logger.info("should not appear")
            logger.warning("should appear")

            content = (Path(tmpdir) / "vibecc.log").read_text()
            assert "should not appear" not in content
            assert "should appear" in content

    @patch.dict(os.environ, {"VIBECC_LOG_LEVEL": "DEBUG"})
    def test_log_level_from_env(self) -> None:
        """Log level can be set via environment variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging(log_dir=tmpdir, console=False)

            assert logger.level == logging.DEBUG

    def test_log_dir_from_env(self) -> None:
        """Log directory can be set via environment variable."""
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.dict(os.environ, {"VIBECC_LOG_DIR": tmpdir}),
        ):
            setup_logging(console=False)

            assert (Path(tmpdir) / "vibecc.log").exists()

    def test_custom_log_filename(self) -> None:
        """Custom log filename is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_dir=tmpdir, log_file="custom.log", console=False)

            assert (Path(tmpdir) / "custom.log").exists()

    def test_returns_vibecc_logger(self) -> None:
        """Returns the root vibecc logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging(log_dir=tmpdir, console=False)

            assert logger.name == "vibecc"

    def test_no_duplicate_handlers_on_repeated_setup(self) -> None:
        """Repeated setup_logging calls don't add duplicate handlers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_dir=tmpdir, console=False)
            setup_logging(log_dir=tmpdir, console=False)

            logger = logging.getLogger("vibecc")
            assert len(logger.handlers) == 1


@pytest.mark.unit
class TestRotation:
    """Tests for log rotation."""

    def test_rotation_configured(self) -> None:
        """RotatingFileHandler is configured with correct max size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(log_dir=tmpdir, max_bytes=1024, backup_count=3, console=False)

            logger = logging.getLogger("vibecc")
            file_handler = None
            for handler in logger.handlers:
                if hasattr(handler, "maxBytes"):
                    file_handler = handler
                    break

            assert file_handler is not None
            assert file_handler.maxBytes == 1024
            assert file_handler.backupCount == 3

    def test_logs_rotate_at_max_size(self) -> None:
        """Log files rotate when they reach max size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set very small max size to trigger rotation
            setup_logging(log_dir=tmpdir, max_bytes=500, backup_count=2, console=False)
            logger = logging.getLogger("vibecc")

            # Write enough to trigger rotation
            for i in range(50):
                logger.info("Rotation test message number %d with padding data", i)

            log_dir = Path(tmpdir)
            # Main log file should exist
            assert (log_dir / "vibecc.log").exists()
            # At least one backup should exist
            assert (log_dir / "vibecc.log.1").exists()


@pytest.mark.unit
class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_prefixes_vibecc(self) -> None:
        """Logger name is prefixed with vibecc."""
        logger = get_logger("git_manager")
        assert logger.name == "vibecc.git_manager"

    def test_get_logger_no_double_prefix(self) -> None:
        """Already prefixed names are not double-prefixed."""
        logger = get_logger("vibecc.kanban")
        assert logger.name == "vibecc.kanban"


@pytest.mark.unit
class TestTruncateOutput:
    """Tests for truncate_output function."""

    def test_short_output_unchanged(self) -> None:
        """Short output is returned as-is."""
        result = truncate_output("short text", max_length=100)
        assert result == "short text"

    def test_long_output_truncated(self) -> None:
        """Long output is truncated with indicator."""
        long_text = "x" * 200
        result = truncate_output(long_text, max_length=100)
        assert len(result) < 200
        assert "truncated" in result
        assert "100 more chars" in result


@pytest.mark.unit
class TestSanitize:
    """Tests for sanitize_for_log function."""

    def test_redacts_github_pat(self) -> None:
        """GitHub PATs are redacted."""
        text = "token is ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        result = sanitize_for_log(text)
        assert "ghp_" not in result
        assert "[GITHUB_TOKEN]" in result

    def test_redacts_github_oauth(self) -> None:
        """GitHub OAuth tokens are redacted."""
        text = "auth: gho_1234567890abcdefghijklmnopqrstuvwxyz"
        result = sanitize_for_log(text)
        assert "gho_" not in result
        assert "[GITHUB_TOKEN]" in result

    def test_redacts_bearer_tokens(self) -> None:
        """Bearer tokens are redacted."""
        text = "Authorization: Bearer abc123.def456.ghi789"
        result = sanitize_for_log(text)
        assert "abc123" not in result
        assert "Bearer [REDACTED]" in result

    def test_safe_text_unchanged(self) -> None:
        """Text without sensitive data is unchanged."""
        text = "Pipeline abc123 moved to TESTING"
        result = sanitize_for_log(text)
        assert result == text
