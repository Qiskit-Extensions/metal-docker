import requests
from collections import defaultdict
import json
from flask import request
import pprint as pp
from scipy.constants import speed_of_light as c_light


def serialize_tuple_dict_list(tuple_dict_list):
    return [json.dumps({str(k): v for k, v in ind_dict.items()}) for ind_dict in tuple_dict_list]


adjacency_list = [{"coupler_connector_pad_Q1": [("coupler_connector_pad_Q1", 59.19879),
                                                ("ground_main_plane", -37.28461),
                                                ("pad_bot_Q1", -2.00818),
                                                ("pad_top_Q1", -19.10774),
                                                ("readout_connector_pad_Q1", -0.22976)],
                   "ground_main_plane": [("ground_main_plane", 246.32877),
                                         ("pad_bot_Q1", -39.78914),
                                         ("pad_top_Q1", -39.86444),
                                         ("readout_connector_pad_Q1", -37.29686)],
                   "pad_bot_Q1": [("pad_bot_Q1", 93.05074),
                                  ("pad_top_Q1", -30.61038),
                                  ("readout_connector_pad_Q1", -19.21994)],
                   "pad_top_Q1": [("pad_top_Q1", 92.99428),
                                  ("readout_connector_pad_Q1", -2.00897)],
                   "readout_connector_pad_Q1": [("readout_connector_pad_Q1", 59.32747)]},
                  {"coupler_connector_pad_Q2": [("coupler_connector_pad_Q2", 64.51526),
                                                ("ground_main_plane", -38.62522),
                                                ("pad_bot_Q2", -2.1826),
                                                ("pad_top_Q2", -22.9334),
                                                ("readout_connector_pad_Q2", -0.21522)],
                   "ground_main_plane": [("ground_main_plane", 267.39714),
                                         ("pad_bot_Q2", -49.28298),
                                         ("pad_top_Q2", -49.29706),
                                         ("readout_connector_pad_Q2", -38.67319)],
                   "pad_bot_Q2": [("pad_bot_Q2", 121.37641),
                                  ("pad_top_Q2", -45.23961),
                                  ("readout_connector_pad_Q2", -23.06437)],
                   "pad_top_Q2": [("pad_top_Q2", 121.23898),
                                  ("readout_connector_pad_Q2", -2.17691)],
                   "readout_connector_pad_Q2": [("readout_connector_pad_Q2", 64.70083)]},
                  {"pad_top_Q1": [("pad_bot_Q1", -2), ("pad_top_Q1", 2)],
                   "pad_bot_Q1": [("pad_bot_Q1", 2)]},
                  {"pad_top_Q2": [("pad_bot_Q2", -2), ("pad_top_Q2", 2)],
                   "pad_bot_Q2": [("pad_bot_Q2", 2)]}]

node_rename_list = [{'coupler_connector_pad_Q1': 'coupling', 'readout_connector_pad_Q1': 'readout_alice'},
                    {'coupler_connector_pad_Q2': 'coupling', 'readout_connector_pad_Q2': 'readout_bob'}]
ind_dict_list = [{('pad_top_Q1', 'pad_bot_Q1'): 10}, {('pad_top_Q2', 'pad_bot_Q2'): 12}]
jj_dict_list = [{('pad_top_Q1', 'pad_bot_Q1'): 'j1'}, {('pad_top_Q2', 'pad_bot_Q2'): 'j2'}]
cj_dict_list = [{('pad_top_Q1', 'pad_bot_Q1'): 2}, {('pad_top_Q2', 'pad_bot_Q2'): 2}]

subsystem_list = [{'name': 'transmon_alice', 'sys_type': 'TRANSMON', 'nodes': ['j1']},
                  {'name': 'transmon_bob', 'sys_type': 'TRANSMON', 'nodes': ['j2']},
                  {'name': 'readout_alice', 'sys_type': 'TL_RESONATOR', 'nodes': ['readout_alice'],
                   'q_opts': {'f_res': 8, 'Z0': 50, 'vp': 0.404314 * c_light}},
                  {'name': 'readout_bob', 'sys_type': 'TL_RESONATOR', 'nodes': ['readout_bob'],
                  'q_opts': {'f_res': 7.6, 'Z0': 50, 'vp': 0.404314 * c_light}}]

front_end_data = {'adjacency_list': json.dumps(adjacency_list),
                  'node_rename_list': json.dumps(node_rename_list),
                  'ind_dict_list': json.dumps(serialize_tuple_dict_list(ind_dict_list)),
                  'jj_dict_list': json.dumps(serialize_tuple_dict_list(jj_dict_list)),
                  'cj_dict_list': json.dumps(serialize_tuple_dict_list(cj_dict_list)),
                  'subsystem_list': json.dumps(subsystem_list)}

resp_data = requests.post('http://localhost:5000/simulate', json=front_end_data)

print('Hamiltonian results:')
pp.pp(resp_data.json())
