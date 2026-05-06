# Security Policy

## Reporting a Security Vulnerability

If you discover a security vulnerability in OpenAxiom, please do NOT open a public issue.

Contact the repository owner directly via GitHub Issues with the `security` label, or reach out through the repository's discussion page.

## What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Scope

The following are **NOT** considered security vulnerabilities:
- Dataset files committed to the repository (they should not be there)
- `.venv` issues (recreate with `pip install`)
- Missing backup files (user-managed)

## Expectations

- You will receive an acknowledgment within 7 days
- We will work with you to understand and resolve the issue
- Once resolved, a security advisory may be published

## Important

- Never commit API keys, tokens, passwords, or personal data to this repository
- The `.gitignore` file is configured to exclude common sensitive files
- If you accidentally commit sensitive data, rotate the credential immediately and contact the maintainer
