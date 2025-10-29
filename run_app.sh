#!/bin/bash
echo "Starting Tracker App..."

# Navigate to script directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate


# Open browser automatically
xdg-open http://localhost:8501 &

# Run the main Python file
streamlit run TrackerSource/TRACKER.py