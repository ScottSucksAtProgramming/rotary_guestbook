"""Unit tests for the custom exceptions module.

This module contains comprehensive tests for all custom exceptions defined in the
Rotary Phone Audio Guestbook system. The tests verify that exceptions are properly
initialized, maintain their inheritance hierarchy, and correctly format their
error messages.

The test suite covers:
- Basic error initialization and string representation
- Error inheritance hierarchy
- Message formatting with and without details
- Attribute access and validation
- Edge cases and error handling patterns

Example:
    ```python
    # Running a specific test
    pytest tests/unit/test_errors.py::test_guestbook_error_basic -v

    # Running all error tests
    pytest tests/unit/test_errors.py -v
    ```

Note:
    These tests are designed to be run as part of the full test suite, but can
    also be run independently for quick verification of the error handling system.
"""

from rotary_guestbook.errors import (
    ArchiveError,
    AudioError,
    ConfigError,
    GuestbookError,
    HardwareError,
    HealthError,
    WebError,
)


def test_guestbook_error_basic() -> None:
    """Test basic GuestbookError initialization and string representation.

    This test verifies that:
    1. A GuestbookError can be created with just a message
    2. The string representation matches the input message
    3. The message attribute is correctly set
    4. The details attribute is None when not provided

    Example:
        ```python
        error = GuestbookError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details is None
        ```
    """
    error = GuestbookError("Test error")
    assert str(error) == "Test error"
    assert error.message == "Test error"
    assert error.details is None


def test_guestbook_error_with_details() -> None:
    """Test GuestbookError with additional details.

    This test verifies that:
    1. A GuestbookError can be created with both message and details
    2. The string representation combines message and details correctly
    3. Both message and details attributes are correctly set
    4. The formatting of the combined string is correct

    Example:
        ```python
        error = GuestbookError("Test error", "Additional details")
        assert str(error) == "Test error - Additional details"
        assert error.message == "Test error"
        assert error.details == "Additional details"
        ```
    """
    error = GuestbookError("Test error", "Additional details")
    assert str(error) == "Test error - Additional details"
    assert error.message == "Test error"
    assert error.details == "Additional details"


def test_error_inheritance() -> None:
    """Test that all custom errors inherit from GuestbookError.

    This test verifies that:
    1. All custom exception classes properly inherit from GuestbookError
    2. All exceptions are also instances of the base Exception class
    3. The inheritance hierarchy is maintained for all error types

    Example:
        ```python
        error = ConfigError("Test")
        assert isinstance(error, GuestbookError)
        assert isinstance(error, Exception)
        ```
    """
    errors = [
        ConfigError("Config error"),
        AudioError("Audio error"),
        HardwareError("Hardware error"),
        ArchiveError("Archive error"),
        WebError("Web error"),
        HealthError("Health error"),
    ]

    for error in errors:
        assert isinstance(error, GuestbookError)
        assert isinstance(error, Exception)


def test_error_messages() -> None:
    """Test that each error type maintains its specific message.

    This test verifies that:
    1. Each error type correctly preserves its message and details
    2. The string representation is consistent across all error types
    3. The formatting of messages with details is uniform

    Example:
        ```python
        error = ConfigError("Test message", "Test details")
        assert str(error) == "Test message - Test details"
        ```
    """
    test_message = "Test message"
    test_details = "Test details"

    config_error = ConfigError(test_message, test_details)
    audio_error = AudioError(test_message, test_details)
    hardware_error = HardwareError(test_message, test_details)
    archive_error = ArchiveError(test_message, test_details)
    web_error = WebError(test_message, test_details)
    health_error = HealthError(test_message, test_details)

    assert str(config_error) == f"{test_message} - {test_details}"
    assert str(audio_error) == f"{test_message} - {test_details}"
    assert str(hardware_error) == f"{test_message} - {test_details}"
    assert str(archive_error) == f"{test_message} - {test_details}"
    assert str(web_error) == f"{test_message} - {test_details}"
    assert str(health_error) == f"{test_message} - {test_details}"


def test_error_attributes() -> None:
    """Test that error attributes are correctly set and accessible.

    This test verifies that:
    1. Error attributes can be accessed after initialization
    2. The attributes contain the expected values
    3. The attributes are properly typed

    Example:
        ```python
        error = GuestbookError("Test message", "Test details")
        assert error.message == "Test message"
        assert error.details == "Test details"
        ```
    """
    error = GuestbookError("Test message", "Test details")
    assert error.message == "Test message"
    assert error.details == "Test details"


def test_error_without_details() -> None:
    """Test error initialization without details parameter.

    This test verifies that:
    1. Errors can be created without providing details
    2. The details attribute is None when not provided
    3. The string representation only includes the message
    4. The behavior is consistent with the base class

    Example:
        ```python
        error = GuestbookError("Test message")
        assert error.message == "Test message"
        assert error.details is None
        assert str(error) == "Test message"
        ```
    """
    error = GuestbookError("Test message")
    assert error.message == "Test message"
    assert error.details is None
    assert str(error) == "Test message"
