# Deployment

The UI is deployed to Vercel. The API services run on an EC2 host with Docker Compose. Postgres, Redis, and Prometheus may remain managed or on separate hosts; the compose file connects to them through environment variables.

## Database migration

Run migrations from the repository root using a direct Postgres connection. Do not commit the connection string:

```bash
export MIGRATION_DB_URL='postgresql://postgres:<password>@<host>:5432/postgres?sslmode=require'
python db/apply.py db/migrations/0008_workspace_users.sql
```

Migrations are idempotent. Apply earlier migrations in numeric order on a new database.

## EC2 services

Install Docker and the Compose plugin on the host, copy this repository, and create an untracked `.env` beside `docker-compose.ec2.yml`:

```dotenv
DATABASE_URL=postgresql+psycopg2://postgres:<password>@<host>:5432/postgres?sslmode=require
CORS_ALLOW_ORIGINS=https://<your-vercel-domain>
AUTH_DISABLED=false
JWT_SECRET=<long-random-secret>
PROMETHEUS_URL=http://<prometheus-host>:9090
PROMETHEUS_PUSHGATEWAY_URL=http://<pushgateway-host>:9091
RABBITMQ_USER=<rabbitmq-user>
RABBITMQ_PASSWORD=<long-random-password>
PINECONE_API_KEY=<optional>
PINECONE_INDEX=<optional>
VOYAGE_API_KEY=<optional>
```

Start the API stack and verify the public gateway:

```bash
docker compose -f docker-compose.ec2.yml up -d --build
docker compose -f docker-compose.ec2.yml ps
curl https://<api-domain>/health
```

Expose only the gateway port through the EC2 security group. Keep service ports internal to the Docker network. Put TLS and a stable DNS name in front of the gateway with an ALB or reverse proxy.

## Vercel UI

Import `ui-service` as the Vercel project. Set:

```dotenv
VITE_API_BASE=https://<api-domain>
```

The project builds with `npm run build`, emits `dist`, and uses `vercel.json` so React Router routes resolve on refresh. Add the final Vercel origin to `CORS_ALLOW_ORIGINS` on EC2, then restart the gateway.

## Operational notes

- No AWS access keys belong in Dockerfiles, compose files, Vercel variables, or git. AWS access is obtained through the tenant’s configured role flow.
- The compose file uses Docker service DNS names, so localhost URLs must not be copied into the EC2 environment.
- Pinecone and model credentials are only passed to the insight service and should be rotated through the deployment secret manager.
