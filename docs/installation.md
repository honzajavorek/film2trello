# Installation

The app should be able to run anywhere, but following documentation presumes you're using [Debian](https://en.wikipedia.org/wiki/Debian)-derived [Linux](https://en.wikipedia.org/wiki/Linux), e.g. [Ubuntu](http://www.ubuntu.com/).

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

5.  The app expects several environment values:

    - `TRELLO_KEY` - Key from [trello.com/app-key](https://trello.com/app-key).
    - `TRELLO_SECRET` - Secret from [trello.com/app-key](https://trello.com/app-key).

    Set them in your terminal. The easiest is to do it one by one using `export TRELLO_KEY="..."` command.

6.  Run development server:

    ```shell
    $ python runserver.py
    ```

7.  Open [http://0.0.0.0:5000](http://0.0.0.0:5000) in your favorite browser.
