# film2trello

Turns film links to Trello cards 🍿

## TODO

- Port trello tests
- Port readme
- Remove legacy folder, also from pyproject.toml
- In Trello board, deal with the tv shows somehow

## Setup

-   Install by Poetry
-   Set `TELEGRAM_TOKEN` environment variable to the token BotFather gives you
-   Set `TRELLO_TOKEN` environment variable to something I don't remember where I've got it
-   Set `TRELLO_KEY` environment variable to something I don't remember where I've got it
-   Verify which Trello board you want to use, because the default value is set to ours (override with `--board`)
-   Verify which Telegram users you want to allow and how they map to your Trello users, because the default values are set to us (override with `--user`)
-   Run `film2trello` executable
-   Stop by Ctrl+C

## Code

-   Format code with `isort . && black .`
