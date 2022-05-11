class SubsystemGraph:
    def __init__(self, circuit_graph, subsystems):
        self.circuit_graph = circuit_graph
        self.subsystems = subsystems

    def make_subsystem_subgraphs(self, component_name):
        raise NotImplementedError()