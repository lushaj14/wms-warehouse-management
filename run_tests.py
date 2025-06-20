#!/usr/bin/env python3
"""
Test runner script
==================
Projedeki testleri çalıştırmak için kullanılır.
"""
import sys
import subprocess
from pathlib import Path


def run_tests(test_type="all", verbose=True, coverage=True):
    """
    Testleri çalıştırır
    
    Args:
        test_type: "all", "unit", "integration", "fast", "slow"
        verbose: Detaylı çıktı
        coverage: Coverage raporu
    """
    base_cmd = ["python", "-m", "pytest"]
    
    # Test tipi seçimi
    if test_type == "unit":
        base_cmd.extend(["tests/unit/"])
    elif test_type == "integration":
        base_cmd.extend(["tests/integration/"])
    elif test_type == "fast":
        base_cmd.extend(["-m", "not slow"])
    elif test_type == "slow":
        base_cmd.extend(["-m", "slow"])
    else:
        base_cmd.extend(["tests/"])
    
    # Seçenekler
    if verbose:
        base_cmd.append("-v")
    
    if coverage:
        base_cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
    
    # Parallel execution
    base_cmd.extend(["-n", "auto"])
    
    print(f"Running: {' '.join(base_cmd)}")
    
    try:
        result = subprocess.run(base_cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Tests failed with exit code {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("Error: pytest not found. Install with: pip install pytest")
        return 1


def main():
    """Ana fonksiyon"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run project tests")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "fast", "slow"],
        default="all",
        help="Test type to run"
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    parser.add_argument(
        "--quiet",
        action="store_true", 
        help="Minimal output"
    )
    
    args = parser.parse_args()
    
    # Proje root'unda olduğumuzu kontrol et
    if not Path("app").exists():
        print("Error: Must be run from project root directory")
        sys.exit(1)
    
    exit_code = run_tests(
        test_type=args.type,
        verbose=not args.quiet,
        coverage=not args.no_coverage
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()