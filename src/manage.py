#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

def main():
    """Run administrative tasks."""
    # Import and configure Django
    from boot_django import boot_django
    boot_django()
    
    # Import Django's management command execution
    from django.core.management import execute_from_command_line
    
    # Execute the command
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
