from pyEPR.calcs.convert import Convert


def _node_name_to_num(node):
    return int(node[1:])


def sc_circuit_code(cap_dict, ind_dict, jj_dict):
    branches = dict()
    for (node_start, node_end), val in ind_dict.items():
        El = Convert.Ej_from_Lj(val)
        node_start_num = _node_name_to_num(node_start)
        node_end_num = _node_name_to_num(node_end)
        if (node_start, node_end) in jj_dict:
            branches[(node_start_num, node_end_num)] = [
                'JJ', node_start_num, node_end_num, El
            ]
        else:
            branches[(node_start_num,
                      node_end_num)] = ['L', node_start_num, node_end_num, El]

    for (node_start, node_end), val in cap_dict.items():
        Ec = Convert.Ec_from_Cs(val)
        node_start_num = _node_name_to_num(node_start)
        node_end_num = _node_name_to_num(node_end)
        if (node_start, node_end) in jj_dict:
            branches[(node_start_num, node_end_num)].append(Ec)
        else:
            branches[(node_start_num,
                      node_end_num)] = ['C', node_start_num, node_end_num, Ec]

    code_string = '''circuit_yaml = """# circuit branches'''