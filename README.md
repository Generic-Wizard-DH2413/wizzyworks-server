# wizzyworks-server

A WebSocket server with HTTP file serving capabilities for the WizzyWorks platform.

## Features

- WebSocket server on port 8765
- HTTP file server on port 8000
- CORS support for web clients
- Bridge connection support for external services
- Client ID management with reusable IDs

## Docker Deployment

### Quick Start

1. **Using Docker Compose (Recommended)**:
```bash
docker-compose up -d
```

2. **Using Docker directly**:
```bash
# Build the image
docker build -t wizzyworks-server .

# Run the container
docker run -d -p 8765:8765 -p 8000:8000 --name wizzyworks-server wizzyworks-server
```

### Docker Commands

- **View logs**: `docker logs wizzyworks-server`
- **Stop container**: `docker stop wizzyworks-server`
- **Remove container**: `docker rm wizzyworks-server`
- **Restart**: `docker restart wizzyworks-server`

### Port Configuration

- **8765**: WebSocket server port
- **8000**: HTTP file server port

Both ports are exposed and can be accessed via:
- WebSocket: `ws://localhost:8765`
- HTTP: `http://localhost:8000`

## Local Development

If you want to run without Docker:

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
cd server
python server.py
```

## Configuration

The server accepts connections from the following origins by default:
- `https://wizzyworks-frontend.vercel.app`
- `http://localhost:3000-3001`
- `http://127.0.0.1:3000-3001`
- `http://localhost:8000`
- `http://127.0.0.1:8000`

Additional origins can be configured in the `ALLOWED_ORIGINS` list in `server.py`.