"""Read-only audit of minimum startup policy; no secret contents or internal paths."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from operia.core.config import settings
from operia.security.production import findings

if __name__ == '__main__':
    issues = findings(settings)
    print(json.dumps({'schema':'operia-production-audit/1','minimum_policy_passed':not issues,'findings':issues,
        'operational_acceptance':'Still requires dedicated account, gateway TLS, egress, MFA, monitoring, shared quotas and independent recovery validation'},ensure_ascii=False))
    raise SystemExit(1 if issues else 0)
