"""Defines the abstract interface for phone hardware interactions."""

import abc
import enum


class HookEvent(enum.Enum):
    """Enumeration for phone hook events."""

    OFF_HOOK = "OFF_HOOK"
    ON_HOOK = "ON_HOOK"
    # Add other events like DIAL_PULSE, DIAL_COMPLETE if needed later


class AbstractPhoneHardware(abc.ABC):
    """Abstract base class for phone hardware interactions.

    This interface defines the essential operations for monitoring phone
    hardware events, such as hook status.
    """

    @abc.abstractmethod
    def wait_for_hook_event(self) -> HookEvent:
        """Wait for and return the next hook event.

        This method should block until a hook event (e.g., receiver lifted
        or replaced) occurs.

        Returns:
            The detected HookEvent (OFF_HOOK or ON_HOOK).

        Raises:
            HardwareError: If there is an issue communicating with the hardware.
        """
        pass

    @abc.abstractmethod
    def is_receiver_off_hook(self) -> bool:
        """Check the current status of the phone receiver.

        Returns:
            True if the receiver is currently off the hook, False otherwise.

        Raises:
            HardwareError: If there is an issue reading the hook status.
        """
        pass


# Placeholder for PhoneEventHandler and concrete hardware implementation
# which will be added in Phase 3.
# class PhoneEventHandler:
#     pass

# class RPiGPIOPhoneHardware(AbstractPhoneHardware):
#     pass
