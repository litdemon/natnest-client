import asyncio
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import sys

# Attempt to import asyncssh for the mock SSH server
try:
    import asyncssh
except ImportError:
    print("⚠️  Warning: 'asyncssh' not found. Mock SSH server will not start.")
    print("    Run: pip install asyncssh")
    asyncssh = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mock-backend")

# --- Mock API Data ---
MOCK_USER = {
    "token": "mock-jwt-token",
    "email": "dev@natnest.site",
    "username": "tester",
    "subdomain": "tester"
}

# --- Mock HTTP API Server ---
class MockAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/version":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"version": "0.5.0", "url": "http://localhost:8000/natnest"}).encode())
        
        elif self.path.startswith("/api/domain/check"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"available": True, "domain": "tester", "suggestion": None}).encode())
            
        elif self.path == "/api/tunnels/me":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            # Simulate one active tunnel
            self.wfile.write(json.dumps({
                "tunnels": [{
                    "domain": "tester.natnest.site",
                    "port": 12345,
                    "is_mine": True
                }]
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/auth/device":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "device_code": "mock-device-code",
                "user_code": "MOCK-1234",
                "verification_url": "http://localhost:8000/verify",
                "interval": 1
            }).encode())
        
        elif self.path == "/api/auth/token":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(MOCK_USER).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        logger.info(f"HTTP: {format % args}")

def run_http_server():
    server = HTTPServer(('0.0.0.0', 8000), MockAPIHandler)
    logger.info("✅ Mock API Server running on http://localhost:8000")
    server.serve_forever()

# --- Mock SSH Tunnel Server ---
if asyncssh:
    class MockSSHServer(asyncssh.SSHServer):
        def connection_made(self, conn):
            logger.info(f"SSH: Connection received from {conn.get_extra_info('peername')[0]}")

        def auth_completed(self):
            logger.info("SSH: Authentication successful (mocked)")

        def public_key_auth_supported(self):
            return True

        def validate_public_key(self, username, key):
            return True  # Accept all keys for development

        def server_requested_client_forwarding(self, host, port):
            return True

        def connection_requested(self, dest_host, dest_port, orig_host, orig_port):
            return True

    async def run_ssh_server():
        # Generate a temporary host key if needed
        host_key = asyncssh.generate_private_key('ssh-ed25519')
        
        # We need to monkey-patch or handle the remote forwarding request
        # Simplified: just start the server
        await asyncssh.create_server(
            MockSSHServer, '', 2222,
            server_host_keys=[host_key],
            process_factory=lambda process: logger.info("SSH: Remote process requested")
        )
        logger.info("✅ Mock SSH Server running on port 2222")
        await asyncio.Event().wait()

# --- Main Entry Point ---
if __name__ == "__main__":
    # Start HTTP server in a separate thread
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Start SSH server in the main loop
    if asyncssh:
        try:
            asyncio.run(run_ssh_server())
        except KeyboardInterrupt:
            pass
    else:
        logger.warning("Mock SSH Server skipped. HTTP Server is still running.")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            pass
