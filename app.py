from cmath import log
import json

from flask_cors import CORS

from flask import Flask, jsonify, request
from flask_sock import Sock

from simulation import simulate, extractSweepSteps  #rename simulate to lom_simulate?
from validation import error_handling_wrapper
from graph_conversion.graph_conversion import Circuit
from simulation import rename_ground_nodes

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
sock = Sock(app)


@sock.route('/simulate')
def sim(sock):
    while True:
        data = json.loads(sock.receive())

        if data['type'] == "socket-connected":
            sock.send(json.dumps(data))

        elif data['type'] == "simulate":
            graphObj = data['message']
            sweepSteps = extractSweepSteps(graphObj)
            results = simulate(sock, graphObj, sweepSteps)
            sock.send(
                json.dumps({
                    "type": "sim_results",
                    "message": {
                        "results": results,
                        "sweepSteps": sweepSteps
                    }
                }))
            sock.close()
            break


@app.route('/test', methods=['GET'])
def test():
    results = jsonify(message='success!')
    return results


@app.route('/get_circuit_code', methods=['POST'])
@error_handling_wrapper
def get_circuit_code():

    req = request.get_json()
    circuit_graph = req['Circuit Graph']
    circuit_library = req['Circuit Library']
    circuit_graph_renamed = rename_ground_nodes(circuit_graph)

    circuit = Circuit(circuit_graph_renamed)
    capacitor_dict = circuit.get_capacitance_branches()
    inductor_dict = circuit.get_inductance_branches()
    junction_dict = circuit.get_jj_branches()

    code_string = '''zp_yaml = """# zero-pi circuit
    branches:
    - ["JJ", 1, 2, EJ=10, 20]
    - ["JJ", 3, 4, EJ, 20]
    - ["L", 2, 3, 0.008]
    - ["L", 4, 1, 0.008]
    - ["C", 1, 3, 0.02]
    - ["C", 2, 4, 0.02]
    """
    '''

    results = jsonify(code_string=code_string)
    return results


CORS(app)
