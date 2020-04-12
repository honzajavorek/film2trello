import sys
import json

from lxml import html
import requests


USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) '
              'Gecko/20100101 Firefox/72.0')


def generate_urls():
    yield 'https://aerovod.cz/katalog'
    p = 2
    while True:
        yield f'https://aerovod.cz/katalog?p={p}'
        p += 1


film_urls = set()
for url in generate_urls():
    print(url, file=sys.stderr, flush=True)
    response = requests.get(url, headers={'User-Agent': USER_AGENT})
    response.raise_for_status()
    html_tree = html.fromstring(response.content)
    html_tree.make_links_absolute(response.url)

    count = len(film_urls)
    for link in html_tree.cssselect('#catalog-films a'):
        film_urls.add(link.get('href'))
    if count == len(film_urls):
        break
film_urls = sorted(film_urls)


films = []
for url in film_urls:
    print(url, file=sys.stderr, flush=True)
    response = requests.get(url, headers={'User-Agent': USER_AGENT})
    response.raise_for_status()
    html_tree = html.fromstring(response.content)
    html_tree.make_links_absolute(response.url)

    try:
        csfd_url = html_tree.cssselect('a[href*="csfd.cz"]')[0].get('href')
    except IndexError:
        csfd_url = None

    film = dict(url=url, csfd_url=csfd_url)
    print(film, file=sys.stderr, flush=True)
    films.append(film)


print(json.dumps(films, ensure_ascii=False, indent=2))
