import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/globals.css';

import '@fontsource-variable/fraunces';
import '@fontsource-variable/source-sans-3';
import '@fontsource/jetbrains-mono';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
