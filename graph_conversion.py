# Quantum SPICE 
# Converts circuit information to capacitance & inductance graph
# arbitrary class for each component in the quantum circuit

class CircuitComponent(object):
    circuit_component_list = []

    def __init__(self, name, type, terminals, value, connections, subsystem=None):
        # name (string) -> e.g. C1, I2
        self.name = name
        # type (string) => e.g. capacitor, inductor
        self.type = type
        # terminal (string tuple) => e.g. (C1_1, C1_2)
        self.terminals = terminals
        # value (string) => e.g. 4F, 15H
        self.value = value
        # connection (dictionary w string key and string list value) 
        # e.g. {C1_1: [C2_1, I1_2], C1_2: []}
        # stores list of connections between 
        # self.terminals (key) & other terminals (values)
        # no connection is shown by []
        self.connections = connections
        self.subsystem = subsystem
        # add CircuitComponent instance to circuit_component_list
        CircuitComponent.circuit_component_list.append(self)

    def __del__(self):
        self.name = None
        self.type = None
        self.terminals = None
        self.value = None
        self.connections = None
        self.subsystem = None
        del self

    # clear circuit


def clear_circuit_component_list():
    for component in CircuitComponent.circuit_component_list:
        CircuitComponent.__del__(component)
    CircuitComponent.circuit_component_list = []


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# #              Helper Functions              ##
# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@


# return the CircuitComponent that has the input terminal
def get_component_from_terminal(terminal):
    for component in CircuitComponent.circuit_component_list:
        if terminal in component.terminals:
            return component
    raise Exception(terminal + " terminal doesn't exist, perhaps you have a wrong test case?")


# return other terminal in the same component 
# (assume only two terminals in a single component)
def get_other_terminal_same_component(terminal):
    component = get_component_from_terminal(terminal)
    for t in component.terminals:
        if t != terminal:
            return t


# return the value of the comp that 
# the terminal is in
def get_value_from_terminal(terminal):
    component = get_component_from_terminal(terminal)
    return component.value


def get_component_from_name(name):
    for component in CircuitComponent.circuit_component_list:
        if component.name == name:
            return component
    raise Exception(component + " comp doesn't exist")


# convert string val to int
def value_to_int(val):
    num = ''
    for c in val:
        if c.isdigit():
            num += c
    return int(num)


def get_set(term, cons):
    connection_set = set()
    connection_set.update(cons)
    connection_set.add(term)
    # node_dict's key is frozenset
    return frozenset(connection_set)


# return node name if terminal is in node_dict
# otherwise, return None
def terminal_in_dict(term, dict):
    for entry in dict:
        if term in entry:
            return dict[entry]
    return None


def node_in_list(node1, node2, node_tuples):
    if (node1, node2) not in node_tuples and (node2, node1) not in node_tuples:
        return False
    else:
        return True


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# #              Main Functions              ##
# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@


def convert_parallel():
    # make 2d list of comps connected in parallel
    parallel_connections = []
    existing_components = []
    for component in CircuitComponent.circuit_component_list:
        if component not in existing_components:
            connected_in_parallel = [component]
            connected1 = []
            for term in component.connections:
                for con in component.connections[term]:
                    connected_components = get_component_from_terminal(con)
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
        index = str(len(CircuitComponent.circuit_component_list) + 1)
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
                CircuitComponent.circuit_component_list.remove(component)
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
                CircuitComponent.circuit_component_list.remove(component)
            # rounding?    
            total_value = str(1 / new_value) + "H"
            # add new capacitor, remove old ones 
            CircuitComponent("I" + index, "inductor", ("I" + index + "_1", "I" + index + "_2"),
                             total_value, new_connection_dict)

        elif connection[0].type == "junction":
            # check other parallel-connected comps to see if there' any capacitors or inductors
            # if all parallel-comps in the group are junctions, throw RUNTIME ERROR #
            raise Exception("junctions connected in parallel")


# loop through each component, 
# return the list of nodes and the values between them
def get_nodes():
    # convertParallel()
    node_tuples = {}
    node_dict = {}
    index = 0
    for component in CircuitComponent.circuit_component_list:
        # for each terminal,
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
            other_terminal = get_other_terminal_same_component(terminal)
            node = terminal_in_dict(other_terminal, node_dict)
            if node is not None and node != node_name and not node_in_list(node, node_name, node_tuples):
                val = get_value_from_terminal(terminal)
                node_tuples[(node, node_name)] = (val, component.name)
    return node_tuples


def get_subsystem_dict():
    # dictionary of subsystems
    # values are set of comps in particular subsystem
    subsystem_dict = {}
    for component in CircuitComponent.circuit_component_list:
        subsystem = component.subsystem
        if subsystem not in subsystem_dict:
            subsystem_dict[subsystem] = {component}
        else:
            subsystem_dict[subsystem].add(component)
    return subsystem_dict


def get_component_name_subsystem():
    # dictionary of subsystems
    # values are set of comps' names in particular subsystem
    subsystem_dict = {}
    for component in CircuitComponent.circuit_component_list:
        subsystem = component.subsystem
        if subsystem not in subsystem_dict:
            subsystem_dict[subsystem] = {component.name}
        else:
            subsystem_dict[subsystem].add(component.name)
    return subsystem_dict


def get_inductor_list(node_tuples):
    inductor_list = []
    # one dictionary per subsystem
    inductor_dict = {}
    subsystem_dict = get_subsystem_dict()
    for subsystem in subsystem_dict:
        for tup in node_tuples:
            value = node_tuples[tup][0]
            component = get_component_from_name(node_tuples[tup][1])
            component_subsystem = component.subsystem
            # if value has unit of inductance and is in current subsystem
            if value[-1] == 'H' and subsystem == component_subsystem:
                integer_value = value_to_int(value)
                inductor_dict[tup] = integer_value
        if inductor_dict != {}:
            inductor_list.append(inductor_dict)
        inductor_dict = {}
    return inductor_list


def get_capacitor_list(node_tuples):
    capacitor_list = []
    # one dictionary per subsystem
    capacitor_dict = {}
    subsystem_dict = get_subsystem_dict()
    for subsystem in subsystem_dict:
        for tup in node_tuples:
            value = node_tuples[tup][0]
            component = get_component_from_name(node_tuples[tup][1])
            component_subsystem = component.subsystem
            # if value has unit of inductance and is in current subsystem
            if value[-1] == 'F' and subsystem == component_subsystem:
                integer_value = value_to_int(value)
                capacitor_dict[tup] = integer_value
        if capacitor_dict != {}:
            capacitor_list.append(capacitor_dict)
        capacitor_dict = {}
    return capacitor_list


def test():
    # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    # #                Test Case 1                 ##
    # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    #         (S1)       (S1)  
    #       -- C1 --  -- C2 -- 
    #       |                  |
    # (S2)  I2                 I1 (S1)
    #       |                  |
    #        -- C3 -- ---------
    #           (S2)

    c1 = CircuitComponent("C1", "capacitor", ("C1_1", "C1_2"), "5F", {"C1_1": ["I2_2"], "C1_2": ["C2_1"]}, 'S1')
    c2 = CircuitComponent("C2", "capacitor", ("C2_1", "C2_2"), "7F", {"C2_1": ["C1_2"], "C2_2": ["I1_1"]}, 'S1')
    i1 = CircuitComponent("I1", "inductor", ("I1_1", "I1_2"), "3H", {"I1_1": ["C2_2"], "I1_2": ["C3_1"]}, 'S1')
    c3 = CircuitComponent("C3", "capacitor", ("C3_1", "C3_2"), "9F", {"C3_1": ["I1_2"], "C3_2": ["I2_1"]}, 'S2')
    i2 = CircuitComponent("I2", "inductor", ("I2_1", "I2_2"), "11H", {"I2_1": ["C3_2"], "I2_2": ["C1_1"]}, 'S2')

    print('c1:', c1, '\nc2:', c2, '\ni1:', i1, '\nc3:', c3, '\ni2:', i2)

    print("Test case 1: node_tuples::")
    node_terminal = get_nodes()
    print("Node Dictionary::")
    print(node_terminal)
    print("Subsystem Dictionary::")
    print(get_component_name_subsystem())
    print("Inductor_list::")
    print(get_inductor_list(node_terminal))
    print("Capacitor list::")
    print(get_capacitor_list(node_terminal))
    print("\n")
    clear_circuit_component_list()

    # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    # #                Test Case 2                 ##
    # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    #         (S1)       (S1)  
    #        -- C1 -- -- C2 --_ 
    #       |        |         |
    # (S2)  I3       C3 (S1)   I1 (S1)
    #       |        |         |
    #        -- I2 -- -- C4 ---
    #           (S2)     (S2)

    c1 = CircuitComponent("C1", "capacitor", ("C1_1", "C1_2"), "5F", {"C1_1": ["I3_1"], "C1_2": ["C2_1", "C3_1"]}, 'S1')
    c2 = CircuitComponent("C2", "capacitor", ("C2_1", "C2_2"), "7F", {"C2_1": ["C1_2", "C3_1"], "C2_2": ["I1_1"]}, 'S1')
    c3 = CircuitComponent("C3", "capacitor", ("C3_1", "C3_2"), "9F",
                          {"C3_1": ["C1_2", "C2_1"], "C3_2": ["C4_1", "I2_2"]}, 'S1')
    i1 = CircuitComponent("I1", "inductor", ("I1_1", "I1_2"), "3H", {"I1_1": ["C2_2"], "I1_2": ["C4_2"]}, 'S1')
    c4 = CircuitComponent("C4", "capacitor", ("C4_1", "C4_2"), "11F", {"C4_1": ["C3_2", "I2_2"], "C4_2": ["I1_2"]},
                          'S2')
    i2 = CircuitComponent("I2", "inductor", ("I2_1", "I2_2"), "20H", {"I2_1": ["I3_2"], "I2_2": ["C3_2", "C4_1"]}, 'S2')
    i3 = CircuitComponent("I3", "inductor", ("I3_1", "I3_2"), "25H", {"I3_1": ["C1_1"], "I3_2": ["I2_1"]}, 'S2')

    print('c1:', c1, '\nc2:', c2, '\nc3:', c3, '\ni1:', i1, '\nc4:', c4, '\ni2:', i2, '\ni3:', i3)

    print("Test case 2: node_tuples::")
    node_terminal = get_nodes()
    print("Node Dictionary::")
    print(node_terminal)
    print("Subsystem Dictionary::")
    print(get_component_name_subsystem())
    print("Inductor_list::")
    print(get_inductor_list(node_terminal))
    print("\n")
    clear_circuit_component_list()


# test()
