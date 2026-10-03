# Security

Do not open public issues for vulnerabilities that could expose download clients or *arr API keys.

Report privately via [GitHub security advisories](https://github.com/HairyDuck/untickarr/security/advisories/new).

Untickarr stores Transmission, Sonarr, Radarr, and Pushover credentials in `/data/settings.json`. Mount that volume privately. Never publish a filled-in settings file.
