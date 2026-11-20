"""
tests/run_tests.py
Standalone test runner for the Timetable Scheduler engine.
Can be executed with 'python3 tests/run_tests.py' or 'pytest'.
"""

import sys
import os
import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main():
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 70)
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}, Failures: {len(result.failures)}")
    if result.wasSuccessful():
        print("ALL TESTS PASSED SUCCESSFULLY! (100% PASS RATE)")
    else:
        print("SOME TESTS FAILED.")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
