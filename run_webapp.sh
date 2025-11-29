#!/bin/bash
# Launch IRCI Web Application
# This script starts the Streamlit web interface for IRCI

echo "========================================="
echo "  IRCI Web Application Launcher"
echo "========================================="
echo ""

# Check if streamlit is installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "❌ Streamlit not installed. Installing dependencies..."
    pip install streamlit plotly
    echo ""
fi

# Check if irci is installed
if ! python -c "import irci" 2>/dev/null; then
    echo "❌ IRCI not installed. Installing..."
    pip install -e .
    echo ""
fi

echo "✓ Starting IRCI Web Application..."
echo ""
echo "📊 Access the app at: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "========================================="
echo ""

# Start streamlit
streamlit run app.py \
    --server.port 8501 \
    --server.address localhost \
    --browser.gatherUsageStats false \
    --server.headless true
