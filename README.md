# film2trello

Personal Telegram bot which turns [CSFD.cz](http://csfd.cz) and [KVIFF.TV](https://kviff.tv) film links to [Trello](http://trello.com/) cards 🍿
Allows me and my wife to use Trello as our "To Watch" list for films.
Assumed Trello board structure:

-   First column is an inbox, a "To Watch" list.
-   Any number of "Seen" columns follows, e.g. "Seen in 2024", "Seen in 2023"…
-   Last column is "Archive".
    If a card is in the inbox for several years, it gets moved out of the way to this archive.

## TODO

- Implement sorting
- Fix https://trello.com/c/nKWsYvUv/543-maestro-bernstein-pracovn%C3%AD-n%C3%A1zev-2023
- In Trello board, deal with the tv shows somehow

## Setup

-   Install by Poetry
-   Set `TELEGRAM_TOKEN` environment variable to the token BotFather gives you
-   Set `TRELLO_KEY` environment variable to something you get at [Trello Power-Ups Admin](https://trello.com/power-ups/admin/)
-   Set `TRELLO_TOKEN` environment variable to something you get at [Trello Power-Ups Admin](https://trello.com/power-ups/admin/), alternatively make a GET request to `https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&name=film2trello&key=<TRELLO_KEY>`, where `TRELLO_KEY` is the key above.
-   Verify which Trello board you want to use, because the default value for the board ID is set to ours.
    Override it with `--board`.
    Get the ID of your board from its URL, e.g. if the URL of the board is `https://trello.com/b/mF7A3n3J/filmy-test`, then `mF7A3n3J` is the ID.
-   Verify which Telegram users you want to allow and how they map to your Trello users, because the default values are set to us.
    Override it with `--user`, e.g. `--user=119318534:honzajavorek`.
    You can use the option multiple times to allow more users.
    I don't remember how I've got the Telegram account IDs, ask the internet.
-   Run `film2trello bot`
-   Stop by Ctrl+C

## Development

-   Use Poetry to manage dependencies
-   Run `pytest` to test
-   Run `ruff check` to lint
-   Run `ruff format` to format code

## Deployment

The app runs on [Fly.io](https://fly.io/). Install their `flyctl`. Then you can do things like `flyctl launch --name=film2trello` or `flyctl deploy`. Use the following to prepare the environment:

```
$ flyctl secrets set TRELLO_KEY=... TRELLO_TOKEN=... TELEGRAM_TOKEN=...
```

The app also uses GitHub Actions. It needs the `TRELLO_KEY`, and `TRELLO_TOKEN` secrets set on the [secrets setting page](https://github.com/honzajavorek/film2trello/settings/secrets/actions). The rest is in the `.github` directory.

## Automatic Deployment

Set GitHub Actions secret `FLY_API_TOKEN` to a value you get by running `flyctl auth token`.

## License

[MIT](LICENSE)
