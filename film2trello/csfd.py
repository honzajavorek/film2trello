import re
from urllib.parse import urlparse


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
    srcset = html_tree.xpath('//*[@class="film-posters"]//img')[0].get('srcset')
    srcset_list = re.split(r'\s+', srcset)

    urls = [f'https:{url}' for url in srcset_list[::2]]
    zoom = [int(re.sub(r'\D', '', z)) for z in srcset_list[1::2]]

    srcset_parsed = dict(zip(zoom, urls))
    return srcset_parsed[max(srcset_parsed.keys())]


def parse_durations(html_tree):
    text = html_tree.xpath('//*[@class="origin"]')[0].text_content().lower()
    match = re.search(r'minutáž:\s+([\d\–\-]+)\s+min', text)
    if match:
        yield from map(int, re.split(r'\D+', match.group(1)))
    else:
        for match in re.finditer(r'\b(\d+)\s+min\b', text):
            yield int(match.group(1))
