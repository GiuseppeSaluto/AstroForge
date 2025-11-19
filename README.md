# PyRust Engine 🚀

> **⚠️ PROOF OF CONCEPT** - Educational project for learning hybrid microservices architecture with Python, Rust, and MongoDB.

## What is this?

A demonstration project combining:
- **Python (Flask)** - API Gateway with input validation
- **Rust (Actix)** - High-performance pricing calculations
- **MongoDB** - NoSQL data storage
- **Docker** - Containerized microservices

## Quick Start

```
┌─────────────────┐
│   Client        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Core API (Py)  │────▶│ Pricing Engine   │
│  Port: 5000     │     │ (Rust)           │
│  - Flask        │     │ Port: 8080       │
│  - Validation   │     │ - Actix-web      │
│  - CORS         │     │ - Fast compute   │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│   MongoDB       │
│   Port: 27017   │
└─────────────────┘
```

### Services:
- **core_api_py**: Flask API Gateway. Handles user requests, validation, and DB operations
- **pricing_engine_rs**: Rust microservice. Performs heavy computational tasks
- **mongo**: MongoDB for NoSQL data persistence

## 📦 Prerequisites

- Docker (20.10+)
- Docker Compose (1.29+)
- Git

## Quick Start

### 1. Clone the repository

```bash
# 1. Clone and setup
git clone <your-repo-url>
cd PyRust_Engine
cp .env.example .env

# 2. Start services
docker-compose up --build

# 3. Test it
curl http://localhost:5000/
curl -X POST http://localhost:5000/calculate_price \
  -H "Content-Type: application/json" \
  -d '{"base_price": 100, "factor": 1.2}'
```

## Architecture

```
Client → Python API (5000) → Rust Engine (8080)
              ↓
          MongoDB (27017)
```

**Services:**
- `core_api_py`: Flask API with validation & MongoDB
- `pricing_engine_rs`: Rust microservice for calculations
- `mongo`: MongoDB database

## API Endpoints

### `GET /` - Service info
### `GET /health` - Health check
### `POST /calculate_price` - Price calculation

```json
// Request
{
  "base_price": 100,
  "factor": 1.2
}

// Response
{
  "success": true,
  "rust_computation": {
    "final_price": 120.0
  }
}
```

## Project Structure

```
PyRust_Engine/
├── core_api_py/          # Python Flask API
│   ├── app/              # Routes, models, config
│   └── requirements.txt
├── pricing_engine_rs/    # Rust microservice
│   ├── src/              # main.rs, pricing_logic.rs
│   └── Cargo.toml
├── docker-compose.yml
├── .env.example          # Template for environment variables
└── README.md
```

## Development

**Without Docker:**
```bash
# Python
cd core_api_py
pip install -r requirements.txt
flask run

# Rust
cd pricing_engine_rs
cargo run
```

**View logs:**
```bash
docker-compose logs -f
```

## What's Implemented ✅

- Basic microservices architecture
- Input validation
- Error handling
- CORS & security headers
- Docker containerization

## What's Missing ❌

- Authentication
- Rate limiting
- Comprehensive tests
- Production hardening
- Monitoring & logging

Made with ❤️ using Python 🐍 and Rust 🦀

> **Note**: This is a POC project for learning purposes. Not production-ready.
