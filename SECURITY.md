# Security Policy

OptiQuake Local is experimental research software and is not a life-safety system.

## Plugin security
Plugins are Python code executed in the OptiQuake process. Plugin API v1 does **not** provide a sandbox.

Only install plugins whose source and publisher you trust. Review code before granting access to cameras, microphones, files, networks, credentials, or automation systems.

Registry inclusion is not a security certification or endorsement.

## Reporting security issues
Do not publish credentials, private recordings, personal data, or exploitable secrets in public issues.

When the GitHub repository is public, security-sensitive reports should use GitHub's private vulnerability-reporting mechanism if enabled. Otherwise contact the project maintainer privately before public disclosure.

## Scientific safety
A plugin or contribution must not convert a local vibration event into a claim of confirmed earthquake, magnitude, or guaranteed early warning without appropriate independent validation.
