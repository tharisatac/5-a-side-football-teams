# Builds one image that serves the web API and the React UI.
#
#   docker compose up --build            # with the local Postgres
#   docker build -t football .           # just the image
#
# Two stages: Node builds the UI, then only the built files are copied into
# a slim Python image, so Node and the dev tools never reach the final image.

# ---- Stage 1: build the React UI into web/dist -------------------------
FROM node:22.20.0-alpine AS ui
WORKDIR /web
# Install packages first, in their own layer, so Docker can reuse it while
# only the UI code changes.
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ---- Stage 2: the app ---------------------------------------------------
FROM python:3.14.7-slim
# Print logs straight away, and don't write .pyc files into the image.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY schema.sql main.py ./
COPY src/ src/
COPY --from=ui /web/dist web/dist

# Don't run as root: if the app were ever compromised, the attacker would
# only have this unprivileged user's permissions.
RUN useradd --create-home app
USER app

# Cloud Run tells the container which port to listen on via $PORT.
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn src.api:app --host 0.0.0.0 --port ${PORT}"]
