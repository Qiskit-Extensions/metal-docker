from collections import defaultdict, namedtuple

CircuitComponent = namedtuple('CircuitComponent', [
    'name', 'component_type', 'terminals', 'value', 'connections', 'subsystem'
])


def _dfs_connected_terminals(connected, terminal, connections, visited):
    # Mark the current terminal as visited
    visited[terminal] = True
    # Store the terminal to list
    connected.append(terminal)
    # Repeat for all terminal connected to this terminal
    for t in connections[terminal]:
        if visited.get(t, False) == False:
            # Update the list
            connected = _dfs_connected_terminals(connected, t, connections,
                                                 visited)
    return connected


def _find_connected_terminals(connections):
    visited = {}
    connected_components = []
    for terminal in connections:
        if visited.get(terminal, False) == False:
            connected = []
            connected_components.append(
                _dfs_connected_terminals(connected, terminal, connections,
                                         visited))
    return connected_components


class Circuit:
    def __init__(self, circuit_graph):
        """
        Create a circuit object to manage circuit-level operations using a circuit component list and
        circuit-level methods
        """
        self._circuit_graph = circuit_graph
        self._circuit_component_list = []

        self._circuit_component_list = []

        for component_name, component_metadata in self._circuit_graph.items():
            if component_metadata['subsystem']:
                subsystem = component_metadata['subsystem']
            else:
                subsystem = None
            circuit_component = CircuitComponent(
                component_name, component_metadata['component_type'],
                component_metadata['terminals'], component_metadata['value'],
                component_metadata['connections'], subsystem)
            self._circuit_component_list.append(circuit_component)

        all_connections = {}
        for comp in self._circuit_component_list:
            all_connections = {**all_connections, **comp.connections}

        connected_terminals = _find_connected_terminals(all_connections)
        nodes = []
        for idx, group in enumerate(connected_terminals):
            if 'GND_gnd' in group:
                nodes.append('GND_gnd')
            else:
                # ***********************************
                # Prefix 'F' is  crucial because it makes sure
                # the ground node is always ordered after the other nodes
                # ***********************************
                nodes.append(f'F{idx+1}')

        self.nodes_to_terminals = dict(zip(nodes, connected_terminals))
        terminals_to_nodes = {}
        for group, node in zip(connected_terminals, nodes):
            for terminal in group:
                terminals_to_nodes[terminal] = node
        self.terminals_to_nodes = terminals_to_nodes

    def get_component_name_subsystem(self):
        # dictionary of subsystems
        # values are set of comps' names in particular subsystem
        subDict = defaultdict(list)
        for comp in self._circuit_component_list:
            subSys = comp.subsystem
            # if comp is in a subsystem
            if subSys != '':
                subDict[subSys].append(comp.name)
        return subDict

    # convert componenets in subsystem map as nodes
    def get_subsystem_map(self, subsystemDict, nodeTup):
        subsystemMap = subsystemDict.copy()
        # loop through all subsystems
        for subsystem in subsystemDict:
            # for each component in a subsystem
            for comp in subsystemDict[subsystem]:
                for tup in nodeTup:
                    if nodeTup[tup][1] == comp:
                        subsystemMap[subsystem].remove(comp)
                        # convert component to nodes it's connected to
                        if tup[0] not in subsystemMap[subsystem]:
                            subsystemMap[subsystem].append(tup[0])
                        if tup[1] not in subsystemMap[subsystem]:
                            subsystemMap[subsystem].append(tup[1])
                        break
        return subsystemMap

    def _get_branches(self, branch_type):
        branches = defaultdict(float)
        for comp in self._circuit_component_list:
            if comp.value.get(branch_type, 0) > 0:
                nodes = tuple(
                    sorted(
                        list(
                            set([
                                self.terminals_to_nodes[t]
                                for t in comp.terminals
                            ]))))
                if branch_type == 'capacitance':
                    branches[nodes] += comp.value['capacitance']
                elif branch_type == "inductance":
                    l = branches[nodes]
                    if l:
                        branches[nodes] = l * comp.value['inductance'] / (
                            l + comp.value['inductance'])
                    else:
                        branches[nodes] = comp.value['inductance']
                else:
                    raise ValueError(f'branch type {branch_type} is not valid')
        return branches

    def get_capacitance_branches(self):
        return self._get_branches('capacitance')

    def get_inductance_branches(self):
        return self._get_branches('inductance')

    def get_jj_branches(self):
        branches = {}
        for comp in self._circuit_component_list:
            if comp.component_type == "josephson_junction":
                nodes = tuple(
                    sorted(
                        list(
                            set([
                                self.terminals_to_nodes[t]
                                for t in comp.terminals
                            ]))))
                branches[nodes] = comp.name
        return branches

    def get_capacitance_graph(self):
        cap_branches = self.get_capacitance_branches()
        capGraph = defaultdict(dict)
        for (node1, node2), val in cap_branches.items():
            capGraph[node1][node2] = val
        return capGraph

    def get_subsystem_to_nodes_map(self):
        subsystem_to_comps = self.get_component_name_subsystem()
        subsystem_to_nodes = {}
        for subsystem, comps in subsystem_to_comps.items():
            nodes = []
            for comp in comps:
                terminals = list(
                    filter(lambda x: x.name == comp,
                           self._circuit_component_list))[0].terminals
                _nodes = [self.terminals_to_nodes[t] for t in terminals]
                nodes.extend(_nodes)
            subsystem_to_nodes[subsystem] = sorted(list(set(nodes)))
        return subsystem_to_nodes
