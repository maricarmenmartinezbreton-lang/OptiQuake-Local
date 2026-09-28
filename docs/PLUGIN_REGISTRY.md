# Community Plugin Registry

`registry/plugins.json` is the repository-managed index of known OptiQuake Local extensions.

## Adding a plugin
1. Publish the plugin source in a public repository or package index.
2. Document its author, license, supported Plugin API version, and purpose.
3. Add a registry entry in a focused pull request.
4. Include a reproducible test or demonstration.
5. Disclose network access, stored data, and external services.

## Trust model
Registry inclusion is discovery, not a security or scientific certification. Users should review third-party code before installing it.

Plugins that claim earthquake classification, magnitude estimation, or early warning must provide evidence appropriate to those claims.

## Compatibility
The current stable extension contract is **Plugin API v1**. Breaking changes require a new API version so older plugins can be detected rather than silently misused.
