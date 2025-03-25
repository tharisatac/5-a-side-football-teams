#!/bin/bash

# Step 1: Create a virtual environment
python3 -m venv venv

# Step 2: Activate the virtual environment
# For Unix-based systems (Linux/MacOS)
source venv/bin/activate

# For Windows, use the following line instead
# .\venv\Scripts\activate

# Step 3: Install dependencies
pip install -r requirements.txt

echo "Virtual environment set up successfully and dependencies installed!"