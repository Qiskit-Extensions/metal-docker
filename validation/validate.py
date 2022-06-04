from sympy import false
from .exceptions import NoSubsystems, InvalidSubsystem, NoAssignedSubsystems

class ValidateInput:
    def __init__(self, graph, subsystems):
        self.graph = graph
        self.subsystems = subsystems
        self.validate_input()

    def validate_input(self): 
        #Check if a subsystem exists
        if (self.subsystems == {}):
                raise NoSubsystems 

        #Check if any components have a assigned subsystem, and if that subsystem is present in the list of subsystems
        validSubsystemExists = False
        for component, component_metadata in self.graph.items():
            subsystem = component_metadata['subsystem']
            if (subsystem != ""):
                if subsystem not in self.subsystems:
                    raise InvalidSubsystem(component, subsystem)
                validSubsystemExists = True
        if (not validSubsystemExists):
            raise NoAssignedSubsystems

