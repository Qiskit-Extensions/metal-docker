from .constants import *


class Error(Exception):

    def __init__(self, e):
        """A custom 'Exception' subclass to format misc exceptions.
        
        Args:
            e (Exception): The raised exception.
        """

        self.message = e
        self.type = type(e).__name__
        self.error_message = BASE_ERROR % (self.type, self.message)


class InvalidSubsystem(Exception):

    def __init__(self, component_name, subsystem_name):
        """A custom 'Exception' subclass to be raised when a component has an assigned subsystem that is not declared in the subsystem dict.

        Args: 
            component_name (str): Name of the component that has been assigned to an invalid subsystem. 
            subsystem_name (str): Name of the invalid subsystem.
        """
        self.subsystem_name = subsystem_name
        self.component_name = component_name
        self.error_message = INVALID_SUBSYSTEM % (self.subsystem_name,
                                                  self.component_name)


class NoAssignedSubsystems(Exception):

    def __init__(self):
        """A custom 'Exception' subclass to be rasied when no component in the circuit graph has an assigned subsystem."""

        self.error_message = NO_ASSIGNED_SUBSYSTEMS


class InvalidReadoutOptions(Exception):

    def __init__(self, component_name, current_options):
        """Raised when a component of type 'TL_RESONATOR' does not have the necessary option keys.

        Args: 
            subsystem_name (str): Name of the subsystem with invalid option keys
            current_options (dict): The current subsystem options defined in the subsystem.
        """

        self.error_message = INVALID_READOUT_OPTION % (component_name, current_options)


class NoSubsystems(Exception):

    def __init__(self):
        """A custom 'Exception' subclass to be raised when the subsystem dict is empty."""

        self.error_message = NO_SUBSYSTEMS

class InvalidSweepingSteps(Exception):

    def __init__(self, component_name ):
        """Raised when the sweeping step input is 0 or invalid"""

        self.error_message = INVALID_SWEEPING_STEPS % (component_name)