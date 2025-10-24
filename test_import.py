#!/usr/bin/env python
# Test script to check missing dependencies

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing imports...")
    from src.environment.research import ResearchEnvironment
    print("✓ ResearchEnvironment imported successfully")
    from src.environment.battle import BattleEnvironment
    print("✓ BattleEnvironment imported successfully")
    print("\n✅ All imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
