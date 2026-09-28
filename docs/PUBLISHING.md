# Publishing OptiQuake Local

## PyPI

OptiQuake Local uses PyPI Trusted Publishing through GitHub OIDC.
No long-lived PyPI API token is stored in GitHub.

One-time PyPI pending-publisher configuration:

- PyPI project name: `optiquake-local`
- GitHub owner: `maricarmenmartinezbreton-lang`
- Repository: `OptiQuake-Local`
- Workflow: `release.yml`
- Environment: `pypi`

The GitHub `pypi` environment requires owner review before deployment.
The workflow builds a wheel and source distribution before publishing.

## Zenodo

Zenodo uses the repository `CITATION.cff` metadata.
A separate `.zenodo.json` is intentionally not used to avoid duplicate metadata sources.

One-time setup:

1. Sign in to Zenodo and link the GitHub account.
2. Open the GitHub integration and sync repositories.
3. Enable `OptiQuake-Local`.
4. Archive a GitHub release from the Zenodo repository view.

After integration, new GitHub releases can be automatically ingested by Zenodo.
