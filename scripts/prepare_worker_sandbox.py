"""Build a private stdlib runtime and grant AppContainers read/execute on it only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from operia.security.sandbox_runtime import prepare

if __name__ == "__main__":
    print(prepare())
