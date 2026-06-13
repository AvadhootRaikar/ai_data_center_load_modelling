import { useLocation, useNavigate } from 'react-router-dom';
import { Zap, Settings, Activity, DollarSign } from 'lucide-react';

const navLinks = [
  { path: '/configuration', label: 'Configuration', icon: Settings },
  { path: '/energy-overview', label: 'Energy Overview', icon: Zap },
  { path: '/grid-analysis', label: 'Grid Analysis', icon: Activity },
  { path: '/cost-analysis', label: 'Cost Analysis', icon: DollarSign },
];

export default function TopNav() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <nav className="topnav">
      <div className="topnav-logo" onClick={() => navigate('/energy-overview')} style={{ cursor: 'pointer' }}>
        <div className="topnav-logo-icon">
          <Zap size={16} />
        </div>
        <span className="topnav-logo-text">HPC Energy Simulation</span>
      </div>

      <div className="topnav-links">
        {navLinks.map(link => (
          <button
            key={link.path}
            className={`topnav-link ${location.pathname === link.path ? 'active' : ''}`}
            onClick={() => navigate(link.path)}
          >
            <link.icon size={13} />
            {link.label}
          </button>
        ))}
      </div>

      <div className="topnav-user">
        <div className="topnav-user-info">
          <div className="topnav-user-name">HPC Cluster #04</div>
          <div className="topnav-user-status">SIMULATION MODE</div>
        </div>
        <div className="topnav-avatar">
          KR
          <span className="topnav-avatar-dot"></span>
        </div>
      </div>
    </nav>
  );
}
