import json

from flask_cors import CORS
from flask import Flask
from flask_sock import Sock

from simulation import simulate

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
sock = Sock(app)


@sock.route('/simulate')
def sim(sock):
    while True:
        data = json.loads(sock.receive())
        print(data['type'] + ": " + str(data['message']))

        if data['type'] == "socket-connected":
            sock.send(json.dumps(data))

        elif data['type'] == "simulate":
            results = simulate(sock, data['message'])
            sock.send(json.dumps({"type": "sim_results", "message": results}))


# Create new socket routes following the example above

CORS(app)
