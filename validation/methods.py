from .exceptions import *
from .constants import TL_RESONATOR_KEYS


def validate_input(graph: dict, subsystems_list: dict):
    """Runs all validation functions. Main function to be imported by app.py

    Args:
        graph (dict): A dict containing all the components on the graph
        subsystems_list (dict): A dict containing the list of all subsystems
    """
    validate_subsystems_list(subsystems_list)
    validate_components_subsystems(graph, subsystems_list)


def validate_subsystems_list(subsystems_list: dict):
    """"Checks if the list of subsystems is non empty. 
    Checks that any subsystem of type 'TL_RESONATOR' has the necessary option keys.
    
    Args:
        subsystems_list (dict): A dict containing the list of all subsystems
    """
    if (subsystems_list == {}):
        # sock.send({"type": "error", "message": NoSubsystems.error_message})
        raise NoSubsystems
    else:
        for subsystem_name, subsystem_metadata in subsystems_list.items():
            if subsystem_metadata['subsystem_type'] == 'TL_RESONATOR':
                if not all(key in subsystem_metadata["options"]
                           for key in TL_RESONATOR_KEYS):
                    raise InvalidReadoutOptions(subsystem_name,
                                                subsystem_metadata["options"])


def validate_components_subsystems(graph: dict, subsystems_list: dict):
    """Check if any components have a assigned subsystem, and if that 
    subsystem is present in the list of subsystems.

    Args:
        graph (dict): A dict containing all the components on the graph
        subsystems_list (dict): A dict containing the list of all subsystems
    """
    validSubsystemExists = False
    for component_name, component_metadata in graph.items():
        subsystem = component_metadata['subsystem']
        if (subsystem != ""):
            if subsystem not in subsystems_list:
                raise InvalidSubsystem(component_name, subsystem)
            validSubsystemExists = True

    if (not validSubsystemExists):
        raise NoAssignedSubsystems