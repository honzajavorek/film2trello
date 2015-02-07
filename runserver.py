#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os

from film2trello import app


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
