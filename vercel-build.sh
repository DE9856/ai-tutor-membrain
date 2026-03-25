#!/bin/bash
echo "Using Python version:"
python --version
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r frontend/requirements.txt