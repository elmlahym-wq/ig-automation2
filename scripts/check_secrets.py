"""Check publishable working-tree files without printing matched values."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache'}
PATTERNS = {
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'Meta access token': re.compile(r'\bEA[A-Za-z0-9]{50,}\b'),
    'GitHub token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b'),
    'credentialed database URL': re.compile(r'postgres(?:ql)?(?:\+psycopg)?://[^\s:/]+:([^\s@]+)@'),
    'literal secret assignment': re.compile(r'^[ \t]*(?:FACEBOOK_APP_SECRET|INSTAGRAM_ACCESS_TOKEN|DASHBOARD_PASSWORD|WEBHOOK_VERIFY_TOKEN)[ \t]*=[ \t]*[\'\"]?([^\s\'\"#]+)', re.MULTILINE),
}


def is_placeholder(value):
    return any(part in value.lower() for part in ('test-only', 'example', 'your_', '<', 'os.getenv', 'os.environ', 'secrets.', 're.compile'))


def candidates():
    result = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True)
    if result.returncode == 0:
        return [ROOT / p for p in result.stdout.decode().split('\0') if p]
    return [p for p in ROOT.rglob('*') if p.is_file() and not any(x in IGNORED for x in p.relative_to(ROOT).parts)]


def main():
    findings = []
    for path in candidates():
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if path.name.startswith('.env') and path.name != '.env.example':
            findings.append((str(relative), 'environment file'))
            continue
        if path.name.upper().startswith(('DEPLOYMENT_SECRETS', 'SECRETS.')):
            findings.append((str(relative), 'secret inventory file'))
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                value = match.group(1) if match.lastindex else match.group()
                if not is_placeholder(value):
                    findings.append((str(relative), label))
    for path, label in sorted(set(findings)):
        print(f'{path}: {label} detected (value withheld)')
    if findings:
        return 1
    print('No targeted secret patterns found in publishable working-tree files.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
