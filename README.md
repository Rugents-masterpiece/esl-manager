# esl-manager

ESL (Electronic Shelf Label) management system with web application, firmware handling, and Oberon ServiceGateway integration. Designed for managing ESL deployments in retail environments.

## Components

```
esl-manager/
├── esl/              # Core ESL protocol handling
├── esl-manager/      # Management application
├── esl-oberon/       # Oberon ServiceGateway integration
├── webapp/           # Web-based management UI
├── tests/            # Test suite
└── ANALYSIS.md       # Architecture analysis
```

## Features

- **ESL Communication**: Protocol handling for electronic shelf labels
- **Firmware Management**: OTA updates, versioning, rollback
- **Oberon Integration**: ServiceGateway client for enterprise connectivity
- **Web Dashboard**: Real-time monitoring, configuration, diagnostics
- **Multi-tenant**: Supports multiple deployments/sites

## Prerequisites

- Python 3.10+
- .NET 8+ (for Oberon integration)
- Docker (for containerized deployment)
- PostgreSQL / MariaDB (persistence)

## Installation

```bash
git clone https://github.com/Rugents-masterpiece/esl-manager.git
cd esl-manager

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run webapp (development)
cd webapp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py

# Or with Docker
docker compose up -d --build
```

## Configuration

Key environment variables (see `.env.example`):

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL/MariaDB connection string |
| `OBERON_GATEWAY_URL` | Oberon ServiceGateway endpoint |
| `OBERON_API_KEY` | API key for Oberon |
| `ESL_FIRMWARE_PATH` | Path to firmware binaries |
| `WEBAPP_PORT` | Web UI port (default: 8080) |

## Project Structure

| Directory | Purpose |
|-----------|---------|
| `esl/` | Low-level ESL protocol (Bluetooth/Zigbee/WiFi) |
| `esl-manager/` | Business logic: label assignment, layouts, scheduling |
| `esl-oberon/` | ServiceGateway client, sync, billing integration |
| `webapp/` | Flask/FastAPI + React/Vue frontend |
| `tests/` | Unit + integration tests |

## Development

```bash
# Run tests
cd tests
python3 -m pytest

# Lint
ruff check .
black --check .
```

## Deployment

```bash
# Build images
docker compose build

# Deploy stack
docker compose up -d

# Check status
docker compose ps
docker compose logs -f webapp
```

## Security

- No credentials in repository
- `.env` is gitignored (copy from `.env.example`)
- API keys loaded from environment at runtime
- Oberon integration uses service accounts, not user credentials

## License

MIT
