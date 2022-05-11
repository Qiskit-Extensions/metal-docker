from copy import deepcopy

from flask import Flask, request, jsonify
from flask_cors import CORS
from qiskit_metal.analyses.quantization.lumped_capacitive import load_q3d_capacitance_matrix
from qiskit_metal.analyses.quantization.lom_core_analysis import CompositeSystem, Cell, Subsystem

from scipy.constants import speed_of_light as c_light
import pandas as pd
import numpy as np
from collections import defaultdict
import json
from ast import literal_eval
from graph_conversion.graph_conversion.graph_conversion import CircuitComponent, Circuit, Subsystem2
import pprint as pp
from time import time

from jupyter import generate_notebook
from subsystems import TLResonator
from utils.utils import dict_to_float

app = Flask(__name__)
CORS(app)

BASIC_COMPONENT_TYPES = [
    "capacitor",
    "inductor",
    "josephson_junction",
    'ground',
]

SUBSYSTEM_TYPE_MAP = {'TL_RESONATOR': TLResonator}


def demo(print_output=True):
    # alice cap matrix
    path1 = './Q1_TwoTransmon_CapMatrix.txt'
    ta_mat, _, _, _ = load_q3d_capacitance_matrix(path1)

    # bob cap matrix
    path2 = './Q2_TwoTransmon_CapMatrix.txt'
    tb_mat, _, _, _ = load_q3d_capacitance_matrix(path2)

    # cell 1: transmon Alice cell
    opt1 = dict(
        node_rename={
            'coupler_connector_pad_Q1': 'coupling',
            'readout_connector_pad_Q1': 'readout_alice'
        },
        cap_mat=ta_mat,
        ind_dict={('pad_top_Q1', 'pad_bot_Q1'):
                  10},  # junction inductance in nH
        jj_dict={('pad_top_Q1', 'pad_bot_Q1'): 'j1'},
        cj_dict={('pad_top_Q1', 'pad_bot_Q1'):
                 2},  # junction capacitance in fF
    )
    cell_1 = Cell(opt1)

    # cell 2: transmon Bob cell
    opt2 = dict(
        node_rename={
            'coupler_connector_pad_Q2': 'coupling',
            'readout_connector_pad_Q2': 'readout_bob'
        },
        cap_mat=tb_mat,
        ind_dict={('pad_top_Q2', 'pad_bot_Q2'):
                  12},  # junction inductance in nH
        jj_dict={('pad_top_Q2', 'pad_bot_Q2'): 'j2'},
        cj_dict={('pad_top_Q2', 'pad_bot_Q2'):
                 2},  # junction capacitance in fF
    )
    cell_2 = Cell(opt2)

    # subsystem 1: transmon Alice
    transmon_alice = Subsystem(name='transmon_alice',
                               sys_type='TRANSMON',
                               nodes=['j1'])

    # subsystem 2: transmon Bob
    transmon_bob = Subsystem(name='transmon_bob',
                             sys_type='TRANSMON',
                             nodes=['j2'])

    # subsystem 3: Alice readout resonator
    q_opts = dict(
        f_res=8,  # resonator dressed frequency in GHz
        Z0=50,  # characteristic impedance in Ohm
        vp=0.404314 * c_light  # phase velocity
    )
    res_alice = Subsystem(name='readout_alice',
                          sys_type='TL_RESONATOR',
                          nodes=['readout_alice'],
                          q_opts=q_opts)

    # subsystem 4: Bob readout resonator
    q_opts = dict(
        f_res=7.6,  # resonator dressed frequency in GHz
        Z0=50,  # characteristic impedance in Ohm
        vp=0.404314 * c_light  # phase velocity
    )
    res_bob = Subsystem(name='readout_bob',
                        sys_type='TL_RESONATOR',
                        nodes=['readout_bob'],
                        q_opts=q_opts)

    composite_sys = CompositeSystem(
        subsystems=[transmon_alice, transmon_bob, res_alice, res_bob],
        cells=[cell_1, cell_2],
        grd_node='ground_main_plane',
        nodes_force_keep=['readout_alice', 'readout_bob'])

    cg = composite_sys.circuitGraph()
    if print_output:
        print(cg)
    return cg


@app.route('/')
def hello_world():
    cg = demo(print_output=False)
    return cg.C_k.to_dataframe().to_json()


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


def _df_cmat_to_adj_list(df_cmat: pd.DataFrame):
    """
    generate an adjacency list from a capacitance matrix in a dataframe
    """
    nodes = df_cmat.columns.values
    vals = df_cmat.values
    graph = defaultdict(list)
    for ii, node in enumerate(nodes):
        for jj in range(ii, len(nodes)):
            graph[node].append((nodes[jj], vals[ii, jj]))
    return graph


def deserialize_tuple_dict_list(serialized_list):
    print('serialized_list:', serialized_list)
    print('items:', serialized_list.items())
    data = {literal_eval(k): v for k, v in serialized_list.items()}
    print(data)
    return data


def convert_netlist_to_maxwell(df):
    df_new = df.copy()
    for key in df.keys():
        df_new[key][key] = -sum(df[key].values)
        df_new[key] = -df_new[key]
    return df_new


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

    for _, comp_data in new_circuit_graph.items():
        connections = comp_data['connections']
        for terminal, connected_terminals in connections.items():
            connected_terminals_new = []
            for term_orig in connected_terminals:
                if term_orig in terminal_map_agg:
                    connected_terminals_new.extend(terminal_map_agg[term_orig])
                else:
                    connected_terminals_new.append(term_orig)
            connections[terminal] = connected_terminals_new

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
    req = request.get_json()
    circuit_graph = req['Circuit Graph']
    subsystem_list = req['Subsystems']

    print('Circuit Graph:')
    pp.pp(circuit_graph)

    new_circuit_graph = add_subsystem_components(circuit_graph, subsystem_list)
    circuit_graph_grounds = rename_ground_nodes(new_circuit_graph)

    circuit_mvp = Circuit(circuit_graph_grounds)

    nodeT = circuit_mvp.get_nodes()
    capacitance_graph = circuit_mvp.get_capacitance_graph(nodeT)

    new_capacitance_graph = {}  #restructure data to work with LOM code
    for node, connections in capacitance_graph.items():
        new_capacitance_graph[node] = []
        for connection_node, capacitance in connections.items():
            new_capacitance_graph[node].append(
                (connection_node, float(capacitance)))

    c_mats = []
    nodes = get_capacitor_nodes(new_capacitance_graph)
    inp_keys_index = pd.Index(nodes)
    c_mats.append(
        _make_cmat_df(adj_list_to_mat(inp_keys_index, new_capacitance_graph),
                      nodes))
    converted_capacitance = convert_netlist_to_maxwell(c_mats[0])

    inductor_dict = circuit_mvp.get_inductor_dict(nodeT)
    junction_dict = circuit_mvp.get_junction_dict(nodeT)
    component_name_subsystem = circuit_mvp.get_component_name_subsystem()
    subsystem_map = circuit_mvp.get_subsystem_map(component_name_subsystem,
                                                  nodeT)

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
