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


## 🤝 Contributing

Contributions are welcome! Whether it's bug fixes, new features, documentation improvements, or testing — every contribution helps.

### Ways to Contribute

| Type | Description |
|------|-------------|
| 🐛 **Bug Reports** | Found an issue? Open a GitHub Issue with steps to reproduce, expected vs actual behavior, and environment details |
| ✨ **Feature Requests** | Have an idea? Open a GitHub Issue with the "enhancement" label describing the use case |
| 📝 **Documentation** | Fix typos, clarify setup steps, add examples — PRs to `README.md` or `/docs` are always appreciated |
| 🔧 **Code** | Bug fixes, new features, refactoring, tests |
| 🧪 **Testing** | Test on different hardware/OS, report compatibility |
| 💡 **Ideas & Feedback** | Discussions, RFCs, architecture suggestions |

### Quick Start for Contributors

```bash
# 1. Fork the repository
# 2. Clone your fork
git clone https://github.com/YOUR-USERNAME/REPO-NAME.git
cd REPO-NAME

# 3. Create a feature branch
git checkout -b feature/your-feature-name

# 4. Make changes, test locally
# (see README for local development setup)

# 5. Commit with conventional commits
git commit -m "feat: add amazing feature"

# 6. Push and open a Pull Request
git push origin feature/your-feature-name
```

### Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat:     new feature
fix:      bug fix
docs:     documentation only
style:    formatting, no code change
refactor: code restructuring
test:     adding tests
chore:    maintenance, deps, build
```

Examples:
- `feat: add voice selection UI for TTS`
- `fix: handle GPU OOM in model offloading`
- `docs: clarify Docker setup for ARM64`

### Pull Request Guidelines

- ✅ **One feature/fix per PR** — keeps reviews focused
- ✅ **Tests pass** — run local tests before pushing
- ✅ **Update docs** — if behavior changes, update README/comments
- ✅ **No credentials** — never commit `.env`, keys, tokens
- ✅ **Small, focused commits** — easier to review

### Development Setup

See the **Installation** section above for local setup. Most projects use:

```bash
# Python projects
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# or pip install -e ".[dev]" for dev dependencies

# .NET projects
dotnet restore
dotnet build

# Docker projects
docker compose up -d --build
```

### Code Style

| Language | Formatter | Linter |
|----------|-----------|--------|
| Python | `black` | `ruff` |
| C# | `dotnet format` | Built-in |
| JavaScript/TypeScript | `prettier` | `eslint` |
| Blazor | `dotnet format` | Built-in |

Run formatters before committing:
```bash
# Python
black . && ruff check .

# .NET
dotnet format

# JS/TS (if applicable)
prettier --write .
```

### Reporting Security Issues

**Do not open public issues for security vulnerabilities.** Email directly or use GitHub's private vulnerability reporting.

### Community

- 💬 **Discussions**: Use GitHub Discussions for questions, ideas, RFCs
- 🐛 **Issues**: Bug reports, feature requests
- 📧 **Contact**: Open an issue for maintainer contact

### Recognition

Contributors are recognized in:
- GitHub Contributors graph
- Release notes (for significant contributions)
- `AUTHORS.md` or `CONTRIBUTORS.md` (if maintained)

---

**Thank you for contributing!** 🎉

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

MIT License allows:
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use
- ❌ No liability
- ❌ No warranty

---

## ⭐ Star History

If you find this project useful, please consider giving it a star! It helps with visibility and motivation.

## License

MIT
