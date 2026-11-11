#!/usr/bin/env python
"""
PharmaTrack CLI Entrypoint.
Execute with: python cli.py
"""
import sys
import os

# Ensure current directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from cli_app import main

if __name__ == "__main__":
    main()
