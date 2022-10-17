# film2trello

Simple app which allows me and my wife to use [Trello](http://trello.com/) as our "To Watch" list for films. Currently works with URLs to films at [CSFD.cz](http://csfd.cz) and [KVIFF.TV](https://kviff.tv).

![screenshot](screenshot.png)

## How does it work?

When you navigate to the main page of the app, it allows you to submit an URL of a film. When submitted, it downloads basic information about the film and creates a card in the first column (assumed inbox) of your "To Watch" Trello board.

Your Trello username is remembered using cookies. The Trello board is hardcoded in the settings of a particular instance of the app.

### Bookmarklet

After submitting your first film, the page offers you a [bookmarklet](https://en.wikipedia.org/wiki/Bookmarklet). You can drag it into your browser's interface and make it a button. Every time you're on a page about a film, e.g. [csfd.cz/film/8365-vyvoleny/](http://www.csfd.cz/film/8365-vyvoleny/), and you want to save it to your "To Watch" Trello board as a card, just click on the button.


## Installation

### Preparation

Set the following environment variables:

- **`TRELLO_KEY`** - Get it at the [Trello app key page](https://trello.com/app-key).
- **`TRELLO_TOKEN`** - Get it at the [Trello app key page](https://trello.com/app-key). Make a GET request to `https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&name=film2trello&key=<TRELLO_KEY>`, where `TRELLO_KEY` is the key above.
- **`TRELLO_BOARD`** - An ID of the Trello board you want to work with. Get it from its URL, e.g. if the URL of the board is `https://trello.com/b/mF7A3n3J/filmy-test`, then `mF7A3n3J` is the ID.
- **`FLASK_SECRET_KEY`** - Something random (see [docs](https://flask.palletsprojects.com/en/1.1.x/config/#SECRET_KEY)).

### Development

Create a virtual environment and install dependencies from the `requirements.txt` file. Run `pytest` to execute tests. To run the app locally:

```
$ FLASK_DEBUG=1 FLASK_APP=film2trello flask run --port=3000 --reload
```

### Deployment

The app runs on [Fly.io](https://fly.io/). Install their `flyctl`. Then you can do things like `flyctl launch --name=film2trello` or `flyctl deploy`. Use the following to prepare the environment:

```
$ flyctl secrets set TRELLO_KEY=... TRELLO_TOKEN=... TRELLO_BOARD=... FLASK_SECRET_KEY=...
```

The app also uses GitHub Actions. It needs the `TRELLO_BOARD`, `TRELLO_KEY`, and `TRELLO_TOKEN` secrets set on the [secrets setting page](https://github.com/honzajavorek/film2trello/settings/secrets/actions). The rest is in the `.github` directory.

### Automatic Deployment

Set GitHub Actions secret `FLY_API_TOKEN` to a value you get by running `flyctl auth token`.

## License

[MIT](LICENSE)
