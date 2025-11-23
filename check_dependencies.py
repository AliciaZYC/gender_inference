#!/usr/bin/env python3
"""
Check if all required dependencies are installed
"""

import sys

def check_dependencies():
    """Check if all required packages are installed"""
    print("=" * 60)
    print("Checking Dependencies")
    print("=" * 60)
    
    dependencies = {
        'pymongo': 'MongoDB driver',
        'gridfs': 'GridFS for file storage (part of pymongo)',
        'gender_guesser': 'Name gender detection',
        'requests': 'HTTP requests for Face++ API',
        'pandas': 'Data processing',
        'numpy': 'Numerical computation',
    }
    
    missing = []
    installed = []
    
    for package, description in dependencies.items():
        try:
            if package == 'gridfs':
                # gridfs is imported from pymongo
                from gridfs import GridFS
                version = "included in pymongo"
            elif package == 'pymongo':
                import pymongo
                version = pymongo.__version__
            elif package == 'gender_guesser':
                import gender_guesser
                version = "installed"
            elif package == 'requests':
                import requests
                version = requests.__version__
            elif package == 'pandas':
                import pandas
                version = pandas.__version__
            elif package == 'numpy':
                import numpy
                version = numpy.__version__
            
            print(f"✓ {package:<20} {version:<15} - {description}")
            installed.append(package)
        except ImportError:
            print(f"✗ {package:<20} {'NOT INSTALLED':<15} - {description}")
            missing.append(package)
    
    print("\n" + "=" * 60)
    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print("\nTo install missing packages:")
        for pkg in missing:
            if pkg == 'gridfs':
                print(f"  - gridfs is part of pymongo, install: pip install pymongo")
            else:
                print(f"  - pip install {pkg}")
        return False
    else:
        print("✓ All dependencies are installed!")
        return True

if __name__ == "__main__":
    success = check_dependencies()
    sys.exit(0 if success else 1)

