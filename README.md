# AstroForge

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
│   │   │   ├── storage/    # Log files
│   │   │   └── main.py     # Flask app
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── rust-engine/        # Rust calculation engine
│   │   ├── src/
│   │   │   ├── domain/     # Asteroid, Orbit, Risk
│   │   │   ├── logic/      # Orbit math, Impact energy
│   │   │   └── main.rs     # Server setup
│   │   ├── Cargo.toml
│   │   └── Dockerfile
│   │
│   └── dashboard/          # Streamlit Dashboard
│       ├── streamlit_app/
│       │   ├── Main.py     # Main dashboard page
│       │   └── utils/      # Helper functions
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
