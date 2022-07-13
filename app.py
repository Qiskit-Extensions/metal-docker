from cmath import log
import json

from flask_cors import CORS

from flask import Flask
from flask_sock import Sock

from simulation import simulate, extractSweepSteps  #rename simulate to lom_simulate?

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
            # print(data['message'])
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


CORS(app)
