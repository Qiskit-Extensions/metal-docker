from copy import deepcopy
import json

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
import pprint as pp

from qiskit_metal.analyses.quantization.lom_core_analysis import CompositeSystem, Cell, Subsystem
from graph_conversion.graph_conversion import Circuit
from jupyter import generate_notebook
from subsystems import TLResonator
from utils.utils import dict_to_float

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

CORS(app)

BASIC_COMPONENT_TYPES = [
    "capacitor",
    "inductor",
    "josephson_junction",
    'ground',
]

SUBSYSTEM_TYPE_MAP = {'TL_RESONATOR': TLResonator}


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


def _make_cmat_df(cmat, nodes):
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
            new_circuit_graph[component_name]['value'] = dict_to_float(
                component_metadata['value'])
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


@app.route('/simulate', methods=['POST'])
def simulate():
    try:

        req = request.get_json()
        circuit_graph = req['Circuit Graph']
        subsystem_list = req['Subsystems']

        print('Circuit Graph:')
        pp.pp(circuit_graph)

        circuit_graph_renamed = rename_ground_nodes(circuit_graph)
        new_circuit_graph = add_subsystem_components(circuit_graph_renamed,
                                                    subsystem_list)

        circuit_mvp = Circuit(new_circuit_graph)

        capacitance_graph = circuit_mvp.get_capacitance_graph()
        new_capacitance_graph = {}  #restructure data to work with LOM code
        for node, connections in capacitance_graph.items():
            new_capacitance_graph[node] = []
            for connection_node, capacitance in connections.items():
                new_capacitance_graph[node].append(
                    (connection_node, float(capacitance)))

        inductor_dict = circuit_mvp.get_inductance_branches()
        junction_dict = circuit_mvp.get_jj_branches()
        subsystem_map = circuit_mvp.get_subsystem_to_nodes_map()

        c_mats = []
        nodes = get_capacitor_nodes(new_capacitance_graph)
        inp_keys_index = pd.Index(nodes)
        c_mats.append(
            _make_cmat_df(adj_list_to_mat(inp_keys_index, new_capacitance_graph),
                        nodes))
        converted_capacitance = convert_netlist_to_maxwell(c_mats[0])

        subsystem_list = req['Subsystems']

        # Check subsystem_map to see if the pair of nodes is in the junction list and replace if it is
        for subsystem, nodes in subsystem_map.items():
            if tuple(nodes) in junction_dict:
                subsystem_list[subsystem]['nodes'] = [junction_dict[tuple(nodes)]]
            else:
                # If the node tuple is not a key in the junction list, remove the ground node, and set
                # 'nodes' for the subsystem in subsystem_list to the remaining nodes
                if subsystem is not None:
                    subsystem_list[subsystem]['nodes'] = [
                        n for n in nodes if n != 'GND_gnd'
                    ]

        subsystems = []
        for subsystem, subsystem_metadata in subsystem_list.items():
            subsystems.append(
                Subsystem(name=subsystem,
                        sys_type=subsystem_metadata['subsystem_type'],
                        nodes=subsystem_metadata['nodes'],
                        q_opts=subsystem_metadata.get('options', None)))

        cell_list = []
        cell_list.append(
            Cell(
                dict(node_rename={},
                    cap_mat=converted_capacitance,
                    ind_dict=inductor_dict,
                    jj_dict=junction_dict,
                    cj_dict={})))

        nodes_force_keep = get_keep_nodes(subsystems)

        composite_sys = CompositeSystem(subsystems=subsystems,
                                        cells=cell_list,
                                        grd_node='GND_gnd',
                                        nodes_force_keep=nodes_force_keep)

        hilbertspace = composite_sys.add_interaction()
        hamiltonian_results = composite_sys.hamiltonian_results(hilbertspace,
                                                                evals_count=30)

        notebook = generate_notebook(composite_sys)
        sim_results = {}
        sim_results['notebook'] = notebook
        sim_results['fQ_in_Ghz'] = hamiltonian_results['fQ_in_Ghz']

        res_df = hamiltonian_results['chi_in_MHz'].to_dataframe()

        sim_results['chi_in_MHz'] = json.loads(res_df.to_json(orient='records'))
        sim_results = jsonify(sim_results)

        return sim_results
    except Exception:
        return jsonify(error="oh crap...")
