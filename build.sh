#!/bin/bash
# Install dependencies
pip install -r requirements.txt

# Build single binary
python3 -m PyInstaller --onefile --name natnest main.py

echo "✅ Build complete! Binary is located at: dist/natnest"
