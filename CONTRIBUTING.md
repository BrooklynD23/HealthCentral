# Contributing to Asclexis

Thank you for your interest in contributing to Asclexis! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We are committed to providing a welcoming and inclusive environment.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 22+ (Node.js 24 LTS recommended)
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

### Running the Maintained Repo-Root Proof Bundle

Follow the WSL/Linux bootstrap in `README.md` first so `./.wsl-pytest-venv` and the frontend dependencies exist, then run the maintained proof bundle from the repository root:

```bash
python3 scripts/repo_hygiene_check.py
python3 scripts/docs_lint.py
npm --prefix src/frontend run test:run -- src/__tests__/ExplainAssistant.test.tsx
npx --prefix src/frontend playwright test --config src/frontend/playwright.config.ts src/frontend/e2e/assistant.spec.ts --grep "category"
PYTHONPATH=src/backend ./.wsl-pytest-venv/bin/python -m pytest src/backend/tests/test_bootstrap_check.py src/backend/tests/security/test_password_hashing.py src/backend/tests/test_repo_hygiene_check.py -q
```

This is the current contributor verification path for the assistant-category surface and repo-hygiene guardrails. Run broader suites as needed after this bundle passes.

### Additional Focused Checks

```bash
# Opt-in Playwright suite (requires lab PDF on disk; see README "Full UI verification")
cd src/frontend && npx playwright test --config playwright.config.ts --project real-pdf-local

# Backend tests
PYTHONPATH=src/backend ./.wsl-pytest-venv/bin/python -m pytest src/backend/tests/ -v

# Frontend tests
npm --prefix src/frontend test

# Frontend lint
npm --prefix src/frontend run lint
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

### Agent Code-Knowledge Layer (Serena)

For AI-assisted development, this repo ships a **dev-only, always-fresh** code-knowledge layer
([Serena](https://github.com/oraios/serena), an LSP-over-MCP server) that gives coding agents
precise symbol/reference navigation over the codebase. It auto-launches in Claude Code via the
repo-root `.mcp.json` and reaches **source code + docs only** (never patient data). See
[docs/dev/agent-code-knowledge.md](docs/dev/agent-code-knowledge.md) for setup, tools, the
privacy guarantee, and the safety-critical module list.

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
4. Run the maintained repo-root proof bundle from the repository root:
   - `python3 scripts/repo_hygiene_check.py`
   - `python3 scripts/docs_lint.py`
   - `npm --prefix src/frontend run test:run -- src/__tests__/ExplainAssistant.test.tsx`
   - `npx --prefix src/frontend playwright test --config src/frontend/playwright.config.ts src/frontend/e2e/assistant.spec.ts --grep "category"`
   - `PYTHONPATH=src/backend ./.wsl-pytest-venv/bin/python -m pytest src/backend/tests/test_bootstrap_check.py src/backend/tests/security/test_password_hashing.py src/backend/tests/test_repo_hygiene_check.py -q`
   For docs-only changes you can start with the first two commands, but do not update contributor-facing proof instructions unless the full bundle still matches reality.

### PR Checklist

- [ ] Maintained repo-root proof bundle passes (`python3 scripts/repo_hygiene_check.py`, `python3 scripts/docs_lint.py`, `npm --prefix src/frontend run test:run -- src/__tests__/ExplainAssistant.test.tsx`, `npx --prefix src/frontend playwright test --config src/frontend/playwright.config.ts src/frontend/e2e/assistant.spec.ts --grep "category"`, and `PYTHONPATH=src/backend ./.wsl-pytest-venv/bin/python -m pytest src/backend/tests/test_bootstrap_check.py src/backend/tests/security/test_password_hashing.py src/backend/tests/test_repo_hygiene_check.py -q`)
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

Asclexis handles sensitive health data. Please:

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
