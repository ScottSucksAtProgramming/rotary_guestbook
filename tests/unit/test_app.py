"""Unit tests for the AppController class."""

from unittest.mock import MagicMock, patch

import pytest

from rotary_guestbook.app import AppController
from rotary_guestbook.config import ConfigManager


@pytest.fixture
def mock_config_manager() -> MagicMock:
    """Fixture to create a mock ConfigManager."""
    return MagicMock(spec=ConfigManager)


@pytest.fixture
def mock_phone_event_handler() -> MagicMock:
    """Fixture to create a mock PhoneEventHandler."""
    return MagicMock()


@pytest.fixture
def mock_audio_manager() -> MagicMock:
    """Fixture to create a mock AudioManager."""
    return MagicMock()


@pytest.fixture
def mock_web_server() -> MagicMock:
    """Fixture to create a mock WebServer."""
    return MagicMock()


class TestAppController:
    """Tests for the AppController class."""

    @patch("rotary_guestbook.app.logger")
    def test_app_controller_instantiation(
        self,
        mock_logger: MagicMock,
        mock_config_manager: MagicMock,
        mock_phone_event_handler: MagicMock,
        mock_audio_manager: MagicMock,
        mock_web_server: MagicMock,
    ) -> None:
        """Test that AppController instantiates correctly."""
        app_controller = AppController(
            config_manager=mock_config_manager,
            phone_event_handler=mock_phone_event_handler,
            audio_manager=mock_audio_manager,
            web_server=mock_web_server,
        )
        assert isinstance(app_controller, AppController)
        assert app_controller.config_manager == mock_config_manager
        assert app_controller.phone_event_handler == mock_phone_event_handler
        assert app_controller.audio_manager == mock_audio_manager
        assert app_controller.web_server == mock_web_server
        mock_logger.info.assert_called_once_with("AppController initialized.")

    @patch("rotary_guestbook.app.logger")
    def test_app_controller_run_method(
        self,
        mock_logger: MagicMock,
        mock_config_manager: MagicMock,
        mock_phone_event_handler: MagicMock,
        mock_audio_manager: MagicMock,
        mock_web_server: MagicMock,
    ) -> None:
        """Test the basic run method functionality."""
        app_controller = AppController(
            config_manager=mock_config_manager,
            phone_event_handler=mock_phone_event_handler,
            audio_manager=mock_audio_manager,
            web_server=mock_web_server,
        )
        # Reset mock logger for this specific test part if it was called in __init__
        mock_logger.reset_mock()

        app_controller.run()

        # Check for expected log messages from the run method
        mock_logger.info.assert_any_call("Starting AppController...")
        mock_logger.info.assert_any_call(
            "AppController finished its current run cycle."
        )
        assert mock_logger.info.call_count == 2
