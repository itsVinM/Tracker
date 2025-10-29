#!/bin/bash
echo "Starting Streamlit app..."

# Navigate to project root
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Set database path for the app
export DB_PATH="$(pwd)/TrackerSource/project_tracker.db"

# Open browser automatically
xdg-open http://localhost:8501 &

# Run Streamlit app
streamlit run TrackerSource/TRACKER.py --server.port 8501