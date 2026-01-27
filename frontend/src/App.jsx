import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import StockScreener from './components/StockScreener';
import StockProfile from './components/StockProfile';
import WatchList from './components/WatchList';
import Portfolio from './components/Portfolio';
import './App.css';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<StockScreener />} />
          <Route path="/profile" element={<StockProfile />} />
          <Route path="/profile/:symbol" element={<StockProfile />} />
          <Route path="/stock/:symbol" element={<StockProfile />} />
          <Route path="/watchlist" element={<WatchList />} />
          <Route path="/portfolio" element={<Portfolio />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;

