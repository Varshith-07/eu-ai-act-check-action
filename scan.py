#!/usr/bin/env python3
"""
AgenticQA EU AI Act Compliance Scanner
Classifies repositories under Annex III and checks Art.9/13/14/22 conformity.
https://github.com/nhomyk/eu-ai-act-check-action
"""
import json
import os
import sys
from pathlib import Path

MINIMAL_SARIF = {
    "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
    "version": "2.1.0",
    "runs": [{
        "tool": {
            "driver": {
                "name": "AgenticQA EU AI Act Scanner",
                "version": "1.0.0",
                "informationUri": "https://github.com/nhomyk/eu-ai-act-check-action",
                "rules": []
            }
        },
        "results": []
    }]
}

def _safe_path(env_var: str, default: str, must_exist: bool = False) -> str:
    """Resolve env var to a real path, preventing path traversal (CWE-22)."""
    raw = os.environ.get(env_var, default)
    resolved = os.path.realpath(raw)
    if must_exist and not os.path.exists(resolved):
        print(f"Warning: {env_var}={raw} does not exist, using default", file=sys.stderr)
        resolved = os.path.realpath(default)
    return resolved

repo_path = _safe_path('SCAN_REPO_PATH', '.', must_exist=True)
sarif_output = _safe_path('SARIF_OUTPUT', 'eu-ai-act-results.sarif')
fail_on_noncompliant = os.environ.get('FAIL_ON_NONCOMPLIANT', 'false').lower() == 'true'

findings_count = 0
critical_count = 0
conformity_score = 1.0
risk_category = 'minimal_risk'
annex_iii_categories = []
evidence = None

# ── Run EU AI Act Compliance Check ────────────────────────────────────────────
print("🔍 Running EU AI Act Compliance Check...")
print(f"   Repo: {Path(repo_path).resolve()}")

try:
    from agenticqa.compliance.ai_act import AIActComplianceChecker

    result = AIActComplianceChecker().check(repo_path)

    if result.scan_error:
        print(f"   Scan error: {result.scan_error}", file=sys.stderr)
    else:
        conformity_score = result.conformity_score
        risk_category = result.risk_category
        annex_iii_categories = result.annex_iii_match
        evidence = result

        # Count findings
        for f in result.findings:
            findings_count += 1
            if f.severity == 'critical' and f.status == 'missing':
                critical_count += 1

        print(f"   Risk category:    {risk_category}")
        print(f"   Conformity score: {conformity_score:.4f}")
        if annex_iii_categories:
            print(f"   Annex III match:  {', '.join(annex_iii_categories)}")
        print(f"   Findings:         {findings_count} ({critical_count} critical gaps)")

        for f in result.findings:
            status_icon = {'present': '✅', 'partial': '⚠️', 'missing': '❌'}.get(f.status, '?')
            print(f"   {status_icon} {f.article}: {f.requirement} [{f.status}]")

except ImportError as e:
    print(f"   AIActComplianceChecker not available: {e}", file=sys.stderr)
except Exception as e:
    print(f"   Compliance scan error: {e}", file=sys.stderr)


# ── Export to SARIF ───────────────────────────────────────────────────────────
print(f"\n📄 Writing SARIF → {sarif_output}")
sarif_count = 0

try:
    from agenticqa.export.sarif import SARIFExporter

    exporter = SARIFExporter(repo_root=repo_path)

    sev_map = {'critical': 'error', 'high': 'warning', 'medium': 'note', 'low': 'note'}
    status_desc = {'present': 'COMPLIANT', 'partial': 'PARTIAL', 'missing': 'MISSING'}

    if evidence:
        for f in evidence.findings:
            rule_id = f'EUAIACT_{f.article.replace(".", "").upper()}_{f.status.upper()}'
            # Determine file and line from evidence string
            ev = f.evidence or 'not found'
            file_path = ev if not ev.startswith('not') and '/' in ev else '.'
            line = 1

            exporter._add(
                rule_id,
                f'{f.article} — {f.requirement}: {status_desc.get(f.status, f.status)}. {f.remediation}',
                file_path,
                line,
                severity=sev_map.get(f.severity, 'note'),
                rule_desc=(
                    f'EU AI Act {f.article}: {f.requirement}. '
                    f'Fine exposure: up to €30M or 6% global turnover for high-risk violations.'
                ),
            )
            sarif_count += 1

        # Add Annex III classification finding if high_risk
        if risk_category == 'high_risk' and annex_iii_categories:
            exporter._add(
                'EUAIACT_ANNEXIII_HIGH_RISK',
                (f'Annex III High-Risk Classification: {", ".join(annex_iii_categories)}. '
                 f'Conformity score: {conformity_score:.2f}. '
                 f'Full compliance required before deployment. '
                 f'Enforcement: August 2026 for high-risk systems.'),
                '.',
                1,
                severity='warning',
                rule_desc='EU AI Act Annex III — High-risk AI system classification.',
            )
            sarif_count += 1

    exporter.write(sarif_output)
    print(f"   {sarif_count} finding(s) written to SARIF")

except Exception as e:
    print(f"   SARIF export error ({e}) — writing fallback", file=sys.stderr)
    with open(sarif_output, 'w') as fh:
        json.dump(MINIMAL_SARIF, fh)


# ── GitHub Step Summary ───────────────────────────────────────────────────────
summary_file = os.path.realpath(os.environ.get('GITHUB_STEP_SUMMARY', ''))
if os.environ.get('GITHUB_STEP_SUMMARY', ''):
    score_pct = int(conformity_score * 100)
    if score_pct >= 90:
        score_icon = '🟢'
    elif score_pct >= 60:
        score_icon = '🟡'
    elif score_pct >= 30:
        score_icon = '🟠'
    else:
        score_icon = '🔴'

    risk_labels = {
        'high_risk': '🔴 High-Risk (Annex III)',
        'limited_risk': '🟡 Limited Risk',
        'minimal_risk': '🟢 Minimal Risk',
    }

    lines = [
        f'## {score_icon} EU AI Act Compliance — {score_pct}% Conformity',
        '',
        f'**Risk Category:** {risk_labels.get(risk_category, risk_category)}  ',
        f'**Conformity Score:** {conformity_score:.4f} / 1.0  ',
        f'**Critical Gaps:** {critical_count}  ',
        '',
    ]

    if annex_iii_categories:
        lines += [
            f'> ⚠️ **Annex III categories matched:** {", ".join(annex_iii_categories)}',
            '> Full compliance required before deployment (enforcement: August 2026).',
            '',
        ]

    if evidence and evidence.findings:
        lines += [
            '| Article | Requirement | Status | Severity |',
            '|---------|------------|--------|----------|',
        ]
        for f in evidence.findings:
            status_icon = {'present': '✅', 'partial': '⚠️', 'missing': '❌'}.get(f.status, '?')
            lines.append(f'| {f.article} | {f.requirement} | {status_icon} {f.status} | {f.severity} |')

    lines += [
        '',
        '*Powered by [AgenticQA](https://github.com/nhomyk/AgenticQA) · '
        '[eu-ai-act-check-action](https://github.com/nhomyk/eu-ai-act-check-action)*',
    ]

    with open(summary_file, 'a') as fh:
        fh.write('\n'.join(lines) + '\n')


# ── GitHub Output Variables ───────────────────────────────────────────────────
github_output = os.path.realpath(os.environ.get('GITHUB_OUTPUT', ''))
if os.environ.get('GITHUB_OUTPUT', ''):
    with open(github_output, 'a') as fh:
        fh.write(f'conformity_score={conformity_score}\n')
        fh.write(f'risk_category={risk_category}\n')
        fh.write(f'annex_iii_categories={",".join(annex_iii_categories)}\n')
        fh.write(f'findings_count={findings_count}\n')
        fh.write(f'critical_count={critical_count}\n')


# ── Summary ───────────────────────────────────────────────────────────────────
print(f'\n📊 Risk category: {risk_category} | Conformity: {conformity_score:.4f} | Critical gaps: {critical_count}')

if risk_category == 'high_risk':
    print('⚠️  High-risk AI system detected under Annex III — full compliance required by August 2026')


# ── Exit code ─────────────────────────────────────────────────────────────────
if fail_on_noncompliant and critical_count > 0:
    print(f'\n❌ Failing: {critical_count} critical compliance gap(s) and fail-on-noncompliant=true')
    sys.exit(1)

print('\n✅ EU AI Act compliance check complete')
