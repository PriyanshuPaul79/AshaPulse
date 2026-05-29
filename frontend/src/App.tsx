/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { HashRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './lib/theme';
import AppShell from './components/layout/AppShell';
import HomePage from './pages/HomePage';
import ResultPage from './pages/ResultPage';
import PhcPage from './pages/PhcPage';
import HistoryPage from './pages/HistoryPage';

export default function App() {
  return (
    <ThemeProvider>
      <HashRouter>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<HomePage />} />
            <Route path="result" element={<ResultPage />} />
            <Route path="phc" element={<PhcPage />} />
            <Route path="history" element={<HistoryPage />} />
          </Route>
        </Routes>
      </HashRouter>
    </ThemeProvider>
  );
}

