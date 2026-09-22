# Guidance for AI agents

## Design

- Keep changes small and code straightforward. Prefer a simple, explicit flow over a generic framework or a new abstraction used only once.
- Keep I/O and orchestration at the edges; put parsing, decisions, and data transformations in small, typed functions that are easy to test.
- Use Python type hints, keep branching shallow, and arrange functions from entry points to smaller helpers where practical.
- Use the project's existing tools and conventions: `uv`, `click`, async `httpx`, and Ruff. Keep imports at module level and avoid `TYPE_CHECKING` blocks.
- Preserve the observable bot messages, card creation/update order, inbox/archive behavior, sorting, and attachment differences between the bot and inbox paths. Treat CSFD browser handling and HTTP retry rules as intentional; read their comments and tests before changing them.
- Log useful diagnostics without logging credentials or other secrets.

## Tests and verification

- For behavior changes, work red-green: write a failing focused test first, then make it pass.
- Favor fast tests of pure logic and a few tests around HTTP, browser, and Trello boundaries. Keep default tests independent of network and current time. Test remote HTML with saved fixtures, including meaningful edge cases.
- Use parametrized tests for related cases; give tests descriptive names and focused assertions.
- Run `uv run pytest` and `uv run ruff check` after Python changes. Use `uv run ruff format --check .` to verify formatting.
