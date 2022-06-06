from flask import Flask, jsonify
from flask_cors import CORS
import numpy as np
from tqdm import tqdm
from scipy import linalg

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

CORS(app)


@app.route('/simulate', methods=['GET'])
def simulate():

    N = 600
    A = np.random.randint(0, 10, (45, 45))
    for _ in tqdm(range(N)):
        _result = linalg.eigh(A, eigvals_only=True)

    sim_results = jsonify(result=_result)

    return sim_results
