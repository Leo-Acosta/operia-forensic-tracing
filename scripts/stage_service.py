"""Create a new private service staging tree, without modifying the working copy."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from operia.security.service_staging import stage

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(json.dumps(stage(Path(__file__).resolve().parents[1], args.destination)))
