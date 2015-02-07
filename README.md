# film2trello

Simple app which allows me to use [Trello](http://trello.com/) as my "To Watch" list for films. Currently works with [csfd.cz](http://csfd.cz) only.

## Status: PET PROJECT

Under development and maintenance only if I feel so.

## How does it work?

Homepage of this app offers you a [bookmarklet](https://en.wikipedia.org/wiki/Bookmarklet). You can drag it into your browser's interface and make it a button. Every time you're on [csfd.cz](http://csfd.cz) page about a film, e.g. [www.csfd.cz/film/8365-vyvoleny/](http://www.csfd.cz/film/8365-vyvoleny/), and you want to save it to your "To Watch" Trello board as a card, just click on the button.

The app asks you for details (authorization with Trello, selecting Trello board, etc.) on the fly, so you don't need to set up anything in advance.

## Known issues

- No tests.
- Crappy interface.
- No error handling whatsoever.
- No way to add the card to a column other than the first one.
- Support only for [csfd.cz](http://csfd.cz). Planned:
    - [imdb.com](http://www.imdb.com/)
    - any generic page containing a link to either csfd.cz or imdb.com

## Instructions

- [Installation](docs/installation.md)
- [Heroku Deployment](docs/heroku.md)
