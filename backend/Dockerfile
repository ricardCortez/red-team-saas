# =============================================================================
# Stage 1: Builder — genera wheels de Python
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Solo lo necesario para compilar extensiones C:
#   build-essential + gcc  → paquetes genéricos con extensiones C
#   libpq-dev              → psycopg2 headers
#   libffi-dev             → cffi / cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# =============================================================================
# Stage 2: Runtime — imagen mínima para ejecutar la app
# =============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime libs (required for the app)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libffi8 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Security tool binaries available in Debian repos — each in its own RUN so one
# missing package never aborts the rest. Failures are intentionally allowed (|| true).
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends nmap 2>/dev/null \
    && rm -rf /var/lib/apt/lists/* \
    || rm -rf /var/lib/apt/lists/*

RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends hydra john medusa whois sqlmap 2>/dev/null \
    && rm -rf /var/lib/apt/lists/* \
    || rm -rf /var/lib/apt/lists/*

# Python-based CLI tools
RUN pip install --no-cache-dir shodan 2>/dev/null || true

# gobuster static binary
RUN curl -fsSL "https://github.com/OJ/gobuster/releases/download/v3.6.0/gobuster_linux_amd64.tar.gz" \
       -o /tmp/gobuster.tar.gz 2>/dev/null \
    && tar xzf /tmp/gobuster.tar.gz -C /usr/local/bin gobuster 2>/dev/null \
    && chmod +x /usr/local/bin/gobuster \
    && rm -f /tmp/gobuster.tar.gz \
    || rm -f /tmp/gobuster.tar.gz

# Usuario no-root (uid 1000)
RUN groupadd -g 1000 appuser \
    && useradd -u 1000 -g appuser -s /bin/bash -m appuser

# Instalar wheels desde el builder
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels

# Copiar código de la aplicación
COPY --chown=appuser:appuser app/        ./app/
COPY --chown=appuser:appuser alembic/    ./alembic/
COPY --chown=appuser:appuser templates/  ./templates/
COPY --chown=appuser:appuser alembic.ini .

RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
