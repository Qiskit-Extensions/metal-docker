from copy import deepcopy
import json
from itertools import product
from operator import itemgetter

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import pandas as pd
import numpy as np
import pprint as pp

from qiskit_metal.analyses.quantization.lom_core_analysis import CompositeSystem, Cell, Subsystem
from graph_conversion.graph_conversion import Circuit, get_capacitance_graph, map_sweeping_component_indices, SWEEP_NUM
from jupyter import generate_notebook
from subsystems import TLResonator
from utils.utils import dict_to_float
from validation import validate_input, error_handling_wrapper

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
        for n2, w in adj_list[n1]:
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


@app.route('/simulate', methods=['POST'])
@error_handling_wrapper
def simulate():
    logging.info('Hitting simulate endpoint')
    req = request.get_json()
    circuit_graph = req['Circuit Graph']
    subsystem_list = req['Subsystems']

    logging.info('Circuit graph and subsystems loaded')
    validate_input(circuit_graph, subsystem_list)

    circuit_graph_renamed = rename_ground_nodes(circuit_graph)
    new_circuit_graph = add_subsystem_components(circuit_graph_renamed,
                                                 subsystem_list)

    circuit_mvp = Circuit(new_circuit_graph)

    capacitor_dict, sweeping_caps = circuit_mvp.get_capacitance_branches()
    inductor_dict, sweeping_inds = circuit_mvp.get_inductance_branches()
    junction_dict = circuit_mvp.get_jj_branches()

    subsystem_map = circuit_mvp.get_subsystem_to_nodes_map()
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

    capacitor_nodes = capacitor_dict.keys()
    capacitor_vals_lists = sweep_dict_to_combo_list(capacitor_dict)
    capacitor_comp_indices_lists = sweep_dict_to_combo_list(
        map_sweeping_component_indices(capacitor_nodes, sweeping_caps))

    inductor_nodes = inductor_dict.keys()
    inductor_vals_lists = sweep_dict_to_combo_list(inductor_dict)
    inductor_comp_indices_lists = sweep_dict_to_combo_list(
        map_sweeping_component_indices(inductor_nodes, sweeping_inds))

    sweep_table = []
    for inductor_vals, inductor_comp_indices in zip(
            inductor_vals_lists, inductor_comp_indices_lists):
        ind_sweep_key = {}
        for _ind_val_idx, nodes in zip(inductor_comp_indices, inductor_nodes):
            if nodes in sweeping_inds:
                ind_sweep_comps = sweeping_inds[nodes]
                for _ind_val_ii, ind_sweep_comp in zip(_ind_val_idx,
                                                       ind_sweep_comps):
                    lo = new_circuit_graph[ind_sweep_comp]['value'][
                        'inductanceLo']
                    hi = new_circuit_graph[ind_sweep_comp]['value'][
                        'inductanceHi']
                    sweep_vals = np.linspace(lo, hi, SWEEP_NUM)
                    ind_sweep_key[f'{ind_sweep_comp}_inductance'] = sweep_vals[
                        _ind_val_ii]

        ind_branches = dict(zip(inductor_nodes, inductor_vals))

        for capacitor_vals, capacitor_comp_indices in zip(
                capacitor_vals_lists, capacitor_comp_indices_lists):

            sweep_entry = ind_sweep_key.copy()
            for _cap_val_idx, nodes in zip(capacitor_comp_indices,
                                           capacitor_nodes):
                if nodes in sweeping_caps:
                    cap_sweep_comps = sweeping_caps[nodes]
                    for _cap_val_ii, cap_sweep_comp in zip(
                            _cap_val_idx, cap_sweep_comps):
                        lo = new_circuit_graph[cap_sweep_comp]['value'][
                            'capacitanceLo']
                        hi = new_circuit_graph[cap_sweep_comp]['value'][
                            'capacitanceHi']
                        sweep_vals = np.linspace(lo, hi, SWEEP_NUM)
                        sweep_entry[
                            f'{cap_sweep_comp}_capacitance'] = sweep_vals[
                                _cap_val_ii]

            cap_branch = dict(zip(capacitor_nodes, capacitor_vals))
            capacitance_graph = get_capacitance_graph(cap_branch)

            c_mats = []
            nodes = get_capacitor_nodes(capacitance_graph)
            inp_keys_index = pd.Index(nodes)
            c_mats.append(
                _make_cmat_df(
                    adj_list_to_mat(inp_keys_index, capacitance_graph), nodes))
            converted_capacitance = convert_netlist_to_maxwell(c_mats[0])

            cell_list = []
            cell_list.append(
                Cell(
                    dict(node_rename={},
                         cap_mat=converted_capacitance,
                         ind_dict=ind_branches,
                         jj_dict=junction_dict,
                         cj_dict={})))

            nodes_force_keep = get_keep_nodes(subsystems)

            composite_sys = CompositeSystem(subsystems=subsystems,
                                            cells=cell_list,
                                            grd_node='GND_gnd',
                                            nodes_force_keep=nodes_force_keep)

            hilbertspace = composite_sys.add_interaction()
            hamiltonian_results = composite_sys.hamiltonian_results(
                hilbertspace, evals_count=30, print_info=False)

            sweep_entry['fQ_in_Ghz'] = hamiltonian_results['fQ_in_Ghz']
            res_df = hamiltonian_results['chi_in_MHz'].to_dataframe()
            sweep_entry['chi_in_MHz'] = json.loads(
                res_df.to_json(orient='records'))

            sweep_table.append(sweep_entry)

    sim_results = {}
    sim_results['table'] = sweep_table
    sim_results['sweep_keys'] = {}

    sweep_keys = sweep_table[0].keys()
    sweep_keys = [
        k for k in sweep_keys if k not in ['fQ_in_Ghz', 'chi_in_MHz']
    ]
    if sweep_keys:
        sweep_table.sort(key=itemgetter(*sweep_keys))
        for key in sweep_keys:
            component_name = "_".join(
                "{}".format(k)
                for k in key.split('_')[:len(key.split('_')) - 1])
            component_sweep_key = key.split("_")[len(key.split("_")) - 1]
            sim_results['sweep_keys'][key] = {
                'component_name':
                component_name,
                'min':
                circuit_graph[component_name]["value"][''.join(
                    [component_sweep_key, "Lo"])],
                'max':
                circuit_graph[component_name]["value"][''.join(
                    [component_sweep_key, "Hi"])],
            }
    # pp.pp(sim_results['sweep_keys'])

    # notebook = generate_notebook(composite_sys)
    # sim_results['notebook'] = notebook
    # sim_results['fQ_in_Ghz'] = hamiltonian_results['fQ_in_Ghz']

    # res_df = hamiltonian_results['chi_in_MHz'].to_dataframe()

    # sim_results['chi_in_MHz'] = json.loads(res_df.to_json(orient='records'))
    sim_results = jsonify(sim_results)

    logging.info('Returning sim results')

    return sim_results
