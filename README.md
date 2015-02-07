# film2trello

Simple app which allows me to use Trello as my "To Watch" list. Currently works with [csfd.cz](http://csfd.cz) only.

## Installation

The app should be able to run anywhere, but following documentation presumes you're using Debian-derived Linux, e.g. Ubuntu.

1.  You need [Redis](http://redis.io/):

    ```shell
    $ sudo apt-get install redis-server redis-tools
    ```

2.  Get code of this app:

    ```shell
    $ git clone git@github.com:honzajavorek/film2trello.git
    $ cd film2trello
    ```

3.  In this step you want to use [virtual environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/). Details on this are out of scope of this tutorial.
4.  Inside your virtual environment, install dependencies:

    ```shell
    $ pip install -r requirements.txt
    ```

5.  The app expets several environment values:

    - `TRELLO_KEY` - Key from [trello.com/app-key](https://trello.com/app-key).
    - `TRELLO_SECRET` - Secret from [trello.com/app-key](https://trello.com/app-key).

    Set them in your terminal. The easiest is to do it one by one using `export TRELLO_KEY="..."` command.

6.  Run development server:

    ```shell
    $ python runserver.py
    ```

7.  Open [http://0.0.0.0:5000](http://0.0.0.0:5000) in your favorite browser.

## Heroku Deployment

The app is [Heroku](https://heroku.com/)-ready. Following documentation presumes you're using Debian-derived Linux, e.g. Ubuntu.

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

4.  The app expets several environment values:

    - `REDIS_URL` or `REDISTOGO_URL` - Connection URL for Redis.
    - `SECRET_KEY` - Secret key for sessions/cookies.
    - `TRELLO_KEY` - Key from [trello.com/app-key](https://trello.com/app-key).
    - `TRELLO_SECRET` - Secret from [trello.com/app-key](https://trello.com/app-key).

    Set them for your Heroku app. The easiest is to do it one by one using `heroku config:set TRELLO_KEY="..."` command.

3.  Deploy!

    ```shell
    $ git push heroku master
    ```
