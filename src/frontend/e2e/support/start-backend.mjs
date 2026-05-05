import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const frontendDir = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const repoRoot = resolve(frontendDir, '..', '..');
const backendDir = resolve(repoRoot, 'src', 'backend');

const candidates = [
  process.env.HC_E2E_BACKEND_PYTHON,
  join(backendDir, '.venv', 'bin', 'python'),
  join(repoRoot, '.wsl-pytest-venv', 'bin', 'python'),
  join(backendDir, 'venv', 'Scripts', 'python.exe'),
  'python3',
  'python',
].filter(Boolean);

function canImportBackendDeps(python) {
  const result = spawnSync(
    python,
    ['-c', 'import fastapi, uvicorn, sqlalchemy, aiosqlite'],
    { cwd: backendDir, encoding: 'utf8' }
  );
  return result.status === 0;
}

function resolvePython() {
  for (const candidate of candidates) {
    if (candidate.includes('/') || candidate.includes('\\')) {
      if (!existsSync(candidate)) continue;
    }
    if (canImportBackendDeps(candidate)) {
      return candidate;
    }
  }

  console.error(
    [
      'Unable to start the E2E backend: no candidate Python can import FastAPI/Uvicorn.',
      'Set HC_E2E_BACKEND_PYTHON to a Python executable with backend requirements installed.',
      'WSL example:',
      '  python3 -m venv src/backend/.venv',
      '  src/backend/.venv/bin/python -m pip install -r src/backend/requirements.txt',
      'Windows fallback:',
      '  py -m venv src/backend/venv',
      '  src/backend/venv/Scripts/python.exe -m pip install -r src/backend/requirements.txt',
    ].join('\n')
  );
  process.exit(1);
}

const python = resolvePython();
const child = spawn(
  python,
  ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'],
  {
    cwd: backendDir,
    stdio: 'inherit',
    env: {
      ...process.env,
      APP_ENV: process.env.APP_ENV || 'development',
    },
  }
);

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    child.kill(signal);
  });
}

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});
