# Asteroid Analysis System

Multi-service system for asteroid analysis via NASA API, Rust calculation engine, and Streamlit dashboard.

## Project Structure

```
project-root/
├── services/
│   ├── python-api/         # Main Python API (Flask)
│   │   ├── app/
│   │   │   ├── routes/     # NASA, Analysis, Logs
│   │   │   ├── core/       # NASA client, Rust client, Config
│   │   │   ├── models/     # Asteroid, Orbit, Analysis Result
│   │   │   ├── utils/      # Logger, Validators
│   │   │   └── storage/    # Log files
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── rust-engine/        # Rust calculation engine
│   │   ├── src/
│   │   │   ├── api/        # Endpoints (analyze, health)
│   │   │   ├── domain/     # Asteroid, Orbit, Risk
│   │   │   ├── logic/      # Orbit math, Impact energy
│   │   │   ├── utils/      # Parsing
│   │   │   └── dto/        # Input/Output
│   │   ├── Cargo.toml
│   │   └── Dockerfile
│   │
│   └── dashboard/          # Streamlit Dashboard
│       ├── streamlit_app/
│       │   ├── Home.py     # Overview
│       │   ├── Asteroids.py # NASA data
│       │   ├── Analysis.py # Rust results
│       │   ├── Logs.py     # Log viewer
│       │   └── utils/
│       ├── requirements.txt
│       └── Dockerfile
│
├── infra/
│   ├── docker-compose.yml
│   ├── scripts/            # start_dev.sh, rebuild.sh
│   └── env/                # Environment variables per service
│
└── docs/
    ├── architecture.md
    ├── roadmap-levels.md
    ├── api-spec-python.md
    ├── api-spec-rust.md
    └── data-flows.md
```

## Setup

Check the documentation in `docs/` for more information on architecture and API specifications.

## Next Steps

1. Implement code in the new modules
2. Configure Docker Compose
3. Integrate NASA APIs
4. Develop orbital calculation logic in Rust
5. Create interactive dashboard
