# Production deployment

The active workflows deliberately avoid running the same checks twice:

- `workflows/ci.yml` checks pull requests targeting `main` (and supports a
  complete manual run).
- `workflows/deploy.yml` triggers Dokploy when the already-checked pull request
  is merged into `main` (and also supports a manual deploy).

Protect `main` in GitHub and require the CI checks before merging. The deploy
workflow assumes that changes only reach `main` through that protected path.

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
