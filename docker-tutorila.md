# Docker Tutorial

This guide explains how to build and run the app container locally.

## Prerequisites

- Docker installed and running
- Project root as your current directory

## 1) Build the image

```bash
docker build -t jae:local .
```

## 1.1) Recommended: run with Docker Compose

This project now includes `docker-compose.yml` with correct env + port mappings.

```bash
docker compose up --build
```

Open: `http://localhost:3000`

Stop:

```bash
docker compose down
```

## 2) Run the container

`GOOGLE_API_KEY` is required for model-backed features.

```bash
docker run --rm --env-file .env -p 3000:3000 -p 8000:8000 jae:local
```

This loads all key/value pairs from your local `.env` file into the container.
Your `.env` is used only at runtime and is not baked into the image.

Then open: `http://localhost:3000`

## 3) Run in detached mode (background)

```bash
docker run -d --name jae-app --env-file .env -p 3000:3000 -p 8000:8000 jae:local
```

View logs:

```bash
docker logs -f jae-app
```

Stop and remove:

```bash
docker rm -f jae-app
```

## 4) Health check

Check container health status:

```bash
docker inspect --format '{{.State.Health.Status}}' jae-app
```

Expected value: `healthy`

## 5) Useful runtime environment variables

- `PORT` (default: `3000`)
- `BACKEND_PORT` (default: `8000`)
- `GOOGLE_API_KEY` (required for AI calls)
- `MODEL_NAME` (optional)
- `UPLOAD_BASE_DIR` (optional)

Example custom ports:

```bash
docker run --rm -p 4000:4000 \
  -p 8000:8000 \
  --env-file .env \
  -e PORT=4000 \
  jae:local
```

## 6) Quick troubleshooting

- Port in use: change `-p host:container` and set matching `PORT`.
- App won’t start: check logs with `docker logs <container-name>`.
- Build cache issues: rebuild with `docker build --no-cache -t jae:local .`.
- API errors: verify `GOOGLE_API_KEY` is set and valid.
