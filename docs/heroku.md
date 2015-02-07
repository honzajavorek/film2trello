# Heroku Deployment

The app is [Heroku](https://heroku.com/)-ready. Following documentation presumes you're [Debian](https://en.wikipedia.org/wiki/Debian)-derived [Linux](https://en.wikipedia.org/wiki/Linux), e.g. [Ubuntu](http://www.ubuntu.com/).

1.  Make sure you can work with Heroku:

    ```shell
    $ wget -qO- https://toolbelt.heroku.com/install-ubuntu.sh | sh  # installing Heroku Toolbelt
    $ heroku login
    ```

2.  In directory with `film2trello`'s code, set up your new Heroku app:

    ```shell
    $ heroku create "my-film2trello"  # optionally: --region eu
    ```

3.  Install [Redis](http://redis.io/), e.g. [Redis To Go](https://addons.heroku.com/redistogo), which has a free plan:

    ```shell
    $ heroku addons:add redistogo
    ```

4.  The app expects several environment values:

    - `REDIS_URL` or `REDISTOGO_URL` - Connection URL for Redis.
    - `SECRET_KEY` - Secret key for sessions/cookies.
    - `TRELLO_KEY` - Key from [trello.com/app-key](https://trello.com/app-key).
    - `TRELLO_SECRET` - Secret from [trello.com/app-key](https://trello.com/app-key).

    Set them for your Heroku app. The easiest is to do it one by one using `heroku config:set TRELLO_KEY="..."` command.

3.  Deploy!

    ```shell
    $ git push heroku master
    ```

4.  View in your favorite browser:

    ```shell
    $ heroku open
    ```
