import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { BrainCircuit, Briefcase, Users, Send, Activity, Home, Clock } from 'lucide-react';
import JobList from './pages/JobList';
import JobDetail from './pages/JobDetail';
import AdminDashboard from './pages/AdminDashboard';
import CandidatesPage from './pages/CandidatesPage';
import SubmissionsPage from './pages/SubmissionsPage';
import HomePage from './pages/HomePage';
import SchedulerPage from './pages/SchedulerPage';

function NavLink({ to, icon: Icon, children }) {
  const location = useLocation();
  const isActive = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
  return (
    <Link to={to} className={`nav-link${isActive ? ' active' : ''}`}>
      <Icon size={15} />
      {children}
    </Link>
  );
}

function Navbar() {
  return (
    <div className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-brand">
          <BrainCircuit size={22} color="var(--accent)" />
          Westley<span style={{ color: 'var(--primary)' }}>AI</span>
          <span className="brand-dot" />
        </Link>
        <nav className="nav-links">
          <NavLink to="/" icon={Home}>Home</NavLink>
          <NavLink to="/jobs" icon={Briefcase}>Jobs</NavLink>
          <NavLink to="/candidates" icon={Users}>Candidates</NavLink>
          <NavLink to="/submissions" icon={Send}>Submissions</NavLink>
          <NavLink to="/admin" icon={Activity}>Admin</NavLink>
          <NavLink to="/scheduler" icon={Clock}>Scheduler</NavLink>
        </nav>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router basename="/app">
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/jobs" element={<JobList />} />
          <Route path="/jobs/:id" element={<JobDetail />} />
          <Route path="/candidates" element={<CandidatesPage />} />
          <Route path="/submissions" element={<SubmissionsPage />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/scheduler" element={<SchedulerPage />} />
        </Routes>
      </main>
    </Router>
  );
}

export default App;
