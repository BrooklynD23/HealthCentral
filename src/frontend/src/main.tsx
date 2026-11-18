import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { MotionProvider } from './motion/MotionProvider';
import './styles/globals.css';

import '@fontsource-variable/fraunces';
import '@fontsource-variable/source-sans-3';
import '@fontsource/jetbrains-mono';

// Load the mono face now, not when the first font-mono value renders. A lazy load lays that text out in the
// fallback font for a frame, then swaps, so every value on /verify jumps about 1 px and grows 2 px (MEDS-G-FLAKE, G10).
void document.fonts?.load('1em "JetBrains Mono"');

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MotionProvider>
      <App />
    </MotionProvider>
  </React.StrictMode>,
);
