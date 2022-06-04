from qiskit_metal import Dict

ErrorMessages = Dict(
    BASE_ERROR = "Encountered a exception of type \'%s\' with message \'%s\'",
    NO_SUBSYSTEMS = "You have not created any subsystems. Utilize the \"Add subsystem parameters\" button in the side-panel to create a subsystem.",
    INVALID_SUBSYSTEM = "You have assigned an invalid subsystem name \'%s\' to component \'%s\'.",
    NO_ASSIGNED_SUBSYSTEMS = "You have not assigned any subsystems. Assign components to a subsystem before running simulations.",
    INVALID_READOUT_OPTION = ""
)

class Error(Exception):
    def __init__(self, e):
        self.message = e
        self.type = type(e).__name__
        self.error_messaage = ErrorMessages.BASE_ERROR % (self.type, self.message)

    
class NoSubsystems(Exception):
    """Raised when the subsystem dict is empty."""
    def __init__(self):
        self.error_message = ErrorMessages.NO_SUBSYSTEMS

class InvalidSubsystem(Exception):
    """Raised when a component has an assigned subsystem that is not decalred in the subsystem dict."""
    def __init__(self, component_name, subsystem_name):
        self.component_name = component_name
        self.subsystem_name = subsystem_name 
        self.error_message = ErrorMessages.INVALID_SUBSYSTEM  % (self.subsystem_name, self.component_name)

class NoAssignedSubsystems(Exception):
    """Rasied when no component in the circuit graph has an assigned subsystem."""
    def __init__(self):
        self.error_message = ErrorMessages.NO_ASSIGNED_SUBSYSTEMS

class InvalidReadoutOptions(Exception):
    """Raised when """
    def __init__(self):
        self.error_message = ErrorMessages.INVALID_READOUT_OPTION

def _error_handling_wrapper(func):
    error_json = {}
    def _wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except InvalidSubsystem as e:
            return {'error' : e.error_message}

        except InvalidReadoutOptions as e:
            return {'error' : e.error_message}

        except NoAssignedSubsystems as e:
            return {'error' : e.error_message}
        
        except NoSubsystems as e:
            return {'error' : e.error_message}

        except Exception as e:
            error = Error(e)
            return {'error' : error.error_messaage}

    return _wrapper