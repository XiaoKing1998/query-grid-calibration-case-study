"""Read-only candidate-release audit. Never print matching secrets or snippets."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

TEXT_SUFFIXES = {'.py', '.txt', '.md', '.json', '.jsonl', '.csv', '.toml', '.yaml', '.yml', '.ps1', '.sh', '.cfg', '.ini', '.cff', '.tex', '.bib', '.gitignore'}
PAYLOAD_SUFFIXES = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.pth', '.pt', '.pkl', '.pickle', '.npy', '.npz', '.zip', '.gz', '.7z', '.tar', '.db', '.sqlite'}
PATTERNS = {
    'private_key_marker': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'github_credential_pattern': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b'),
    'huggingface_credential_pattern': re.compile(r'\bhf_[A-Za-z0-9]{20,}\b'),
    'openai_credential_pattern': re.compile(r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{25,}\b'),
    'cloud_access_id_pattern': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'absolute_windows_path': re.compile(r'(?<![A-Za-z])[A-Za-z]:[\\/][^\s\"\']+'),
    'absolute_personal_unix_path': re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+(?:/[^\s\"\']*)?'),
    'private_conversation_marker': re.compile(r'(?:<system>|<developer>|BEGIN PRIVATE|Message Type: NEW_TASK|Sender: /root|密码是|口令是|访问令牌是)'),
}
SECRET_NAME = re.compile(r'(?:password|passwd|api[_-]?key|access[_-]?token|auth[_-]?token|secret)', re.I)
QUOTED_SECRET = re.compile(r'''["']?(?:password|passwd|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)["']?\s*[:=]\s*["']([^"'\r\n]{8,})["']''', re.I)


def audit(root: Path, output: Path) -> dict:
    findings = []
    files = []
    excluded_generated = []
    self_path = Path(__file__).resolve()
    for path in sorted(root.rglob('*')):
        if not path.is_file() or '.git' in path.relative_to(root).parts:
            continue
        rel = path.relative_to(root).as_posix()
        if path.relative_to(root).parts[0] == 'build' or any(part.endswith('.egg-info') for part in path.relative_to(root).parts):
            excluded_generated.append(rel)
            continue
        if path.resolve() == output or path.name in {'security_scan.json', 'security_scan.md', 'security_scan_findings.json'}:
            continue
        if path.is_symlink():
            findings.append({'file': rel, 'line': None, 'category': 'symlink_not_followed', 'classification': 'review'})
            continue
        if path.name in {'.env', '.netrc', '.pypirc', 'credentials'} or path.name.startswith('.env.'):
            findings.append({'file': rel, 'line': None, 'category': 'credential_filename_not_opened', 'classification': 'block'})
            continue
        raw = path.read_bytes()
        files.append({'file': rel, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        if path.suffix.lower() in PAYLOAD_SUFFIXES:
            findings.append({'file': rel, 'line': None, 'category': 'data_or_model_payload_extension', 'classification': 'review'})
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            continue
        if path.resolve() != self_path:
            for number, line in enumerate(text.splitlines(), 1):
                for label, pattern in PATTERNS.items():
                    if pattern.search(line):
                        findings.append({'file': rel, 'line': number, 'category': label,
                                         'classification': 'block' if 'credential' in label or 'private_key' in label else 'review'})
                for match in QUOTED_SECRET.finditer(line):
                    if not any(x in match.group(1).lower() for x in ('example', 'placeholder', '${', '<', 'none', 'test')):
                        findings.append({'file': rel, 'line': number, 'category': 'quoted_secret_named_value', 'classification': 'review'})
        if path.name.endswith(('.py', '.py.txt')):
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue
                val = node.value
                names = node.targets if isinstance(node, ast.Assign) else [node.target]
                if isinstance(val, ast.Constant) and isinstance(val.value, str) and len(val.value) >= 8:
                    if any(isinstance(n, ast.Name) and SECRET_NAME.search(n.id) for n in names):
                        if not any(x in val.value.lower() for x in ('example', 'placeholder', '${', '<', 'none')):
                            findings.append({'file': rel, 'line': node.lineno, 'category': 'literal_secret_named_assignment', 'classification': 'review'})
    return {'schema_version': 1, 'generated_utc': datetime.now(timezone.utc).isoformat(),
            'scope': 'current local release checkout; no credential stores or research data opened',
            'files_scanned': len(files), 'file_manifest': files,
            'excluded_generated_not_in_release': excluded_generated,
            'finding_count': len(findings), 'findings': findings,
            'blocking_pattern_count': sum(x['classification'] == 'block' for x in findings),
            'status': 'PATTERN_SCAN_CLEAR' if not findings else 'REVIEW_FINDINGS',
            'limitations': ['Pattern-based only; no guarantee of exhaustive secret detection.',
                           'Results apply only to the hashes listed; rerun after modifications.',
                           'No matching values or source snippets are emitted.']}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    if not output.is_relative_to(root / 'provenance'):
        raise SystemExit('Report output must stay under the selected checkout provenance directory.')
    result = audit(root, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'files_scanned', 'finding_count', 'blocking_pattern_count')}))
    for finding in result['findings']:
        print(json.dumps(finding))


if __name__ == '__main__':
    main()
