#!/usr/bin/env bash
# exit on error
set -o errexit

# Install system dependencies required for psycopg2
apt-get update
apt-get install -y python3-dev libpq-dev

# Install Python dependencies
pip install --upgrade pip
pip install psycopg2-binary
pip install -r requirements.txt 