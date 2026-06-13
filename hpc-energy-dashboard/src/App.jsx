import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { SimulationProvider } from './context/SimulationContext';
import TopNav from './components/layout/TopNav';
import Sidebar from './components/layout/Sidebar';
import Footer from './components/layout/Footer';
import Configuration from './pages/Configuration';
import EnergyOverview from './pages/EnergyOverview';
import GridAnalysis from './pages/GridAnalysis';
import CostAnalysis from './pages/CostAnalysis';

export default function App() {
  return (
    <SimulationProvider>
      <BrowserRouter>
        <div className="app-layout">
          <TopNav />
          <div className="app-body">
            <Sidebar />
            <div className="main-content">
              <Routes>
                <Route path="/" element={<Navigate to="/energy-overview" replace />} />
                <Route path="/configuration" element={<Configuration />} />
                <Route path="/energy-overview" element={<EnergyOverview />} />
                <Route path="/grid-analysis" element={<GridAnalysis />} />
                <Route path="/cost-analysis" element={<CostAnalysis />} />
              </Routes>
              <Footer />
            </div>
          </div>
        </div>
      </BrowserRouter>
    </SimulationProvider>
  );
}

