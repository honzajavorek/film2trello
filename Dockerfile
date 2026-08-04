FROM python:3.14-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /bin/

ENV PORT=8080
# Compile to .pyc, don't buffer stdout/stderr, install into a project-local venv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Run as a dedicated non-root user
RUN useradd --create-home --uid 1000 app
WORKDIR /app
RUN chown app:app /app
USER app

# Install dependencies first (cached unless the lockfile changes), then the project
COPY --chown=app:app pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY --chown=app:app . .
RUN uv sync --frozen --no-dev

CMD ["film2trello", "bot"]
