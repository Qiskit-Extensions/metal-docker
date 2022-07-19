from cmath import log
import json

from flask_cors import CORS

from flask import Flask, jsonify, request
from flask_sock import Sock

from simulation import simulate, extractSweepSteps  #rename simulate to lom_simulate?
from validation import error_handling_wrapper
from graph_conversion.graph_conversion import Circuit
from simulation import rename_ground_nodes
from graph_conversion.scqubits import sc_circuit_code

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
                json.dumps(
                    {
                        "type": "sim_results",
                        "message": {
                            "results": results,
                            "sweepSteps": sweepSteps
                        }
                    },
                    default=float))
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
    capacitor_dict, _ = circuit.get_capacitance_branches()
    inductor_dict, _ = circuit.get_inductance_branches()
    junction_dict = circuit.get_jj_branches()

    code_string = sc_circuit_code(capacitor_dict, inductor_dict, junction_dict)
    results = jsonify(code_string=code_string)
    return results


CORS(app)
