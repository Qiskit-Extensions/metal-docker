from .exceptions import *


def validate_input(graph, subsystems):
    #Check if a subsystem exists
    if (subsystems == {}):
        raise NoSubsystems

    #Check if any components have a assigned subsystem, and if that subsystem is present in the list of subsystems
    validSubsystemExists = False
    for component, component_metadata in graph.items():
        subsystem = component_metadata['subsystem']
        if (subsystem != ""):
            if subsystem not in subsystems:
                raise InvalidSubsystem(component, subsystem)
            validSubsystemExists = True

    if (not validSubsystemExists):
        raise NoAssignedSubsystems
