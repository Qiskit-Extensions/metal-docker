# metal-docker

This is a [Flask](https://flask.palletsprojects.com/en/2.1.x/) project.

# Setup

## Retrieve the code from GitHub

You could download the code as a zip file at the top of this page.
However we recommend investing time into setting up a proper git linkage, which will simplify the retrieval of code updates and your possible contributions back to the source code.

To do that, you will need to `git clone` this repository's main branch following one of two ways.

1. We recommend creating a root folder to store all the repositories required for this project.

2. Open any command line shell that has been configured with git. Navigate to your newly created root folder and execute the following command:

```sh
git clone https://github.com/qiskit-metal-cloud/metal-docker.git
```

2. Alternatively, you can download and use the user interface [GitHub Desktop GUI](https://desktop.github.com/) and refer to these [notes](https://help.github.com/en/desktop/contributing-to-projects/cloning-a-repository-from-github-to-github-desktop).

## Setup in a conda environment (preferred setup)

We recommend using the same conda environment for both the frontend and the backend.
If you did not yet install conda, please follow these [instructions](https://docs.conda.io/projects/conda/en/latest/user-guide/install/).

```sh
conda create --name <env_name>
conda activate <env_name>
```

## Install Qiskit Metal

Still in the same root folder, run

```sh
git clone https://github.com/Qiskit/qiskit-metal.git
```

Navigate to your local qiskit-metal repository

```sh
cd qiskit-metal
```

and update your conda environment

```sh
conda env update -n <env_name_exist> environment.yml
conda activate <env_name_exist>
python -m pip install --no-deps -e .
```

## Install the remaining dependencies

Naviagate to your local metal-docker repository and install the remaining dependencies.

```sh
pip install -r requirements.txt
```

We recommend using the same conda environment for both the frontend and the backend.

## Run the development server:

#### In debug mode in VS Code

Create a file named `.vscode/launch.json` at the root of your project with the following content:

```json
{
  // Use IntelliSense to learn about possible attributes.
  // Hover to view descriptions of existing attributes.
  // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Flask",
      "type": "python",
      "request": "launch",
      "module": "flask",
      "env": {
        "FLASK_APP": "app.py",
        "FLASK_ENV": "development",
        "FLASK_DEBUG": "1"
      },
      "args": ["run", "--no-debugger", "--no-reload"],
      "jinja": true
    }
  ]
}
```

Open the command palette (Ctrl+Shift+P on Windows/Linux, ⇧+⌘+P on macOS) and type `Python: Select Interpreter`. Select the conda environment you created or your desired environment. If your environment is not an option, add the environment as a kernel.

```
conda activate <env_name>
conda install ipykernel
ipython kernel install --user --name=<any_name_for_kernel>
```

Now go to the Debug panel (Ctrl+Shift+D on Windows/Linux, ⇧+⌘+D on macOS), select a launch configuration, then press F5 or select Debug: Start Debugging from the Command Palette to start your debugging session.

See the [qc-spice README](https://github.com/qiskit-metal-cloud/qc-spice/blob/pass-errors/README.md) for setup instructions for the frontend.
