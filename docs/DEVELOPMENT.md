# NatNest Client Standalone Development Guide

This document explains how to set up a development environment for the NatNest CLI client without needing the entire backend infrastructure (api-server, tunnel-server, postgres, etc.).

## 1. Prerequisites

- **Python 3.9+**
- **SSH Client**: `ssh` command must be available in your PATH.
- **Mock Backend**: Since the client relies on a server for authentication and tunnel coordination, you need a mock server for local development.

## 2. Environment Setup

1. **Install Dependencies**:
   ```bash
   cd client
   pip install -r requirements.txt
   ```

2. **Configuration**:
   The client uses the `NATNEST_SERVER_URL` environment variable to locate the API server. For local development, set this to your mock server (default: `http://localhost:8000`).

   ```bash
   export NATNEST_SERVER_URL="http://localhost:8000"
   ```

## 3. Running with Mock Backend

We provide a lightweight mock backend that simulates both the REST API and the SSH Tunnel Server.

1. **Start Mock Server**:
   ```bash
   python docs/mock_backend.py
   ```
   *This will start a FastAPI/Flask-like server on port 8000 and a mock SSH server on port 2222.*

2. **Initialize Client (Setup)**:
   ```bash
   python main.py setup
   ```
   *Follow the instructions to "authenticate" against the mock server.*

3. **Start a Tunnel**:
   ```bash
   python main.py 8080
   ```
   *The client will connect to the mock SSH server and display a mock public URL.*

## 4. Key Client Components

- `main.py`: The entry point for the CLI. Handles commands, configuration, and process management.
- `ensure_ssh_key()`: Manages the local identity key in `~/.natnest/id_ed25519`.
- `run_watchdog()`: A background loop that ensures the SSH tunnel stays alive.
- `start_tunnel()`: Coordinates with the API for domain availability and launches the SSH process.

## 5. Building the Binary

The client is distributed as a single-file binary using PyInstaller.

```bash
./build.sh
```
*The resulting binary will be in `client/dist/natnest`.*

## 6. Testing Strategy

- **API Mocking**: Use the provided `mock_backend.py` to test different API responses (errors, version updates, domain collisions).
- **SSH Simulation**: The mock SSH server validates how the client handles connection drops and port assignments.
- **Unit Tests**: Add tests to `tests/` (if available) or create a new test suite that mocks the `requests` and `subprocess` calls.
