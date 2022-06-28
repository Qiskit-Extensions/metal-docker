import pandas as pd
import numpy as np
from copy import deepcopy
from itertools import product

from .constants import *


def sweep_dict_to_combo_list(sweep_dict):
    """Example:
       {(n1, n2): [x, y], (n3, n4): [z]} --> [(x, z), (y, z)]
    """
    return list(product(*sweep_dict.values()))


def adj_list_to_mat(index, adj_list):
    """ convert adjacency list representation of capacitance graph to
    a matrix representation 
    """
    idx = index
    dim = len(idx)
    mat = np.zeros((dim, dim))
    for n1 in adj_list:
        print('n1:', n1)
        for n2, w in adj_list[n1]:
            print('n2:', n2, '\nw:', w)
            r = idx.get_indexer([n1])[0]
            c = idx.get_indexer([n2])[0]
            mat[r, c] += w
            if r != c:
                mat[c, r] += w
    return mat


def make_cmat_df(cmat, nodes):
    """
    generate a pandas dataframe from a capacitance matrix and list of node names
    """
    df = pd.DataFrame(cmat)
    df.columns = nodes
    df.index = nodes
    return df


def convert_netlist_to_maxwell(df):
    df_new = df.copy()
    for key in df.keys():
        df_new[key][key] = -sum(df[key].values)
        df_new[key] = -df_new[key]
    return df_new


def get_component_name_from_terminal(circuit_graph, terminal):
    """
    Return the CircuitComponent that has the given terminal
    """
    for comp_name, comp_data in circuit_graph.items():
        if terminal in comp_data['terminals']:
            return comp_name
    raise ValueError(f'Terminal {terminal} doesn\'t exist')


def add_subsystem_components(circuit_graph, subsystem_list):
    circuit_graph_copy = deepcopy(circuit_graph)

    new_circuit_graph = {}
    terminal_map_agg = {}

    for component_name, component_metadata in circuit_graph_copy.items():
        if component_metadata['component_type'] in BASIC_COMPONENT_TYPES:
            new_circuit_graph[component_name] = component_metadata
            new_circuit_graph[component_name]['value'] = component_metadata[
                'value']
        else:
            subsystem_type = subsystem_list[
                component_metadata['subsystem']].get('subsystem_type')
            subsystem = SUBSYSTEM_TYPE_MAP[subsystem_type](circuit_graph,
                                                           subsystem_list)
            subgraphs, terminal_map = subsystem.make_subsystem_subgraphs(
                component_name)
            new_circuit_graph = {**new_circuit_graph, **subgraphs}
            terminal_map_agg = {**terminal_map_agg, **terminal_map}

    for _, terminal_new in terminal_map_agg.items():
        comp = new_circuit_graph[get_component_name_from_terminal(
            new_circuit_graph, terminal_new)]
        for terminal, connections in comp['connections'].items():
            for t in connections:
                if t in terminal_map_agg:
                    t = terminal_map_agg[t]
                connected_comp = new_circuit_graph[
                    get_component_name_from_terminal(new_circuit_graph, t)]
                _connections = connected_comp['connections'][t]
                for idx, _t in enumerate(_connections):
                    if _t in terminal_map_agg:
                        _connections[idx] = terminal_map_agg[_t]
                if terminal not in _connections:
                    _connections.append(terminal)

    return new_circuit_graph


def rename_ground_nodes(new_circuit_graph):
    circuit_graph_grounds = {}

    circuit_graph_grounds['GND'] = {}
    circuit_graph_grounds['GND']['label'] = 'ground'
    circuit_graph_grounds['GND']['subsystem'] = ''
    circuit_graph_grounds['GND']['component_type'] = 'ground'
    circuit_graph_grounds['GND']['value'] = {'capacitance': 0, 'inductance': 0}
    circuit_graph_grounds['GND']['terminals'] = ['GND_gnd']
    circuit_graph_grounds['GND']['connections'] = {'GND_gnd': []}

    for component, component_metadata in new_circuit_graph.items():
        if 'ground' in component:
            circuit_graph_grounds['GND']['connections']['GND_gnd'].extend(
                component_metadata['connections'][component + '_gnd'])
        else:
            circuit_graph_grounds[component] = component_metadata
            for terminal, connections in component_metadata[
                    'connections'].items():
                new_connections = []
                for connection in connections:
                    if 'ground' in connection:
                        new_connections.append('GND_gnd')
                    else:
                        new_connections.append(connection)
                circuit_graph_grounds[component]['connections'][
                    terminal] = new_connections

    circuit_graph_grounds['GND']['connections']['GND_gnd'] = list(
        set(circuit_graph_grounds['GND']['connections']['GND_gnd']))

    return circuit_graph_grounds


def get_capacitor_nodes(capacitance_list):
    nodes = []
    for key, values in capacitance_list.items():
        nodes.append(key)
        for value in values:
            nodes.append(value[0])

    return set(nodes)


def get_keep_nodes(subsystems):
    keep_nodes = []
    for subsystem in subsystems:
        if subsystem.sys_type == 'TL_RESONATOR':
            keep_nodes.extend(subsystem.nodes)

    return keep_nodes
