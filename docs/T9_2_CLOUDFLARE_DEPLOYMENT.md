# T9.2 Cloudflare deployment

This deployment uses the free Cloudflare Workers plan, a Python Worker, SQLite-backed Durable Objects, and Workers Static Assets. It does not require a VPS, Docker, a credit card, or a separate domain.

## First deployment

1. Create a free Cloudflare account.
2. Run `wrangler login` once. This is the only interactive account step.
3. From the repository root run `scripts\cloudflare_preflight.ps1`.
4. Run `scripts\deploy_cloudflare.ps1`.
5. Open the printed `workers.dev` URL and create a room.

The deploy script builds React assets before deploying `cloudflare/game-room/wrangler.jsonc`. It never creates paid resources. Public deployment was not run in this task because it requires the user's Cloudflare OAuth session.
