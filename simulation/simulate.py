import logging
import pandas as pd
import numpy as np
import pprint as pp
from operator import itemgetter
import json

from qiskit_metal.analyses.quantization.lom_core_analysis import CompositeSystem, Cell, Subsystem
from graph_conversion.graph_conversion import Circuit, get_capacitance_graph, map_sweeping_component_indices, SWEEP_NUM
# from jupyter import generate_notebook
from validation import validate_input, error_handling_wrapper

from .methods import *


@error_handling_wrapper
def simulate(sock, request):
    sock.send("SIMULATION STARTED")
    logging.info('Hitting simulate endpoint')

    req = request
    circuit_graph = req['Circuit Graph']
    subsystem_list = req['Subsystems']

    logging.info('Circuit graph and subsystems loaded')
    validate_input(circuit_graph, subsystem_list)

    # print('Circuit Graph:')
    # pp.pp(circuit_graph)

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
                make_cmat_df(
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

    # notebook = generate_notebook(composite_sys)
    # sim_results['notebook'] = notebook
    # sim_results['fQ_in_Ghz'] = hamiltonian_results['fQ_in_Ghz']

    # res_df = hamiltonian_results['chi_in_MHz'].to_dataframe()

    # sim_results['chi_in_MHz'] = json.loads(res_df.to_json(orient='records'))
    # sim_results = jsonify(sim_results)

    logging.info('Returning sim results')

    return sim_results
