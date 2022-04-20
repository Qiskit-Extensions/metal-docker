from flask import Flask, request
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
app = Flask(__name__)
CORS(app)


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


def dict_to_float(dictionary):
    new_dictionary = {}
    for key, value in dictionary.items():
        new_dictionary[key] = float(value)
    
    return new_dictionary


@app.route('/simulate', methods=['POST'])
def simulate():
    req = request.get_json()
    circuit_graph = req['Circuit Graph']
    
    print('Circuit Graph:')
    pp.pp(circuit_graph)

    not_hardcoded = False

    if not_hardcoded:
        new_circuit_graph = {}

        # TODO: There can be composite subsystems where user uploads info, so first get info 
        # from frontend for composite_subsystem
        for component_name, component_metadata in circuit_graph.items():
            if component_metadata['component_type'] != 'composite_subsystem':
                new_circuit_graph[component_name] = component_metadata
                new_circuit_graph[component_name]['value'] = dict_to_float(component_metadata['value'])
            else:
                new_circuit_graph['capacitor_2'] = {}
                new_circuit_graph['capacitor_2']['label'] = 'capacitor'
                new_circuit_graph['capacitor_2']['component_type'] = 'capacitor'
                new_circuit_graph['capacitor_2']['terminals'] = ['capacitor_2_1', 'capacitor_2_2']
                new_circuit_graph['capacitor_2']['value'] = dict_to_float(component_metadata['value'])
                new_circuit_graph['capacitor_2']['connections'] = {}
                new_circuit_graph['capacitor_2']['connections']['capacitor_2_1'] = ['capacitor_1_2']
                new_circuit_graph['capacitor_2']['connections']['capacitor_2_2'] = []
                new_circuit_graph['capacitor_2']['subsystem'] = component_metadata['subsystem']

        new_circuit_graph['capacitor_1']['connections']['capacitor_1_2'] = ['capacitor_2_1']
        new_circuit_graph['capacitor_2']['connections']['capacitor_2_2'] = ['GND_gnd']
        new_circuit_graph['josephson_junction_0']['value']['inductance'] = 10.0
    else:
        new_circuit_graph = circuit_graph

    print('new_circuit_graph:')
    pp.pp(new_circuit_graph)

    print('Subsystems:')
    pp.pp(req['Subsystems'])
    
    circuit_mvp = Circuit(new_circuit_graph)

    nodeT = circuit_mvp.get_nodes()
    capacitance_graph = circuit_mvp.get_capacitance_graph(nodeT)

    # Process capacitance graph to include self-capacitance for ground
    # for node,  capacitance in
    # {'n1': {'n1': 0, 'GND': 7, 'n2': 5}, 'n2':{'n2': 0, 'GND': 10}, 'GND': {'GND': 0}}

    new_capacitance_graph = {} #restructure data to work with LOM code
    for node, connections in capacitance_graph.items():
        new_capacitance_graph[node] = []
        for connection_node, capacitance in connections.items():
            new_capacitance_graph[node].append((connection_node, float(capacitance)))

    c_mats = []
    # nodes = new_capacitance_graph.keys()
    nodes = ['n1', 'capacitor_2', 'GND_gnd']
    inp_keys_index = pd.Index(nodes)
    c_mats.append(_make_cmat_df(adj_list_to_mat(inp_keys_index, new_capacitance_graph), nodes))
    converted_capacitance = convert_netlist_to_maxwell(c_mats[0])

    inductor_list = circuit_mvp.get_inductor_list(nodeT)
    junction_list = circuit_mvp.get_junction_list(nodeT)
    component_name_subsystem = circuit_mvp.get_component_name_subsystem()
    subsystem_map = circuit_mvp.get_subsystem_map(component_name_subsystem, nodeT)

    subsystem_list = req['Subsystems']

    # Check subsystem_map to see if the pair of nodes is in the junction list and replace if it is
    for subsystem, nodes in subsystem_map.items():
        if tuple(nodes) in junction_list[0].keys():
            subsystem_list[subsystem]['nodes'] = [junction_list[0][tuple(nodes)]]
        else:
            # If the node tuple is not a key in the junction list, remove the ground node, and set 
            # 'nodes' for the subsystem in subsystem_list to the remaining nodes
            if subsystem is not None:
                subsystem_list[subsystem]['nodes'] = [n for n in nodes if n!='GND_gnd']

    subsystems = []
    for subsystem, subsystem_metadata in subsystem_list.items():
        subsystems.append(Subsystem(name=subsystem, sys_type=subsystem_metadata['subsystem_type'],
                                    nodes=subsystem_metadata['nodes'], q_opts=subsystem_metadata.get('options', None)))

    cell_list = []
    cell_list.append(Cell(dict(node_rename={},
                            cap_mat=converted_capacitance,
                            ind_dict=inductor_list[0],
                            jj_dict=junction_list[0],
                            cj_dict={})))
    
    composite_sys = CompositeSystem(
        subsystems=subsystems,
        cells=cell_list,
        grd_node='GND_gnd',
        nodes_force_keep=['capacitor_2']
    )
    
    hilbertspace = composite_sys.add_interaction()
    hamiltonian_results = composite_sys.hamiltonian_results(hilbertspace, evals_count=30)
    hamiltonian_results['chi_in_MHz'] = hamiltonian_results['chi_in_MHz'].to_dataframe().to_dict()

    return hamiltonian_results
    # return '0'
