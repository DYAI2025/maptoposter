"""
Fix for matplotlib backend issues on macOS
"""

import os
import matplotlib
import sys

def setup_matplotlib_backend():
    """
    Set up the appropriate matplotlib backend for the platform
    """
    # Check if we're on macOS
    if sys.platform.startswith('darwin'):
        # For macOS, try different backends in order of preference
        backends_to_try = ['Agg', 'TkAgg', 'Qt5Agg']
        
        for backend in backends_to_try:
            try:
                matplotlib.use(backend, force=True)
                print(f"Successfully set matplotlib backend to {backend}")
                break
            except ImportError:
                print(f"Backend {backend} not available, trying next...")
                continue
    else:
        # For other platforms, use Agg as default
        matplotlib.use('Agg', force=True)
        print("Set matplotlib backend to Agg")


# Call this function when importing
setup_matplotlib_backend()