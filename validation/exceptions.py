from validation.constants import *


class Error(Exception):

    def __init__(self, e):
        self.message = e
        self.type = type(e).__name__
        self.error_message = BASE_ERROR % (self.type, self.message)


class InvalidSubsystem(Exception):
    """Raised when a component has an assigned subsystem that is not decalred in the subsystem dict."""

    def __init__(self, component_name, subsystem_name):
        self.subsystem_name = subsystem_name
        self.component_name = component_name
        self.error_message = INVALID_SUBSYSTEM % (self.subsystem_name,
                                                  self.component_name)


class NoAssignedSubsystems(Exception):
    """Rasied when no component in the circuit graph has an assigned subsystem."""

    def __init__(self):
        self.error_message = NO_ASSIGNED_SUBSYSTEMS


class InvalidReadoutOptions(Exception):
    """Raised when """

    def __init__(self):
        self.error_message = INVALID_READOUT_OPTION


class NoSubsystems(Exception):
    """Raised when the subsystem dict is empty."""

    def __init__(self):
        self.error_message = NO_SUBSYSTEMS
