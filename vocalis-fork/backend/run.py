"""
Startup script for VoiceClaw backend on Railway/cloud platforms.

This script handles the package import issue when running with uvicorn.
"""

import sys
import os

# Add the parent directory to the path so we can import as a package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the app from main module
from main import app

# Export app for uvicorn
__all__ = ['app']
