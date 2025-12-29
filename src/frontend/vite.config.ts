import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig({
  plugins: [react()],
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
  server: {
    port: 3000,
    strictPort: false,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
