# Security Policy

## Supported Versions

Security fixes are applied to the active `main` branch and to the latest public GitHub release.

## Reporting a Vulnerability

Please report security issues privately to `support@aspose.com`.

Include the affected version or commit, a minimal reproduction when possible, and whether the issue affects font parsing, serialization, generated assets, CI/CD, or release automation.

Do not include secrets, private keys, access tokens, or proprietary font files in public issues.

## Secret Handling

Repository configuration uses environment variables for credentials and deployment tokens. Local `.env` files are ignored by Git and `.env.example` contains names only, without secret values.
