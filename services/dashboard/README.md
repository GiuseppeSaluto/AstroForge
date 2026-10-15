# AstroForge Dashboard

Terminal-based UI for monitoring and controlling the AstroForge asteroid analysis system.

## Overview

The dashboard is built with **Textual** and provides:
- **System Health Monitoring** - Real-time backend, MongoDB, and Rust engine status
- **Pipeline Statistics** - Unprocessed asteroids, daily analysis count, high-risk asteroids
- **Asteroid Browser** - View all analyzed asteroids with risk levels and metrics
- **Pipeline Control** - Manually trigger analysis runs
- **Log Viewer** - Monitor system logs in real-time

## Features

### Home Screen (Default)
- System status (Backend, MongoDB, Rust Engine)
- Pipeline statistics (live counts)
- Quick action buttons
- Auto-refresh every 10 seconds

### Asteroids Screen
- Data table of analyzed asteroids
- Sortable by multiple columns (ID, Name, Risk Level, Score, Energy, Distance, Diameter, Velocity)
- Color-coded risk levels:
  - 🔴 Red: Critical or High risk
  - 🟡 Yellow: Medium risk
  - 🟢 Green: Low or unknown risk

### Pipeline Screen
- Current pipeline statistics
- "Run Now" button to trigger analysis
- Pipeline execution status
- Auto-refresh every 15 seconds

### Logs Screen
- Recent logs from Python API
- Color-coded by level (ERROR=red, WARNING=yellow, DEBUG=blue, INFO=green)
- Most recent logs shown first
- Refresh and clear options

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit the application |
| `h` | Home screen |
| `a` | Asteroids screen |
| `p` | Pipeline screen |
| `l` | Logs screen |

## Installation

1. Create virtual environment:
```bash
cd services/dashboard
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The dashboard only talks to the Python API, which reports Mongo and Rust Engine health on its behalf:

```bash
export API_BASE_URL=http://localhost:5001          # default
```

## Running

### 🚀 Automatic Launch (Recommended)

Use the main project launcher to start everything automatically:

```bash
# From project root
./infra/scripts/start_dev.sh
```

This will open the dashboard in a dedicated terminal window after starting all services.

### Manual Launch

#### Development
```bash
python3 -m app.main
```

#### From workspace task
```
Cmd/Ctrl + Shift + B → Select "Run Dashboard"
```

## Architecture

```
app/
├── main.py                 # App entry point with navigation
├── scheduler.py            # Background task scheduler (optional)
├── client/
│   └── api_client.py      # API client with retry logic
├── screens/               # Screen views
│   ├── home.py           # Dashboard home
│   ├── asteroids.py      # Asteroid table
│   ├── pipeline.py       # Pipeline control
│   └── logs.py           # Log viewer
└── widgets/              # Reusable widgets
    ├── stats_panel.py    # Stats display widget
    ├── asteroid_table.py # DataTable wrapper
    └── log_viewer.py     # RichLog wrapper
```

## API Integration

The dashboard communicates with the Python API at:
- `http://localhost:5001` (default)

Required endpoints:
- `GET /pipeline/status` - System health check
- `GET /pipeline/stats` - Pipeline statistics
- `POST /pipeline/neo/analyze` - Trigger analysis
- `GET /pipeline/analysis/asteroids` - List analyzed asteroids
- `GET /logs` - Fetch recent logs

## Improvements Made

### API Client (`api_client.py`)
- ✅ Fixed API base URL (was 5000, now 5001)
- ✅ Retry logic with exponential backoff
- ✅ Session pooling for efficiency
- ✅ Proper timeout handling
- ✅ Error handling and logging
- ✅ Support for `/pipeline/stats` endpoint

### Navigation (`main.py`)
- ✅ Proper screen navigation with keyboard bindings
- ✅ Global CSS for consistent styling
- ✅ Dedicated action methods for each screen

### Home Screen (`home.py`)
- ✅ Real-time system status display
- ✅ Live pipeline statistics
- ✅ Pipeline execution from UI
- ✅ Auto-refresh every 10 seconds
- ✅ Color-coded status indicators

### Pipeline Screen (`pipeline.py`)
- ✅ Complete pipeline control
- ✅ Real-time execution feedback
- ✅ Statistical display
- ✅ Error handling

### Asteroids Screen (`asteroids.py`)
- ✅ Sortable data table
- ✅ Color-coded risk levels
- ✅ Formatted metrics display
- ✅ Data loading with error handling

### Logs Screen (`logs.py`)
- ✅ Real-time log display
- ✅ Color-coded log levels
- ✅ Timestamp display
- ✅ Refresh and clear options

### Widgets
- ✅ `stats_panel.py` - Reusable stats panel
- ✅ `asteroid_table.py` - Custom DataTable with utilities
- ✅ `log_viewer.py` - Custom RichLog with formatting

## Troubleshooting

### "Backend unreachable"
- Check Python API is running on port 5001
- Verify `API_BASE_URL` environment variable

### "MongoDB disconnected"
- Check MongoDB is running (`mongod`)
- Verify connection string in Python API config

### "Rust Engine unreachable"
- Check Rust engine is running on port 8080
- Verify `RUST_ENGINE_URL` in the Python API config (`infra/env/python.env`)

### No data showing
- Ensure pipeline has been run at least once
- Check logs screen for errors
- Verify Rust engine connectivity

## Future Enhancements

- [ ] Live log streaming (WebSocket)
- [ ] Advanced filtering for asteroids
- [ ] Risk trend graphs
- [ ] NASA NEO feed browser
- [ ] Export to CSV/JSON
- [ ] Custom refresh intervals
