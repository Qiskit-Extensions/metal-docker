import numpy as np
from collections import defaultdict, namedtuple
from itertools import product

from validation.exceptions import InvalidSweepingSteps

SWEEP_NUM = 3

CircuitComponent = namedtuple('CircuitComponent', [
    'name', 'component_type', 'terminals', 'value', 'connections', 'subsystem'
])


def _combine_parallel_cap(*args):
    if len(args) == 2:
        return args[0] + args[1]
    else:
        return args[0]


def _combine_parallel_ind(*args):
    if len(args) == 2:
        return (args[0] * args[1]) / (args[0] + args[1])
    else:
        return args[0]


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


def get_capacitance_graph(cap_branches):
    capGraph = defaultdict(dict)
    for (node1, node2), val in cap_branches.items():
        capGraph[node1][node2] = val

    new_capacitance_graph = {}  #restructure data to work with LOM code
    for node, connections in capGraph.items():
        new_capacitance_graph[node] = []
        for connection_node, capacitance in connections.items():
            new_capacitance_graph[node].append(
                (connection_node, float(capacitance)))

    return new_capacitance_graph


class Circuit:

    def __init__(self, circuit_graph):
        """
        Create a circuit object to manage circuit-level operations using a circuit component list and
        circuit-level methods
        """
        self._circuit_graph = circuit_graph
        self._circuit_component_list = []
        self._sweep_steps = {}

        # self._circuit_component_list = []

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
        excluding_gnd = []
        gnd_group = None
        for group in connected_terminals:
            if 'GND_gnd' in group:
                gnd_group = group
            else:
                excluding_gnd.append(group)
        connected_terminals = [gnd_group] + excluding_gnd
        nodes = [f'n{ii}' for ii in range(len(connected_terminals))]

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

    def _get_branches(self, branch_type):
        branches = defaultdict(list)
        to_sweeping_components = defaultdict(list)
        for comp in self._circuit_component_list:
            nodes = tuple(
                sorted(list(
                    set([self.terminals_to_nodes[t] for t in comp.terminals])),
                       reverse=True))

            lo = comp.value.get(f'{branch_type}Lo', 0)
            hi = comp.value.get(f'{branch_type}Hi', 0)
            sweep_vals = []
            if lo is not None and hi is not None and lo > 0 and hi > lo:
                try:
                    sweep_step = int(self._sweep_steps["_".join(
                        [comp.name, branch_type])])
                    sweep_vals = np.linspace(lo, hi, sweep_step)
                    to_sweeping_components[nodes].append(comp.name)
                except Exception:
                    raise InvalidSweepingSteps("_".join(
                        [comp.name, branch_type]))
            elif comp.value.get(branch_type, 0) > 0:
                sweep_vals = [comp.value[branch_type]]

            if len(sweep_vals):
                current_vals = branches[nodes]
                if current_vals:
                    combo = product(current_vals, sweep_vals)
                else:
                    combo = [(x, ) for x in sweep_vals]
                if branch_type == 'capacitance':
                    branches[nodes] = [
                        _combine_parallel_cap(*x) for x in combo
                    ]
                elif branch_type == "inductance":
                    branches[nodes] = [
                        _combine_parallel_ind(*x) for x in combo
                    ]
                else:
                    raise ValueError(f'branch type {branch_type} is not valid')

        return branches, to_sweeping_components

    def set_sweep_steps(self, sweep_steps):
        self._sweep_steps = sweep_steps

    def get_capacitance_branches(self):
        return self._get_branches('capacitance')

    def get_inductance_branches(self):
        return self._get_branches('inductance')

    def get_jj_branches(self):
        branches = {}
        for comp in self._circuit_component_list:
            if comp.component_type == "josephson_junction":
                nodes = tuple(
                    sorted(list(
                        set([
                            self.terminals_to_nodes[t] for t in comp.terminals
                        ])),
                           reverse=True))
                branches[nodes] = comp.name
        return branches

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
            subsystem_to_nodes[subsystem] = sorted(list(set(nodes)),
                                                   reverse=True)
        return subsystem_to_nodes


def map_sweeping_component_indices(comp_nodes, sweeping_components,
                                   sweep_steps, branch_type):
    indices = {}
    for _nodes in comp_nodes:
        if _nodes in sweeping_components:
            components = sweeping_components[_nodes]
            num_comp = len(components)
            idx_arr = [
                range(int(sweep_steps[sweep_step + "_" + branch_type]))
                for sweep_step in components
            ]
            idx_combo = product(*idx_arr)
            indices[_nodes] = list(idx_combo)
        else:
            idx_arr = [range(1) for _ in range(1)]
            idx_combo = product(*idx_arr)
            indices[_nodes] = list(idx_combo)

    return indices
