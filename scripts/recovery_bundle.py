"""Operator-only offline recovery. No HTTP endpoint, scheduling or implicit overwrite."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from operia.security import recovery_bundle as bundle


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('backup','verify','restore'))
    parser.add_argument('source',type=Path,help='Project root for backup, encrypted bundle for verify/restore')
    parser.add_argument('destination',type=Path,nargs='?')
    parser.add_argument('--storage',type=Path)
    parser.add_argument('--database',type=Path)
    parser.add_argument('--signing-key-file',type=Path)
    parser.add_argument('--quiesced',action='store_true',help='Operator confirms API/workers/writers stopped; not an automatic freeze')
    args=parser.parse_args()
    try:
        if args.action=='verify': result=bundle.verify(args.source)
        elif args.action=='restore':
            if args.destination is None: parser.error('Se requiere un destino nuevo')
            result=bundle.restore(args.source,args.destination)
        else:
            if args.destination is None or args.storage is None or args.database is None or args.signing_key_file is None:
                parser.error('Backup requiere destino, --storage, --database y --signing-key-file explícitos')
            result=bundle.create(args.source,args.storage,args.database,args.destination,args.signing_key_file,quiesced=args.quiesced)
        print(json.dumps({'ok':True,**result},ensure_ascii=False))
    except Exception as error:
        code=str(error) if isinstance(error,RuntimeError) and str(error).startswith(('backup_','private_','auth_','windows_')) else 'backup_operation_failed'
        print(json.dumps({'ok':False,'code':code}),file=sys.stderr)
        raise SystemExit(1) from None

if __name__=='__main__': main()
