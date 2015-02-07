# film2trello

Simple app which allows me to use Trello as my "To Watch" list. Currently works with [csfd.cz](http://csfd.cz) only.

## Development

Install dependencies:

```
$ pip install -r requirements.txt
```

Run server:

```
$ python runserver.py
```

Open `http://0.0.0.0:5000` in browser.

## Deployment

1. You need [Redis](http://redis.io/): `heroku addons:add redistogo`.
2. Expected environment values:

    - `REDIS_URL` or `REDISTOGO_URL` - Connection URL for Redis.
    - `SECRET_KEY` - Secret key for sessions/cookies.
    - `TRELLO_KEY` - Key from [trello.com/app-key](https://trello.com/app-key).
    - `TRELLO_SECRET` - Secret from [trello.com/app-key](https://trello.com/app-key).

3. Now you can deploy to [Heroku](https://heroku.com/), there's `Procfile` and `requirements.txt`.
