# Suggested Commands for HealthCentral Development

## Quick Start
```bash
# From project root - starts both backend and frontend
.\dev.bat          # Windows CMD
.\dev.ps1          # PowerShell
```

## Backend Commands
```bash
# Navigate to backend
cd src/backend

# Create virtual environment
python -m venv venv

# Activate venv (Windows)
venv\Scripts\activate

# Activate venv (Linux/WSL)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# API Documentation available at:
# http://localhost:8000/docs
# http://localhost:8000/redoc
```

## Frontend Commands
```bash
# Navigate to frontend
cd src/frontend

# Install dependencies
npm install

# Start development server
npm run dev
# Frontend runs at: http://localhost:3000
```

## Testing Commands
```bash
# Backend tests
cd src/backend
pytest                        # Run all tests
pytest --cov=.               # With coverage
pytest -v                     # Verbose output

# Frontend tests (when added)
cd src/frontend
npm test
```

## Code Quality Commands
```bash
# Backend
cd src/backend
black .                       # Format Python code
ruff .                        # Lint Python code
mypy .                        # Type checking

# Frontend
cd src/frontend
npm run lint                  # ESLint (if configured)
npm run format                # Prettier (if configured)
```

## Git Commands
```bash
git status
git add .
git commit -m "message"
git push origin Security-Revamp
```

## System Info
- **OS**: Linux (WSL2 on Windows)
- **Python**: 3.10+
- **Node.js**: 18+
- **Main Branch**: main
- **Working Branch**: Security-Revamp
