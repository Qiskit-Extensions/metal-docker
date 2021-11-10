from qiskit_metal.analyses.quantization.lumped_capacitive import load_q3d_capacitance_matrix
from qiskit_metal.analyses.quantization.lom_core_analysis import CompositeSystem, Cell, Subsystem

from scipy.constants import speed_of_light as c_light


def demo():
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
    print(cg)


def main():
    demo()


if __name__ == '__main__':
    main()