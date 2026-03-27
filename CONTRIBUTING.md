# Contributing to HealthCentral

Thank you for your interest in contributing to HealthCentral! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We are committed to providing a welcoming and inclusive environment.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/HealthCentral.git
   cd HealthCentral
   ```

2. **Use the dev script (recommended)**
   ```powershell
   .\dev.ps1
   ```
   This automatically sets up virtual environments and installs dependencies.

3. **Or manual setup**
   ```bash
   # Backend
   cd src/backend
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or: venv\Scripts\activate  # Windows
   pip install -r requirements.txt

   # Frontend
   cd ../frontend
   npm install
   ```

### SQLCipher Setup

For database encryption support, see the SQLCipher Setup section in README.md.

For development without SQLCipher, set in your `.env`:
```
DATABASE_ENCRYPTION_REQUIRED=false
```

## Development Workflow

### Running the Application

```bash
# Backend (from src/backend)
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Frontend (from src/frontend)
npm run dev
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Running Tests

```bash
# Backend tests
cd src/backend
python -m pytest tests/ -v

# Frontend tests
cd src/frontend
npm test

# Frontend lint
npm run lint
```

### Code Style

**Backend (Python)**
- Use `ruff` for linting and formatting
- Follow PEP 8 guidelines
- Use type hints for all function parameters and returns
- Configuration in `pyproject.toml`

**Frontend (TypeScript/React)**
- Use ESLint with the project's flat config (`eslint.config.js`)
- Follow React Hooks rules
- Use TypeScript strict mode

### Running Linters

```bash
# Backend
cd src/backend
ruff check .
ruff format .

# Frontend
cd src/frontend
npm run lint
```

## Making Changes

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions or fixes

Example: `feature/add-export-pdf`

### Commit Messages

Write clear, concise commit messages:
- Use imperative mood ("Add feature" not "Added feature")
- First line: brief summary (50 chars or less)
- Body: explain what and why (wrap at 72 chars)

Example:
```
Add PDF export functionality

Implement PDF generation for doctor summaries using ReportLab.
Includes page numbering and proper formatting for printing.
```

### Pull Request Process

1. **Create a branch** from `main`
2. **Make your changes** with tests
3. **Ensure all tests pass** locally
4. **Run linters** and fix any issues
5. **Create a pull request** with:
   - Clear title describing the change
   - Description of what changed and why
   - Reference to any related issues

### Repo hygiene for status-sensitive work

Treat local helper state separately from shared project changes so dirty-worktree checks stay meaningful:

- **Ignore category:** `.bg-shell/` and `.wsl-pytest-venv/` are local-only directories used for shell state and WSL verification bootstrap. They belong in `.gitignore`, not in commits.
- **Clean-up category:** ad-hoc root files such as `PLAN.md`, `HANDOFF-*.md`, and generated local reports like `*_report*.md` should be removed or relocated before review. They are intentionally not broadly ignored because they can look like real project docs.
- **Document category:** when contributor guidance changes, update `README.md`, `CONTRIBUTING.md`, and `.gsd/KNOWLEDGE.md` together so future audits interpret local-only artifacts consistently.

#### Lightweight pre-merge checklist

1. Run `git status --short` from the repository root.
2. Confirm that only intentional tracked edits remain.
3. Delete, rename, or move any local-only scratch files before asking someone else to interpret the worktree.
4. Re-run the repo checks relevant to your changes; for documentation-only hygiene changes, start with `python3 scripts/docs_lint.py`.

### PR Checklist

- [ ] Tests pass locally (`pytest` and `npm test`)
- [ ] Lint passes (`ruff` and `npm run lint`)
- [ ] New code has appropriate test coverage
- [ ] Documentation updated if needed
- [ ] No sensitive data (API keys, passwords) committed
- [ ] Pre-merge hygiene pass completed (no unexpected local-only artifacts in `git status`)

## Project Structure

```
HealthCentral/
├── src/
│   ├── backend/           # Python FastAPI backend
│   │   ├── api/           # API routes
│   │   ├── core/          # Config, security, database
│   │   ├── models/        # SQLAlchemy models
│   │   ├── modules/       # Business logic
│   │   └── tests/         # Backend tests
│   └── frontend/          # React + Vite + TypeScript
│       ├── src/
│       │   ├── components/
│       │   ├── pages/
│       │   ├── services/
│       │   └── stores/
│       └── e2e/           # E2E tests
├── docs/                  # Documentation
└── config/                # Configuration templates
```

## Security Considerations

HealthCentral handles sensitive health data. Please:

- Never log sensitive data (passwords, health information)
- Use parameterized queries (SQLAlchemy ORM)
- Validate all user inputs
- Follow the principle of least privilege
- Report security vulnerabilities via SECURITY.md

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- For security issues, see SECURITY.md

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
