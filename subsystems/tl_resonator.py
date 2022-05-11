from utils.utils import dict_to_float
from .base import SubsystemGraph

# {
#     "label": "left_side_loaded_tl_resonator",
#     "component_type": "left_side_loaded_tl_resonator",
#     "terminals": [
#         "left_side_loaded_tl_resonator_16510409290088_1",
#         "left_side_loaded_tl_resonator_16510409290088_2"
#     ],
#     "value": {
#         "capacitance": 50,
#         "inductance": 0
#     },
#     "connections": {
#         "left_side_loaded_tl_resonator_16510409290088_1": [
#             "capacitor_16510409175186_2"
#         ],
#         "left_side_loaded_tl_resonator_16510409290088_2": []
#     },
#     "subsystem": "alice_readout"
# }


class TLResonator(SubsystemGraph):
    def make_subsystem_subgraphs(self, component_name):
        """create the subgraphs extracted from a component's parameters, which
        will be added to the circuit_graph

        Args:
            component_name (string): name of the component from which a subgraph is created
        """
        subgraphs = {}
        subsys_name = self.circuit_graph[component_name]['subsystem']
        loading_cap_name = f'capacitor_{subsys_name}'
        subgraphs[loading_cap_name] = {}
        subgraphs[loading_cap_name]['label'] = 'capacitor'
        subgraphs[loading_cap_name]['component_type'] = 'capacitor'
        subgraphs[loading_cap_name]['terminals'] = [
            f'{loading_cap_name}_1', f'{loading_cap_name}_2'
        ]
        subgraphs[loading_cap_name]['value'] = dict_to_float(
            self.circuit_graph[component_name]['value'])
        subgraphs[loading_cap_name]['subsystem'] = subsys_name

        connections = {}
        connections[f'{loading_cap_name}_1'] = self.circuit_graph[
            component_name]['connections'][f'{component_name}_1']
        connections[f'{loading_cap_name}_2'] = ['GND_gnd']
        subgraphs[loading_cap_name]['connections'] = connections

        terminal_map = {
            f'{component_name}_1': [f'{loading_cap_name}_1'],
            f'{component_name}_2': [f'{loading_cap_name}_2']
        }

        return subgraphs, terminal_map
