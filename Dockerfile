FROM python:3.14-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /bin/

ENV PORT=8080
# Compile to .pyc, don't buffer stdout/stderr, install into a project-local venv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install dependencies first (cached unless the lockfile changes), as root:
# Camoufox's Firefox build needs system libraries only apt can install, and
# that needs root, so this has to happen before switching to the app user.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
# `playwright` directly, not `uv run playwright`: uv run re-syncs the
# project first, which fails this early since src/ isn't copied in yet.
RUN playwright install-deps firefox

# Run as a dedicated non-root user from here on
RUN useradd --create-home --uid 1000 app
RUN chown -R app:app /app
USER app

COPY --chown=app:app . .
RUN uv sync --frozen --no-dev

# Downloads Camoufox's patched Firefox build into the app user's own cache
# dir, since that's the user the app also runs as (see CMD below).
RUN camoufox fetch

CMD ["film2trello", "bot"]
