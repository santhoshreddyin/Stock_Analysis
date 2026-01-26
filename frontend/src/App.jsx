import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import StockScreener from './components/StockScreener';
import StockProfile from './components/StockProfile';
import './App.css';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<StockScreener />} />
          <Route path="/profile" element={<StockProfile />} />
          <Route path="/profile/:symbol" element={<StockProfile />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
