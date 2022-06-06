from validation.exceptions import *


def error_handling_wrapper(func):
    error_json = {}

    def _wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except InvalidSubsystem as e:
            return {'error': e.error_message}

        except InvalidReadoutOptions as e:
            return {'error': e.error_message}

        except NoAssignedSubsystems as e:
            return {'error': e.error_message}

        except NoSubsystems as e:
            return {'error': e.error_message}

        except Exception as e:
            error = Error(e)
            return {'error': error.error_message}

    return _wrapper