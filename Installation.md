# Timetrack Application Installation

This guide provides the steps to install and run the `timetrack` command-line application on a new Linux environment.

## Requirements

- Python 3.12 or higher
- `pipx` (Python application installer)

## Installation Steps

1.  **Install `pipx`:**
    If you don't have `pipx` installed, you can install it with pip:

    ```bash
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    ```

2.  **Navigate to the Project Directory:**
    Open your terminal and change into the `project/` directory where this file is located.

    ```bash
    cd path/to/project/
    ```

3.  **Install the Application with `pipx`:**
    This command will install the `timetrack` application and its dependencies in an isolated environment, making the `timetrack` command available globally.

    ```bash
    pipx install --editable .
    ```

## Running the Application

Once the installation is complete, you can use the `timetrack` command from anywhere in your terminal.

To see the available commands and options, run:

```bash
timetrack --help
```

### Example Usage

-   **Start a new task:**
    ```bash
    timetrack start "My new task"
    ```

-   **Check the current status:**
    ```bash
    timetrack status
    ```

-   **Stop the current task:**
    ```bash
    timetrack stop
    ```

## Troubleshooting

-   **`timetrack: command not found`**:
    This error can occur if the `pipx` installation path is not in your system's `PATH`. You may need to add it. For most Linux systems, this is `~/.local/bin`. You can also run `pipx ensurepath` to automatically add it to your path.

-   **Module Not Found Errors**:
    If you encounter errors like `ModuleNotFoundError`, it likely means the dependencies are not installed correctly. Run `pipx install --editable .` again to be sure.
