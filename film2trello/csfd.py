# -*- coding: utf-8 -*-


import re
import urlparse

import requests
from lxml import html


def scrape_film(url):
    res = requests.get(normalize_url(url))
    res.raise_for_status()
    dom = html.fromstring(res.content)

    return {
        'url': res.url,
        'title': parse_title(dom),
        'poster_url': parse_poster_url(dom),
    }


def normalize_url(url):
    match = re.search(r'csfd\.cz/film/(\d+)', url)
    if match:
        return 'http://www.csfd.cz/film/{}/'.format(match.group(1))
    raise ValueError


def parse_title(dom):
    text = dom.xpath('//title')[0].text_content()
    return re.sub(ur' \| ČSFD\.cz$', '', text)


def parse_poster_url(dom):
    url = dom.xpath('//img[@class="film-poster"]')[0].get('src')
    scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
    return urlparse.urlunparse(('http', netloc, path, '', '', ''))
