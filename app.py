from flask import Flask, request
from qiskit_metal.analyses.quantization.lumped_capacitive import load_q3d_capacitance_matrix
from qiskit_metal.analyses.quantization.lom_core_analysis import CompositeSystem, Cell, Subsystem

from scipy.constants import speed_of_light as c_light
import pandas as pd
import numpy as np
from collections import defaultdict
import json
from ast import literal_eval

app = Flask(__name__)


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
    print(type(cg.C_k.to_dataframe().to_json()))
    return cg.C_k.to_dataframe().to_json()


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
    return {literal_eval(k): v for k, v in serialized_list.items()}


@app.route('/simulate', methods=['POST'])
def simulate():
    adjacency_list = json.loads(request.json['adjacency_list'])
    node_rename_list = json.loads(request.json['node_rename_list'])
    ind_dict_list = json.loads(request.json['ind_dict_list'])
    jj_dict_list = json.loads(request.json['jj_dict_list'])
    cj_dict_list = json.loads(request.json['cj_dict_list'])
    subsystem_list = json.loads(request.json['subsystem_list'])

    c_mats = []
    for adjacency in adjacency_list:
        nodes = adjacency.keys()
        inp_keys_index = pd.Index(nodes)
        c_mats.append(_make_cmat_df(adj_list_to_mat(inp_keys_index, adjacency), nodes))

    cell_list = []
    for ii in range(len(node_rename_list)):
        cell_list.append(Cell(dict(node_rename=node_rename_list[ii],
                              cap_mat=c_mats[ii],
                              ind_dict=deserialize_tuple_dict_list(json.loads(ind_dict_list[ii])),
                              jj_dict=deserialize_tuple_dict_list(json.loads(jj_dict_list[ii])),
                              cj_dict=deserialize_tuple_dict_list(json.loads(cj_dict_list[ii])))))

    subsystems = []
    for subsystem in subsystem_list:
        if 'q_opts' in subsystem:
            subsystems.append(Subsystem(name=subsystem['name'], sys_type=subsystem['sys_type'],
                                        nodes=subsystem['nodes'], q_opts=subsystem['q_opts']))
        else:
            subsystems.append(Subsystem(name=subsystem['name'], sys_type=subsystem['sys_type'],
                                        nodes=subsystem['nodes']))

    composite_sys = CompositeSystem(
        subsystems=subsystems,
        cells=cell_list,
        grd_node='ground_main_plane',
        nodes_force_keep=['readout_alice', 'readout_bob']
    )

    hilbertspace = composite_sys.add_interaction()
    hamiltonian_results = composite_sys.hamiltonian_results(hilbertspace, evals_count=30)
    hamiltonian_results['chi_in_MHz'] = hamiltonian_results['chi_in_MHz'].to_dataframe().to_dict()

    return hamiltonian_results
