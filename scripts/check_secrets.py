#!/usr/bin/env python3
"""Scan added staged text for credential patterns; never print matched values."""
import sys
import re
import subprocess

# Staged files (Added, Copied, Modified)
cmd = ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACM"]
res = subprocess.run(cmd, capture_output=True, text=True, check=True)
staged_files = [f for f in res.stdout.split("\0") if f]

if not staged_files:
    sys.exit(0)

# Secret regex patterns: (Name, Pattern)
SECRET_PATTERNS = [
    ("AWS Access Key ID", re.compile(r'(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}')),
    ("AWS Secret Access Key", re.compile(r'(?i)aws_secret_access_key\s*[:=]\s*["\']?[A-Za-z0-9/+=]{40}["\']?')),
    ("Private Key", re.compile(r'-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY-----')),
    ("OpenAI API Key", re.compile(r'sk-[a-zA-Z0-9]{32,}')),
    ("Anthropic API Key", re.compile(r'sk-ant-api03-[a-zA-Z0-9_\-]{80,}')),
    ("GitHub Personal Access Token", re.compile(r'(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36}')),
    ("Generic High-Entropy API Key / Token", re.compile(r'(?i)(?:api_key|apikey|secret_key|client_secret|auth_token)\s*[:=]\s*["\'][a-zA-Z0-9_\-]{20,}["\']')),
    ("Hardcoded Database Credentials", re.compile(r'(?:postgres|postgresql|mysql|mongodb\+srv)://[^:]+:[^@]+@[^/]+'))
]

found_secrets = False

for filepath in staged_files:
    # Skip symlinks, deleted files, binary files
    try:
        diff_cmd = ["git", "diff", "--cached", "-U0", "--", filepath]
        diff_res = subprocess.run(diff_cmd, capture_output=True, text=True, check=True)
    except Exception:
        print(f"❌ Secret scan could not read staged diff: {filepath}")
        sys.exit(1)

    # Only scan added lines in diff
    for line in diff_res.stdout.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            content = line[1:]
            for name, pattern in SECRET_PATTERNS:
                if pattern.search(content):
                    print(f"❌ [SECRET DETECTED] File: {filepath} | Pattern: {name}")
                    found_secrets = True

if found_secrets:
    print("\n🚨 Pre-commit hook failed: Staged changes contain sensitive credentials/secrets.")
    print("   Please remove secrets or use environment variables before committing.")
    sys.exit(1)

print("✅ Secret scanner passed cleanly.")
