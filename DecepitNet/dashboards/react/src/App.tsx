import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import Dashboard from './pages/Dashboard';
import AttackHeatmap from './pages/AttackHeatmap';
import ThreatIntel from './pages/ThreatIntel';
import MLInsights from './pages/MLInsights';
import Sidebar from './components/Sidebar';
import './App.css';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00ff41',
    },
    secondary: {
      main: '#ff4444',
    },
    background: {
      default: '#0a0e27',
      paper: '#141b2d',
    },
  },
  typography: {
    fontFamily: '"Roboto Mono", monospace',
  },
});

function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Router>
        <div className="app">
          <Sidebar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/heatmap" element={<AttackHeatmap />} />
              <Route path="/threat-intel" element={<ThreatIntel />} />
              <Route path="/ml-insights" element={<MLInsights />} />
            </Routes>
          </main>
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;
