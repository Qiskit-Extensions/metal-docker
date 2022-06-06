"""A file containing all constants used in the validation module."""

TL_RESONATOR_KEYS = ["f_res", "Z0", "vp"]

BASE_ERROR = 'Encountered a exception of type \'%s\' with message \'%s\''
NO_SUBSYSTEMS = 'You have not created any subsystems. Utilize the \"Add subsystem parameters\" button in the side-panel to create a subsystem.'
INVALID_SUBSYSTEM = 'You have assigned an invalid subsystem name \'%s\' to component \'%s\'.'
NO_ASSIGNED_SUBSYSTEMS = 'You have not assigned any subsystems. Assign components to a subsystem before running simulations.'
INVALID_READOUT_OPTION = 'The subsytem \'%s\' of type \'TL_RESONATOR\' does not have the correct subsystem option keys. You have defined the subsystem options as %s. \'TL_RESONATOR \' must be formatted as: \n {' + '\n'.join(
    '\"{}\" : ... '.format(k) for k in (TL_RESONATOR_KEYS)) + '}'
