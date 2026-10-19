"""Startup gates are a minimum policy, never a production-readiness certificate."""
import os
from operia.security.private_files import read_key, token_info, assert_private


def findings(config):
    issues = []
    mode = config.env.lower()
    if mode not in ('local','test','docker-local','production'):
        issues.append('environment_unknown')
    if mode != 'production': issues.append('production_mode_not_selected')
    if os.name != 'nt':
        issues.append('production_os_profile_unvalidated')
    else:
        try:
            token = token_info()
            if token['elevated'] or token['system'] or token.get('administrator_member',False):
                issues.append('supervisor_privileged_token')
        except RuntimeError:
            issues.append('supervisor_token_unverifiable')
    if config.auth_signing_key is not None: issues.append('inline_signing_key_not_allowed')
    if config.auth_signing_key_file is None:
        issues.append('production_secret_file_required')
    else:
        try:
            read_key(config.auth_signing_key_file)
            assert_private(config.auth_signing_key_file.absolute().parent)
        except (OSError, RuntimeError): issues.append('secret_file_invalid_or_not_private')
    if config.local_recovery_enabled: issues.append('production_recovery_must_be_disabled')
    if '*' in config.cors_origins or any(not origin.startswith('https://') for origin in config.cors_origins):
        issues.append('production_https_origins_required')
    return issues


def enforce_production(config):
    if config.env.lower() not in ('local','test','docker-local','production'):
        raise RuntimeError('environment_unknown')
    if config.env.lower() == 'production':
        issues = findings(config)
        if issues: raise RuntimeError('production_policy_rejected:' + ','.join(issues))
