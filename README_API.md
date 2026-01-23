# Stock Analysis Data Presentation Layer

This project adds a FastAPI backend and ReactJS frontend to the existing Stock Analysis batch processing system. It provides a user-friendly interface to view and analyze stock data stored in PostgreSQL.

## Architecture

### Backend (FastAPI)
- **Location**: `api/` directory
- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Port**: 8000 (default)

### Frontend (ReactJS)
- **Location**: `frontend/` directory
- **Framework**: React with Vite
- **UI Library**: Custom CSS with modern styling
- **Port**: 5173 (default Vite dev server)

## Prerequisites

- Python 3.8+
- Node.js 16+ and npm
- PostgreSQL database (configured with environment variables)
- Environment variables set for database connection:
  - `DB_HOST` (default: localhost)
  - `DB_PORT` (default: 5432)
  - `DB_NAME` (default: postgres)
  - `DB_USER` (default: postgres)
  - `DB_PASSWORD` (default: postgres)

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

## Running the Application

### Start the Backend (FastAPI)

```bash
# From the root directory
python -m api.main

# Or with uvicorn directly
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: http://localhost:8000

API Documentation (Swagger UI): http://localhost:8000/docs

### Start the Frontend (React)

```bash
cd frontend
npm run dev
```

The frontend will be available at: http://localhost:5173

## API Endpoints

### Core Endpoints

- `GET /` - API information
- `GET /api/health` - Health check
- `GET /api/stocks` - Get list of stocks with filters
  - Query params: `limit`, `sector`, `frequency`
- `GET /api/stocks/{symbol}` - Get detailed stock information
- `GET /api/key-parameters` - Get dashboard key parameters and statistics
- `GET /api/stocks/{symbol}/history` - Get historical price data
  - Query params: `limit` (default: 30)
- `GET /api/sectors` - Get list of all sectors

## Features

### Dashboard View
- Total stocks count
- Stocks with price data
- Recommendation summary (Buy/Hold/Sell)
- Total sectors
- Top 5 stocks by price

### Stock List View
- Paginated stock list
- Filters by sector, frequency, and limit
- Search and browse all stocks
- Click to view detailed information

### Stock Detail View
- Complete stock information
- Current price and recommendations
- 52-week high/low
- Target prices
- Average volume
- Historical price data (last 30 days)
- Company description

## Database Schema

The application reads from the following PostgreSQL tables:

- **Stock_List**: Basic stock information (symbol, name, sector, industry)
- **StockPrice**: Current price data and recommendations
- **Stock_History**: Historical price records

## Development

### Backend Development

The FastAPI backend uses:
- Pydantic for request/response validation
- SQLAlchemy for database ORM
- CORS middleware for frontend integration

### Frontend Development

The React frontend uses:
- Vite for fast development and building
- Axios for API communication
- Modern CSS with gradient designs
- Responsive design for mobile devices

## Environment Configuration

Create a `.env` file in the root directory (optional):

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres

# API Configuration (for frontend)
VITE_API_URL=http://localhost:8000
```

## Project Structure

```
Stock_Analysis/
├── api/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   └── models.py        # Pydantic models
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Dashboard.css
│   │   │   ├── StockList.jsx
│   │   │   ├── StockList.css
│   │   │   ├── StockDetail.jsx
│   │   │   └── StockDetail.css
│   │   ├── services/
│   │   │   └── api.js   # API service layer
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── Data_Loader.py       # Database connection & models
├── requirements.txt
└── README_API.md        # This file
```

## Testing

### Test the Backend

```bash
# Check API health
curl http://localhost:8000/api/health

# Get stocks
curl http://localhost:8000/api/stocks?limit=10

# Get key parameters
curl http://localhost:8000/api/key-parameters
```

### Test the Frontend

1. Start both backend and frontend servers
2. Navigate to http://localhost:5173
3. Verify dashboard loads with data
4. Test navigation between views
5. Test stock detail page

## Troubleshooting

### Backend Issues

- **Database connection failed**: Check environment variables and PostgreSQL service
- **Import errors**: Ensure all dependencies are installed with `pip install -r requirements.txt`

### Frontend Issues

- **API connection failed**: Verify backend is running on port 8000
- **CORS errors**: Check CORS middleware configuration in `api/main.py`
- **Module not found**: Run `npm install` in the frontend directory

## Production Deployment

### Backend

```bash
# Use production-grade ASGI server
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend

```bash
cd frontend
npm run build
# Serve the dist/ directory with nginx or any static file server
```

## License

Part of the Stock Analysis project.
