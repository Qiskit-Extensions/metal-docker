# Quantum SPICE 
# Converts circuit information to capacitance & inductance graph
# arbitrary class for each component in the quantum circuit

def value_to_int(val):
    """
    Convert value to integer
    """
    num = ''
    for c in val:
        if c.isdigit():
            num += c
    return int(num)


def get_set(terminal, connections):
    """
    Get connection set given a terminal and a list of connections
    """
    connection_set = set()
    connection_set.update(connections)
    connection_set.add(terminal)
    return frozenset(connection_set)


def terminal_in_dict(term, node_dict):
    """
    Return node name if terminal is in node_dict, otherwise, return None
    """
    for entry in node_dict:
        if term in entry:
            return node_dict[entry]
    return None


def node_in_list(node1, node2, node_tuple_list):
    """
    Return True if a node tuple is in the given node tuple list
    """
    if (node1, node2) not in node_tuple_list and (node2, node1) not in node_tuple_list:
        return False
    else:
        return True


class CircuitComponent(object):
    def __init__(self, name, type, terminals, value, connections, subsystem=None):
        """
        name (string) -> e.g. C1 or I2
        type (string) => e.g. capacitor or inductor
        terminal (string tuple) => e.g. (C1_1, C1_2)
        value (string) => e.g. 4F, 15H
        connection (dictionary w string key and string list value) => e.g. {C1_1: [C2_1, I1_2], C1_2: []}
        stores list of connections between => self.terminals (key) & other terminals (values)
        no connection is shown by []
        """
        self.name = name
        self.type = type
        self.terminals = terminals
        self.value = value
        self.connections = connections
        self.subsystem = subsystem


class Circuit(object):
    def __init__(self):
        """
        Create a circuit object to manage circuit-level operations using a circuit component list and
        circuit-level methods
        """
        self._circuit_component_list = []

    def clear_circuit_component_list(self):
        """
        Clear the circuit component list
        """
        self._circuit_component_list = []

    def get_component_from_terminal(self, terminal):
        """
        Return the CircuitComponent that has the give input terminal
        """
        for component in self._circuit_component_list:
            if terminal in component.terminals:
                return component
        raise Exception("Terminal " + terminal + " doesn't exist, perhaps you have a wrong test case?")

    def convert_parallel(self):
        """
        Make 2d list of components connected in parallel
        """
        parallel_connections = []
        existing_components = []
        for component in self._circuit_component_list:
            if component not in existing_components:
                connected_in_parallel = [component]
                connected1 = []
                for term in component.connections:
                    for con in component.connections[term]:
                        connected_components = self.get_component_from_terminal(con)
                        # if same type, add in the same list
                        if connected_components.type == component.type:
                            # if same component connected to both terminals
                            if connected_components in connected1:
                                connected_in_parallel.append(connected_components)
                            else:
                                connected1.append(connected_components)
                if len(connected_in_parallel) > 1:
                    parallel_connections.append(connected_in_parallel)
                    for connection in connected_in_parallel:
                        existing_components.append(connection)
        # loop through parallel_connections list,
        # replace parallel-connected components with single component
        # don't remove junctions for now
        for connection in parallel_connections:
            new_value = 0
            # get new index so that name doesn't overlap
            index = str(len(self._circuit_component_list) + 1)
            if connection[0].type == "capacitor":
                # make new connections dictionary
                new_connection_dict = {"C" + index + "_1": connection[0].connections[connection.terminals[0]],
                                       "C" + index + "_2": connection[0].connections[connection.terminals[1]]}
                for component in connection:
                    # add capacitance in parallel
                    new_value += value_to_int(component.value)
                    # remove redundant connections
                    for t in component.terminals:
                        for connection_dict_terminal in new_connection_dict:
                            if t in new_connection_dict[connection_dict_terminal]:
                                new_connection_dict[connection_dict_terminal].remove(t)
                    self._circuit_component_list.remove(component)
                total_value = str(new_value) + "F"
                # add new capacitor, remove old ones
                CircuitComponent("C" + index, "capacitor", ("C" + index + "_1", "C" + index + "_2"),
                                 total_value, new_connection_dict)
            elif connection[0].type == "inductor":
                # make new connections dictionary
                new_connection_dict = {"C" + index + "_1": connection[0].connections[connection.terminals[0]],
                                       "C" + index + "_2": connection[0].connections[connection.terminals[1]]}
                for component in connection:
                    # inverse --
                    new_value += 1 / value_to_int(component.value)
                    # remove redundant connections
                    for t in component.terminals:
                        for connection_dict_terminal in new_connection_dict:
                            if t in new_connection_dict[connection_dict_terminal]:
                                new_connection_dict[connection_dict_terminal].remove(t)
                    self._circuit_component_list.remove(component)
                # rounding?
                total_value = str(1 / new_value) + "H"
                # add new capacitor, remove old ones
                CircuitComponent("I" + index, "inductor", ("I" + index + "_1", "I" + index + "_2"),
                                 total_value, new_connection_dict)

            elif connection[0].type == "junction":
                # check other parallel-connected comps to see if there' any capacitors or inductors
                # if all parallel-comps in the group are junctions, throw RUNTIME ERROR #
                raise Exception("junctions connected in parallel")

    def get_other_terminal_same_component(self, terminal):
        """
        Return other terminal in the same component (assume only two terminals in a single component)
        """
        component = self.get_component_from_terminal(terminal)
        for t in component.terminals:
            if t != terminal:
                return t

    def get_value_from_terminal(self, terminal):
        """
        Return the value of the component that the terminal is in
        """
        component = self.get_component_from_terminal(terminal)
        return component.value

    def get_component_from_name(self, name):
        """
        Given the name of a component, return the CircuitComponent object
        """
        for component in self._circuit_component_list:
            if component.name == name:
                return component
        raise Exception("Component " + name + " doesn't exist")

    def get_nodes(self):
        """
        Loop through each component and return the list of nodes and the values between them
        """
        node_tuples = {}
        node_dict = {}
        index = 0
        for component in self._circuit_component_list:
            node_name = 'n' + str(index)
            for terminal in component.terminals:
                connections = component.connections[terminal]
                f_set = get_set(terminal, connections)

                # check if node already exist
                if not (f_set in node_dict):
                    # add to node_dict
                    index += 1
                    node_name = 'n' + str(index)
                    node_dict[f_set] = node_name

                # check if connected to other node
                other_terminal = self.get_other_terminal_same_component(terminal)
                node = terminal_in_dict(other_terminal, node_dict)
                if node is not None and node != node_name and not node_in_list(node, node_name, node_tuples):
                    val = get_value_from_terminal(terminal)
                    node_tuples[(node, node_name)] = (val, component.name)
        return node_tuples

    def get_subsystem_dict(self):
        """
        Return dictionary of subsystems - values are set of components in particular subsystem
        """
        subsystem_dict = {}
        for component in self._circuit_component_list:
            subsystem = component.subsystem
            if subsystem not in subsystem_dict:
                subsystem_dict[subsystem] = {component}
            else:
                subsystem_dict[subsystem].add(component)
        return subsystem_dict

    def get_component_name_subsystem(self):
        """
        Dictionary of subsystems - values are set of components' names in particular subsystem
        """
        subsystem_dict = {}
        for component in self._circuit_component_list:
            subsystem = component.subsystem
            if subsystem not in subsystem_dict:
                subsystem_dict[subsystem] = {component.name}
            else:
                subsystem_dict[subsystem].add(component.name)
        return subsystem_dict

    def get_inductor_list(self, node_tuples):
        """
        Get the inductor list for the current Circuit object
        """
        inductor_list = []
        # one dictionary per subsystem
        inductor_dict = {}
        subsystem_dict = self.get_subsystem_dict()
        for subsystem in subsystem_dict:
            for tup in node_tuples:
                value = node_tuples[tup][0]
                component = self.get_component_from_name(node_tuples[tup][1])
                component_subsystem = component.subsystem
                # if value has unit of inductance and is in current subsystem
                if value[-1] == 'H' and subsystem == component_subsystem:
                    integer_value = value_to_int(value)
                    inductor_dict[tup] = integer_value
            if inductor_dict != {}:
                inductor_list.append(inductor_dict)
            inductor_dict = {}
        return inductor_list
