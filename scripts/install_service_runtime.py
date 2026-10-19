import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from operia.security.service_runtime import install

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Offline pinned service runtime installation into new staging')
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    print(json.dumps(install(args.root, Path(__file__).resolve().parents[1] / 'requirements.txt')))
