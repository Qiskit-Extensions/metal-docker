import io
import json

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

_SUPPORTED_SUBSYSTEMS = {
    "TRANSMON": {
        'params': ['EJ', 'EC', 'ng', 'ncut'],
        'sweep_params': {
            'ng': {
                'sweep_name': 'ng_list',
                'sweep_vals': 'np.linspace(-2, 2, 220)'
            }
        }
    }
}

KERNEL = 'python'


def _extract_params(quantum_sys, param_keys):
    params = {}
    for param in param_keys:
        params[param] = getattr(quantum_sys, param)
    return params


def generate_notebook(composite_sys):

    nb = nbf.v4.new_notebook()
    nb_cells = []

    import_section = "'exec(%matplotlib inline)'\n" \
                     'import numpy as np\n'\
                     'import scqubits as scq'

    nb_cells.append(nbf.v4.new_code_cell(import_section))

    for subsystem in composite_sys.subsystems:
        sys_name = subsystem.name
        sys_type = subsystem.sys_type
        quantum_sys = subsystem.quantum_system

        if sys_type not in _SUPPORTED_SUBSYSTEMS:
            continue

        params = _extract_params(quantum_sys,
                                 _SUPPORTED_SUBSYSTEMS[sys_type]['params'])
        code = f"""{sys_name} = scq.Transmon(**{params})"""
        nb_cells.append(nbf.v4.new_code_cell(code))

        title = f"""### Computing and plotting eigenenergies and wavefunctions for {sys_type}: {sys_name}"""
        nb_cells.append(nbf.v4.new_markdown_cell(title))

        for sweep_param, sweep_details in _SUPPORTED_SUBSYSTEMS[sys_type][
                'sweep_params'].items():

            subtitle = f"""#### Plot energy levels vs {sweep_param}"""
            nb_cells.append(nbf.v4.new_markdown_cell(subtitle))

            param_sweep = f"{sweep_details['sweep_name']} = {sweep_details['sweep_vals']}\n" \
                          f"fig, axes = {sys_name}.plot_evals_vs_paramvals(\'{sweep_param}\', {sweep_details['sweep_name']}, evals_count=6, subtract_ground=False)"
            nb_cells.append(nbf.v4.new_code_cell(param_sweep))

        subtitle = """#### Phase-basis wavefunction for eigenstate"""
        nb_cells.append(nbf.v4.new_markdown_cell(subtitle))

        wavefunction = f"""_ = {sys_name}.plot_wavefunction(esys=None, which=(0,1,2,3,8), mode='real')"""
        nb_cells.append(nbf.v4.new_code_cell(wavefunction))

    nb['cells'] = nb_cells
    ep = ExecutePreprocessor(timeout=600, kernel_name=KERNEL)
    _ = ep.preprocess(nb)

    f = io.StringIO()
    nbf.write(nb, f)
    f.seek(0)

    return json.load(f)