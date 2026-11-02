import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

// Node ignores a TZ write inside a worker thread, so the zone is set here, before the pool starts (VITEST-TZ-PIN).
process.env.TZ = process.env.VITEST_TZ ?? 'America/New_York';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const isWslWindowsMount = process.cwd().startsWith('/mnt/');

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: [
      './src/__tests__/setupLocalStorage.ts',
      './src/__tests__/setup.ts',
    ],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    pool: isWslWindowsMount ? 'threads' : 'forks',
    testTimeout: 10000,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@components': resolve(__dirname, './src/components'),
      '@pages': resolve(__dirname, './src/pages'),
      '@hooks': resolve(__dirname, './src/hooks'),
      '@utils': resolve(__dirname, './src/utils'),
      '@stores': resolve(__dirname, './src/stores'),
      '@types': resolve(__dirname, './src/types'),
      '@services': resolve(__dirname, './src/services'),
    },
  },
});
