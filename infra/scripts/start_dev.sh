#!/bin/bash
# AstroForge Development Launcher
# Starts all services and opens dashboard in a dedicated window

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

set -euo pipefail

# Project directories
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVICES_DIR="$PROJECT_DIR/services"

echo -e "${BLUE}🚀 AstroForge Development Launcher${NC}"
echo -e "${BLUE}=================================${NC}"

# Function to check if a port is in use
check_port() {
    local port=$1
    # Try to connect to the port
    (echo >/dev/tcp/localhost/$port) 2>/dev/null && return 0 || return 1
}

# Function to wait for a service to be ready
wait_for_service() {
    local name=$1
    local port=$2
    local max_attempts=30
    local attempt=1

    echo -e "${YELLOW}⏳ Waiting for $name on port $port...${NC}"

    while [ $attempt -le $max_attempts ]; do
        if check_port $port; then
            echo -e "${GREEN}✅ $name is ready on port $port${NC}"
            return 0
        fi
        echo -e "${YELLOW}   Attempt $attempt/$max_attempts...${NC}"
        sleep 2
        ((attempt++))
    done

    echo -e "${RED}❌ Timeout: $name did not start on port $port${NC}"
    return 1
}

# Check if MongoDB is running
check_mongodb() {
    echo -e "${BLUE}🐳 Checking MongoDB...${NC}"

    if check_port 27017; then
        echo -e "${GREEN}✅ MongoDB is running on port 27017${NC}"
        return 0
    else
        echo -e "${RED}❌ MongoDB is not running on port 27017${NC}"
        echo -e "${YELLOW}Please start MongoDB first: mongod or systemctl start mongod${NC}"
        exit 1
    fi
}

# A venv can exist and still be dead (e.g. after a system Python upgrade
# its interpreter or site-packages no longer match), so checking for the
# folder isn't enough: actually run it and import the service's main dependency.
check_venv() {
    local service=$1
    local module=$2
    local requirements=$3

    if ! "$SERVICES_DIR/$service/venv/bin/python" -c "import $module" &> /dev/null; then
        echo -e "${RED}❌ $service venv missing or broken (cannot import $module). Recreate it:${NC}"
        echo -e "${YELLOW}  cd services/$service && rm -rf venv && python3 -m venv venv && venv/bin/pip install -r $requirements${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ $service venv OK${NC}"
}

print_dashboard_manual_start() {
    echo -e "${YELLOW}Open a new terminal and run:${NC}"
    echo -e "${GREEN}cd $SERVICES_DIR/dashboard${NC}"
    echo -e "${GREEN}source venv/bin/activate${NC}"
    echo -e "${GREEN}python -m app.main${NC}"
}

# Function to start Rust Engine
start_rust_engine() {
    echo -e "${BLUE}🦀 Starting Rust Engine...${NC}"

    if check_port 8080; then
        echo -e "${GREEN}✅ Rust Engine already running${NC}"
        return 0
    fi

    cd "$SERVICES_DIR/rust-engine"

    # Check if cargo is available
    if ! command -v cargo &> /dev/null; then
        echo -e "${RED}❌ Cargo not found. Install Rust first.${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Compiling and starting Rust Engine...${NC}"
    setsid cargo run &
    RUST_PID=$!

    # Save PID for cleanup
    echo $RUST_PID > /tmp/astroforge_rust.pid

    wait_for_service "Rust Engine" 8080
}

# Function to start Python API
start_python_api() {
    echo -e "${BLUE}🐍 Starting Python API...${NC}"

    if check_port 5001; then
        echo -e "${GREEN}✅ Python API already running${NC}"
        return 0
    fi

    cd "$SERVICES_DIR/python-api"

    echo -e "${YELLOW}Starting Python API...${NC}"
    source venv/bin/activate
    setsid python -m app.main &
    PYTHON_PID=$!

    # Save PID for cleanup
    echo $PYTHON_PID > /tmp/astroforge_python.pid

    wait_for_service "Python API" 5001
}

# Function to open dashboard
open_dashboard() {
    echo -e "${BLUE}📊 Opening Dashboard...${NC}"

    cd "$SERVICES_DIR/dashboard"

    # Determine command to open new terminal
    if command -v gnome-terminal &> /dev/null; then
        echo -e "${GREEN}Opening dashboard in GNOME Terminal...${NC}"
        gnome-terminal --title="AstroForge Dashboard" -- bash -c "cd '$SERVICES_DIR/dashboard' && source venv/bin/activate && python -m app.main; echo -e '\nPress Enter to close...'; read"
    elif command -v konsole &> /dev/null; then
        echo -e "${GREEN}Opening dashboard in Konsole...${NC}"
        konsole --title "AstroForge Dashboard" -e bash -c "cd '$SERVICES_DIR/dashboard' && source venv/bin/activate && python -m app.main; echo -e '\nPress Enter to close...'; read"
    elif command -v xterm &> /dev/null; then
        echo -e "${GREEN}Opening dashboard in XTerm...${NC}"
        xterm -title "AstroForge Dashboard" -e bash -c "cd '$SERVICES_DIR/dashboard' && source venv/bin/activate && python -m app.main; echo -e '\nPress Enter to close...'; read" &
    elif command -v osascript &> /dev/null; then  # macOS
        echo -e "${GREEN}Opening dashboard in Terminal.app (macOS)...${NC}"
        osascript -e "tell app \"Terminal\" to do script \"cd '$SERVICES_DIR/dashboard' && source venv/bin/activate && python -m app.main\""
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then  # Windows
        echo -e "${GREEN}Opening dashboard in new CMD...${NC}"
        start cmd /k "cd /d $SERVICES_DIR/dashboard && venv\Scripts\activate && python -m app.main && pause"
    else
        echo -e "${YELLOW}💡 Terminal not detected automatically.${NC}"
        print_dashboard_manual_start
        echo -e "${YELLOW}Press Enter to continue...${NC}"
        read
    fi
}

# Cleanup function
cleanup() {
    echo -e "\n${BLUE}🧹 Cleaning up services...${NC}"

    # Terminate Python and Rust processes
    if [ -f /tmp/astroforge_python.pid ]; then
        PYTHON_PID=$(cat /tmp/astroforge_python.pid)
        if kill -0 $PYTHON_PID 2>/dev/null; then
            echo -e "${YELLOW}Terminating Python API group (PGID: $PYTHON_PID)...${NC}"
            kill -TERM -- -$PYTHON_PID 2>/dev/null || kill -TERM $PYTHON_PID 2>/dev/null || true
        fi
        rm -f /tmp/astroforge_python.pid
    fi

    if [ -f /tmp/astroforge_rust.pid ]; then
        RUST_PID=$(cat /tmp/astroforge_rust.pid)
        if kill -0 $RUST_PID 2>/dev/null; then
            echo -e "${YELLOW}Terminating Rust Engine group (PGID: $RUST_PID)...${NC}"
            kill -TERM -- -$RUST_PID 2>/dev/null || kill -TERM $RUST_PID 2>/dev/null || true
        fi
        rm -f /tmp/astroforge_rust.pid
    fi

    # Don't terminate MongoDB automatically (might be used by others)
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Signal handling for cleanup
trap 'cleanup; exit 0' INT TERM
trap cleanup EXIT

# Check basic dependencies
echo -e "${BLUE}🔍 Checking dependencies...${NC}"

if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python found${NC}"

if ! command -v cargo &> /dev/null; then
    echo -e "${RED}❌ Cargo (Rust) not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Rust/Cargo found${NC}"

# Check MongoDB
check_mongodb

check_venv python-api flask requirements-dev.txt
check_venv dashboard textual requirements.txt

echo -e "${GREEN}✅ All dependencies OK${NC}\n"

# Start services
start_rust_engine
start_python_api

echo -e "\n${GREEN}🎉 All services are active!${NC}"
echo -e "${BLUE}=====================================${NC}"
echo -e "${GREEN}• MongoDB:     localhost:27017${NC}"
echo -e "${GREEN}• Rust Engine: localhost:8080${NC}"
echo -e "${GREEN}• Python API:  localhost:5001${NC}"
echo -e "${BLUE}=====================================${NC}"

# Open dashboard. Called inside `if` on purpose: under `set -e` a failing
# terminal (crash, no display) would otherwise exit the script, and the
# EXIT trap would then stop the API and engine that are running fine.
if ! open_dashboard; then
    echo -e "${YELLOW}⚠️  Could not open a terminal for the dashboard — services are still running.${NC}"
    print_dashboard_manual_start
fi

echo -e "\n${GREEN}Press Ctrl+C in this launcher terminal to terminate services...${NC}"

echo -e "${YELLOW}Waiting for Ctrl+C in this terminal to stop Rust and Python services...${NC}"

# Keep script active so cleanup runs on interrupt
while true; do
    sleep 1
done
