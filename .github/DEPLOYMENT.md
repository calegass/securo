# Production deployment

The active workflow in `workflows/ci.yml` runs backend and frontend checks on
pull requests and pushes. A push to `main` triggers Dokploy only after both
checks pass.

## GitHub configuration

Create a GitHub environment named `production` and add these environment
secrets:

- `DOKPLOY_API_KEY`: an API key generated in the Dokploy profile settings.
- `DOKPLOY_COMPOSE_ID`: the ID of the Securo Docker Compose service in Dokploy.

## Cloudflare configuration

Keep the Dokploy panel private. Allow public access only to:

- Method: `POST`
- Host: `dokploy.calegari.dev.br`
- Path: `/api/compose.deploy`

Dokploy authenticates this request using the `x-api-key` header. The
`/api/deploy/github` endpoint is reserved for signed GitHub App webhooks and is
not used by this workflow.

The files in `workflows-disabled/` are inherited upstream release, badge, and
container-publishing workflows. GitHub ignores them because workflows are only
loaded directly from `.github/workflows/`.
