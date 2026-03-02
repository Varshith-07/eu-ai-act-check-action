# eu-ai-act-check-action

<div align="center">

### The first GitHub Action that checks your AI system for EU AI Act conformity — Annex III classification, Articles 9, 13, 14, and 22 — before you deploy.

[![GitHub Marketplace](https://img.shields.io/badge/GitHub%20Marketplace-eu--ai--act--check--action-blue?logo=github&logoColor=white&style=for-the-badge)](https://github.com/marketplace/actions/eu-ai-act-compliance-check)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![SARIF](https://img.shields.io/badge/Output-SARIF%202.1.0-orange?style=for-the-badge)](https://sarifweb.azurewebsites.net/)
[![No API Key](https://img.shields.io/badge/API%20Key-Not%20Required-brightgreen?style=for-the-badge)](#no-api-key-required)

**Enforcement is live. Fines up to €30M or 6% global revenue. One line of YAML.**

</div>

---

## Why This Exists

The EU AI Act is not a future threat. Prohibited AI systems have been banned since February 2025. High-risk systems under Annex III — employment, credit, education, healthcare, law enforcement, critical infrastructure — face full compliance requirements by August 2026.

Most AI engineering teams are not checking for compliance in CI. Violations are discovered in audits, not pipelines.

This action brings automated EU AI Act conformity checking to every pull request — classifying your system under Annex III and checking for evidence of Articles 9, 13, 14, and 22 before any code ships.

---

## Quickstart — One Line

```yaml
- uses: nhomyk/eu-ai-act-check-action@v1
```

Add it to any job that checks out your code. That's it.

---

## Full Workflow

```yaml
name: EU AI Act Compliance

on: [push, pull_request]

jobs:
  eu-ai-act:
    name: EU AI Act Compliance Check
    runs-on: ubuntu-latest
    permissions:
      security-events: write   # upload findings to GitHub Security tab
      contents: read

    steps:
      - uses: actions/checkout@v4

      - uses: nhomyk/eu-ai-act-check-action@v1
        id: compliance
        with:
          fail-on-noncompliant: 'true'   # block deploys on critical gaps

      - name: Show conformity score
        run: |
          echo "Risk category: ${{ steps.compliance.outputs.risk-category }}"
          echo "Conformity:    ${{ steps.compliance.outputs.conformity-score }}"
```

Findings appear under **Security → Code scanning alerts.**

---

## What It Checks

### Step 1: Annex III Risk Classification

The action scans your README, package files, and dependency lists to classify your system's risk tier under the EU AI Act's high-risk categories:

| Annex III Category | Examples |
|-------------------|---------|
| `employment` | Hiring, recruitment, workforce management, performance review |
| `credit` | Loan approval, creditworthiness scoring, underwriting |
| `education` | Exam assessment, admission decisions, student grading |
| `legal` | Contract analysis, litigation support, legal decisions |
| `critical_infra` | Power grids, water systems, transport, hospitals |
| `biometric` | Face recognition, fingerprint, iris scan, voice ID |
| `law_enforcement` | Fraud detection, predictive policing, surveillance |

Classification only triggers for systems that actually use AI/ML — detected via library dependencies (`anthropic`, `openai`, `torch`, `transformers`, `langchain`, etc.), model files, or AI keywords in documentation.

### Step 2: Four Article Checks

| Article | Requirement | What It Looks For |
|---------|------------|-------------------|
| **Art. 9** | Risk management system | `RISK_MANAGEMENT.md`, risk register, circuit breakers, fallback handlers |
| **Art. 13** | Transparency — inform users of AI | `AI-generated` labels, `ai_generated` fields, disclosure in UI code |
| **Art. 14** | Human oversight — monitor and override | `require_human_review()`, `human_override`, audit logs, escalation paths |
| **Art. 22** | Automated decisions — right to explanation | Human override before pass/fail decisions, appeal mechanism |

Each article is assessed as `present` / `partial` / `missing` with a conformity score and specific remediation guidance.

---

## Output — GitHub Security Tab

Findings upload as **SARIF 2.1.0** to your repository's **Security → Code scanning** page:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Security  /  Code scanning alerts                                   │
│                                                                      │
│  ● EUAIACT_ART9_MISSING   Error    Risk management system not found  │
│  ● EUAIACT_ART13_MISSING  Warning  No AI transparency disclosure     │
│  ● EUAIACT_ART22_MISSING  Error    No human override for AI decisions│
│  ● EUAIACT_ANNEXIII       Warning  High-risk: employment, credit     │
│                                                                      │
│  4 open alerts  ·  Powered by AgenticQA EU AI Act Scanner            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Step Summary

After every run, a compliance table appears in your workflow's Summary tab:

```
🟡 EU AI Act Compliance — 50% Conformity

Risk Category: 🔴 High-Risk (Annex III)
Conformity Score: 0.5000 / 1.0
Critical Gaps: 2

⚠️ Annex III categories matched: employment, credit
   Full compliance required before deployment (enforcement: August 2026).

| Article | Requirement                          | Status   | Severity |
|---------|--------------------------------------|----------|----------|
| Art.9   | Risk management system documented    | ❌ missing | critical |
| Art.13  | AI-generated output disclosed        | ✅ present | medium   |
| Art.14  | Human oversight mechanism            | ⚠️ partial | high     |
| Art.22  | Automated decisions have human override | ❌ missing | critical |
```

---

## Use Outputs in Downstream Steps

```yaml
- uses: nhomyk/eu-ai-act-check-action@v1
  id: compliance

# Block deployment for high-risk non-compliant systems
- name: Compliance gate
  if: |
    steps.compliance.outputs.risk-category == 'high_risk' &&
    steps.compliance.outputs.critical-count != '0'
  run: |
    echo "❌ High-risk system with ${{ steps.compliance.outputs.critical-count }} critical gaps"
    echo "   Conformity score: ${{ steps.compliance.outputs.conformity-score }}"
    exit 1

# Save SARIF as artifact
- name: Upload compliance report
  uses: actions/upload-artifact@v4
  with:
    name: eu-ai-act-sarif
    path: ${{ steps.compliance.outputs.sarif-file }}
```

---

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `repo-path` | `.` | Path to the repository root to scan |
| `fail-on-noncompliant` | `false` | Exit code 1 if any critical compliance gaps exist |
| `sarif-output` | `eu-ai-act-results.sarif` | SARIF output filename |
| `upload-sarif` | `true` | Upload to GitHub Code Scanning (`security-events: write` required) |
| `category` | `eu-ai-act` | SARIF category — useful when running multiple compliance scans |

## Outputs

| Output | Values | Description |
|--------|--------|-------------|
| `conformity-score` | 0.0–1.0 | Overall conformity (1.0 = fully compliant) |
| `risk-category` | `high_risk` · `limited_risk` · `minimal_risk` | Annex III classification |
| `annex-iii-categories` | comma-separated | Matched high-risk categories |
| `findings-count` | integer | Total article findings |
| `critical-count` | integer | Critical compliance gaps |
| `sarif-file` | path | Location of the generated SARIF file |

---

## The Regulatory Stakes

| Without this action | With this action |
|---------------------|-----------------|
| Compliance audit discovery: **months after deployment** | Compliance gaps caught at every pull request |
| Fine for high-risk violations: **up to €30M or 6% global revenue** | $0 — automated, continuous, in CI |
| Compliance consultant for AI Act audit: **€50,000–€200,000** | Open source, deterministic, no API key |
| "We didn't know it was high-risk" is not a defense | Annex III classification runs on every push |

> High-risk AI systems that deploy without evidence of Art.9/13/14/22 compliance face enforcement actions from national supervisory authorities. The gap between "we have an AI system" and "we have documented compliance evidence" is the gap this action closes.

---

## Compliance Timeline

| Date | Milestone |
|------|-----------|
| **Feb 2025** | Prohibited AI systems banned (Art. 5) |
| **Aug 2025** | GPAI model rules apply |
| **Aug 2026** | **High-risk system rules fully enforced** — Annex III systems must demonstrate Art.9/13/14/22 compliance |
| Ongoing | National supervisory authorities conducting audits |

---

## No API Key Required

All checking is **pure static analysis.** The action:

- Never calls an LLM
- Never sends your code to an external service
- Produces results deterministically — same code, same findings, every run
- Works entirely within your GitHub Actions runner

---

## How It Works

```
Your repo
    │
    ├── Annex III classifier    → scans README, package files, dep lists
    │                             detects AI/ML usage + high-risk domain keywords
    │                             outputs: high_risk | limited_risk | minimal_risk
    │
    ├── Art. 9 checker          → looks for RISK_MANAGEMENT.md, risk register,
    │                             circuit_breaker, fallback_handler patterns
    │
    ├── Art. 13 checker         → looks for AI-generated labels in UI code,
    │                             ai_generated fields in API responses
    │
    ├── Art. 14 checker         → looks for require_human_review(), human_override,
    │                             audit_log, escalation mechanisms
    │
    └── Art. 22 checker         → detects pass/fail = llm_output patterns,
                                  checks for human override + appeal mechanism
                                          │
                                          ▼
                                 SARIFExporter (2.1.0)
                                          │
                                          ▼
                          GitHub Security → Code scanning alerts
```

---

## Powered by AgenticQA

This action wraps the compliance scanners from **[AgenticQA](https://github.com/nhomyk/AgenticQA)** — an open-source autonomous CI/CD platform for AI-native teams.

AgenticQA adds to your pipeline:
- **EU AI Act compliance** (this action)
- **MCP security scanning** — [mcp-scan-action](https://github.com/marketplace/actions/mcp-security-scan)
- **HIPAA PHI detection** — 5 PHI taint categories across your codebase
- **Self-healing CI** — SRE agent auto-fixes lint errors and test failures
- **Adversarial hardening** — Red Team agent with 20 bypass techniques + constitutional gate
- **SOC 2 / GDPR** — 7 compliance scanners, SARIF-exportable evidence

[Explore AgenticQA →](https://github.com/nhomyk/AgenticQA)

---

## License

MIT © [nhomyk](https://github.com/nhomyk)
