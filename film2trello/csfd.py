import re
from urllib.parse import urlparse, urlunparse


class InvalidURLError(ValueError):
    pass


def normalize_url(url):
    match = re.search(r'csfd\.cz/film/(\d+)', url)
    if match:
        return 'https://www.csfd.cz/film/{}/'.format(match.group(1))
    raise InvalidURLError(url)


def parse_title(html_tree):
    text = html_tree.xpath('//title')[0].text_content()
    return re.sub(r' \| ČSFD\.cz$', '', text)


def parse_poster_url(html_tree):
    url = html_tree.xpath('//img[@class="film-poster"]')[0].get('src')
    scheme, netloc, path, params, query, fragment = urlparse(url)
    return urlunparse(('https', netloc, path, '', '', ''))


def parse_durations(html_tree):
    text = html_tree.xpath('//p[@class="origin"]')[0].text_content().lower()
    match = re.search(r'minutáž:\s+([\d\–\-]+)\s+min', text)
    if match:
        yield from map(int, re.split(r'\D+', match.group(1)))
    else:
        for match in re.finditer(r'\b(\d+)\s+min\b', text):
            yield int(match.group(1))
