# syntax=docker/dockerfile:1
FROM node:24.21.0-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337 AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
    STAYLENS_STATIC_DIR=/app/frontend/dist \
    STAYLENS_ARTIFACT_DIR=/app/runtime/model \
    STAYLENS_CATALOG_DIR=/app/runtime/catalog
WORKDIR /app
COPY requirements.lock.txt ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.lock.txt
COPY pyproject.toml ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir --no-deps . \
    && groupadd --gid 10001 staylens \
    && useradd --uid 10001 --gid 10001 --no-create-home staylens
COPY --from=frontend /build/dist/ ./frontend/dist/
COPY .runtime/ ./runtime/
COPY THIRD_PARTY_NOTICES.md ./
ARG VCS_REF=local
ENV STAYLENS_REVISION=$VCS_REF
LABEL org.opencontainers.image.title="StayLens" \
      org.opencontainers.image.source="https://github.com/KawekPL/StayLens" \
      org.opencontainers.image.revision=$VCS_REF
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).read()"
CMD ["python", "-m", "uvicorn", "staylens.production:create_production_app", "--factory", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-access-log", "--no-server-header"]
