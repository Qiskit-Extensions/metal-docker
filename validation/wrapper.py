from .exceptions import *
import logging

def error_handling_wrapper(func):
    """A custom error handling wrapper to catch all exceptions raised during simulation. 
    """

    def _wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except InvalidSubsystem as e:
            logging.exception("Exception occurred")
            return {
                'error': {
                    'type': type(e).__name__,
                    'message': e.error_message
                }
            }

        except InvalidReadoutOptions as e:
            logging.exception("Exception occurred")
            return {
                'error': {
                    'type': type(e).__name__,
                    'message': e.error_message
                }
            }
        except NoAssignedSubsystems as e:
            logging.exception("Exception occurred")
            return {
                'error': {
                    'type': type(e).__name__,
                    'message': e.error_message
                }
            }
        except NoSubsystems as e:
            logging.exception("Exception occurred")
            return {
                'error': {
                    'type': type(e).__name__,
                    'message': e.error_message
                }
            }
        except Exception as e:
            logging.exception("Exception occurred")
            error = Error(e)
            return {
                'error': {
                    'type': type(error).__name__,
                    'message': error.error_message
                }
            }

    return _wrapper