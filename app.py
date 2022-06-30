import json

from flask_cors import CORS
from flask import Flask
from flask_sock import Sock

from simulation import simulate #rename simulate to lom_simulate?

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


CORS(app)

# pull in cahnges from connor-main for backend (this)
# pull in changes from curent-main for frontend