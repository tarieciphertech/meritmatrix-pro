# MeritMatrix Pro — Oracle Cloud API deployment

This deployment file is intentionally separate from the development Compose stack. It does **not** start, replace, or expose a second PostgreSQL server, and it binds the API to localhost so an existing TLS reverse proxy can forward traffic to it.

## 1. Prepare the Oracle instance

- Confirm Docker Engine and the Docker Compose plugin are installed.
- Use a dedicated Linux account for the application; do not run the API container as root.
- Clone/update this repository in a stable directory and enter `meritmatrix-backend/`.
- Confirm the existing PostgreSQL server is backed up and reachable from the API container.
- Keep the PostgreSQL port private; do not open port 5432 publicly.

## 2. Configure production environment

Copy `.env.example` to `.env` and set all production values. At minimum:

- `ENVIRONMENT=production`
- `DEBUG=false`
- `DATABASE_URL=postgresql+psycopg://…` pointing to the existing production database
- independent random `SECRET_KEY` and `JWT_SECRET` values (at least 32 characters)
- `CORS_ORIGINS` to the exact frontend origin(s), comma-separated
- `FRONTEND_URL` to the deployed frontend URL
- SMTP settings if password/notification email delivery is enabled
- A real SMS provider if phone OTP activation is enabled; never use mock OTP in production

Do not commit `.env`, paste secrets into issues, or print secret values in deployment logs. Ensure the application database user has only the database privileges it needs.

## 3. Back up and deploy

Take a PostgreSQL backup using the backup procedure already used for this Oracle instance and verify the backup file is readable. Then run:

```bash
cd meritmatrix-backend
DB_BACKUP_CONFIRMED=1 ./deploy-oracle.sh
```

The script validates required settings, builds the production image, applies Alembic migrations, starts the API, and checks `http://127.0.0.1:8000/health`. It deliberately refuses to run unless the backup confirmation variable is set.

The API listens only on `127.0.0.1:8000`. Configure the existing Nginx/Caddy/Apache reverse proxy and TLS certificate to forward the API hostname to that local port. Do not expose port 8000 directly to the public internet.

## 4. Smoke-test after deployment

1. Open `https://YOUR_API_HOST/health` and confirm `status=ok` and `database=connected`.
2. Open `https://YOUR_API_HOST/api/v1/docs` only if API docs are intended to be public; otherwise restrict them at the reverse proxy.
3. Test staff login and token refresh.
4. Test one school admin can only access their assigned school.
5. Test teacher assignment, attendance register read/write, assessment creation, marks save, publish, report-card generation, and fee charge/payment flows.
6. Test a guardian can select only linked schools and sees only linked students, published results, attendance and fee balances.
7. Check logs with `docker compose -f docker-compose.production.yml logs --tail=150 backend`; never share tokens or database credentials.

## 5. Rollback notes

Do not automatically downgrade migrations after a failed release. Inspect the failed migration and database state, restore from the verified backup if necessary, and deploy a known-good image/commit. Preserve the existing database and other services on the Oracle host.
