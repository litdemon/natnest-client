# NatNest Client-Backend API Specification

This document lists the HTTP API endpoints the NatNest client expects from the backend.

## 1. Versioning

### `GET /api/version`
Used to check for updates.
- **Response (200 OK)**:
  ```json
  {
    "version": "0.5.0",
    "url": "https://natnest.site/bin/linux/natnest"
  }
  ```

## 2. Authentication (Device Flow)

### `POST /api/auth/device`
Initiates the Google OAuth device flow.
- **Request Body**:
  ```json
  { "public_key": "ssh-ed25519 AAA..." }
  ```
- **Response (200 OK)**:
  ```json
  {
    "device_code": "...",
    "user_code": "ABCD-EFGH",
    "verification_url": "https://natnest.site/auth/device",
    "interval": 5
  }
  ```

### `POST /api/auth/token`
Polls for authentication completion.
- **Request Body**:
  ```json
  { "device_code": "..." }
  ```
- **Response (200 OK)**:
  ```json
  {
    "token": "JWT_TOKEN",
    "email": "user@example.com",
    "username": "user123",
    "subdomain": "user123"
  }
  ```
- **Response (400 Bad Request)**:
  ```json
  { "error": "authorization_pending" }
  ```

## 3. Domain Management

### `GET /api/domain/check`
Verifies if a custom subdomain is available.
- **Query Parameters**:
  - `domain`: Requested subdomain.
  - `username`: Current user's name.
- **Response (200 OK)**:
  ```json
  {
    "available": true,
    "domain": "requested-sub",
    "suggestion": null
  }
  ```
  Or if taken:
  ```json
  {
    "available": false,
    "domain": "requested-sub",
    "suggestion": "requested-sub-user123"
  }
  ```

## 4. Tunnel Status

### `GET /api/tunnels/me`
Fetches active tunnels for the authenticated user.
- **Headers**: `Authorization: Bearer <token>`
- **Response (200 OK)**:
  ```json
  {
    "tunnels": [
      {
        "domain": "user123.natnest.site",
        "port": 12345,
        "client_uuid": "...",
        "is_mine": true
      }
    ]
  }
  ```

## 5. SSH Tunnel (TCP Port 2222)

The client uses standard SSH Remote Port Forwarding.

- **Username Format**: `<username>#<subdomain>#<client_uuid>`
- **Authentication**: Public Key (using the key provided in `/api/auth/device`).
- **Success Signal**: The server must output `Allocated port <PORT>` to stderr when port 0 is requested.
- **Behavior**: Keepalive is maintained via `ServerAliveInterval`.
