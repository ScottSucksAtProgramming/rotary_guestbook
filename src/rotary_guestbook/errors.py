"""Custom exceptions for the Rotary Phone Audio Guestbook system.

This module provides a hierarchy of custom exceptions for the Rotary Phone Audio
Guestbook system. These exceptions are designed to provide clear, meaningful error
messages and proper error handling throughout the application.

The base exception class `GuestbookError` provides a foundation for all custom
exceptions, with support for both a primary message and optional detailed
information. All other exceptions in this module inherit from this base class.

Example:
    ```python
    try:
        # Some operation that might fail
        raise ConfigError("Failed to load configuration", "File not found")
    except ConfigError as e:
        print(f"Error: {e}")
        # Output: "Error: Failed to load configuration - File not found"
    ```

Note:
    All exceptions in this module support both a primary message and optional
    details. The string representation of an exception combines both pieces of
    information when details are provided.
"""

from typing import Optional


class GuestbookError(Exception):
    """Base exception class for all guestbook-related errors.

    This class serves as the foundation for all custom exceptions in the
    Rotary Phone Audio Guestbook system. It provides a standardized way to
    handle errors with both a primary message and optional detailed information.

    Attributes:
        message (str): The primary error message describing what went wrong.
        details (Optional[str]): Additional context or technical details about
            the error, if available.

    Example:
        ```python
        # Basic error
        error = GuestbookError("Operation failed")
        print(str(error))  # Output: "Operation failed"

        # Error with details
        error = GuestbookError("Operation failed", "Invalid input: xyz")
        print(str(error))  # Output: "Operation failed - Invalid input: xyz"
        ```
    """

    def __init__(self, message: str, details: Optional[str] = None) -> None:
        """Initialize the error with a message and optional details.

        Args:
            message: A human-readable error message that clearly describes
                what went wrong. This should be suitable for display to end users.
            details: Optional additional technical details about the error.
                This can include specific error codes, stack traces, or other
                debugging information that would be helpful for developers.

        Note:
            The string representation of the error will combine both the message
            and details (if provided) in a user-friendly format.
        """
        self.message = message
        self.details = details
        super().__init__(f"{message}{f' - {details}' if details else ''}")


class ConfigError(GuestbookError):
    """Raised when there is an error in configuration loading or validation.

    This exception is used for any issues related to the application's
    configuration, including:
    - Missing or invalid configuration files
    - Invalid configuration values
    - Configuration parsing errors
    - Missing required configuration parameters

    Example:
        ```python
        try:
            load_config("config.yaml")
        except ConfigError as e:
            logger.error(f"Configuration error: {e}")
        ```
    """

    pass


class AudioError(GuestbookError):
    """Raised when there is an error in audio operations.

    This exception covers all audio-related errors in the system, including:
    - Audio device initialization failures
    - Recording errors (e.g., device in use, permission denied)
    - Playback errors (e.g., file not found, format not supported)
    - Audio format conversion issues
    - Audio device not found or unavailable

    Example:
        ```python
        try:
            start_recording()
        except AudioError as e:
            logger.error(f"Audio recording failed: {e}")
        ```
    """

    pass


class HardwareError(GuestbookError):
    """Raised when there is an error in hardware operations.

    This exception is used for any issues related to the physical hardware
    components, including:
    - GPIO initialization failures
    - Hardware communication errors
    - Device not found or not responding
    - Hardware permission issues
    - Physical connection problems

    Example:
        ```python
        try:
            initialize_gpio()
        except HardwareError as e:
            logger.error(f"Hardware initialization failed: {e}")
        ```
    """

    pass


class ArchiveError(GuestbookError):
    """Raised when there is an error in message archiving operations.

    This exception covers all issues related to saving and managing recorded
    messages, including:
    - File system errors (e.g., disk full, permission denied)
    - Message format conversion failures
    - Database errors (if using a database backend)
    - Archive corruption or integrity issues
    - Backup failures

    Example:
        ```python
        try:
            save_message(audio_file)
        except ArchiveError as e:
            logger.error(f"Failed to archive message: {e}")
        ```
    """

    pass


class WebError(GuestbookError):
    """Raised when there is an error in web interface operations.

    This exception covers all web-related errors, including:
    - Server startup failures
    - Request handling errors
    - Authentication/authorization failures
    - API endpoint errors
    - WebSocket communication issues
    - Template rendering errors

    Example:
        ```python
        try:
            start_web_server()
        except WebError as e:
            logger.error(f"Web server failed to start: {e}")
        ```
    """

    pass


class HealthError(GuestbookError):
    """Raised when there is an error in system health monitoring.

    This exception is used for issues related to system health checks and
    monitoring, including:
    - Resource monitoring failures (CPU, memory, disk)
    - Device status check errors
    - Health check timeout or connection issues
    - Monitoring service failures
    - Alert system errors

    Example:
        ```python
        try:
            check_system_health()
        except HealthError as e:
            logger.error(f"Health check failed: {e}")
        ```
    """

    pass
