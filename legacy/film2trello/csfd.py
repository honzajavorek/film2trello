import re
from urllib.parse import urlparse


TITLE_YEAR_RE = re.compile(r'\((\d{4})\)\s*$')


class InvalidURLError(ValueError):
    pass


def normalize_url(url):
    match = re.search(r'csfd\.cz/film/(\d+)', url)
    if match:
        return 'https://www.csfd.cz/film/{}/'.format(match.group(1))
    raise InvalidURLError(url)


def parse_title(html_tree):
    title_text = html_tree.cssselect('title')[0].text_content().strip()
    main_title_text = title_text.split('|')[0].strip()

    year = int(TITLE_YEAR_RE.search(main_title_text).group(1))
    title = TITLE_YEAR_RE.sub('', main_title_text).strip()

    try:
        first_lang = html_tree.cssselect('.film-names li')[0]
    except IndexError:
        return f'{title} ({year})'
    else:
        first_lang_text = re.sub(r'\s*\(více\)', '', first_lang.text_content().strip())

        if title == first_lang_text:
            return f'{title} ({year})'
        return f'{title} / {first_lang_text} ({year})'


def parse_poster_url(html_tree):
    srcset = html_tree.cssselect('.film-posters img')[0].get('srcset')
    if not srcset:
        return None

    srcset_list = re.split(r'\s+', srcset)
    urls = [f'https:{url}' for url in srcset_list[::2]]
    zoom = [int(re.sub(r'\D', '', z)) for z in srcset_list[1::2]]

    srcset_parsed = dict(zip(zoom, urls))
    return srcset_parsed[max(srcset_parsed.keys())]


def parse_durations(html_tree):
    text = html_tree.cssselect('.origin')[0].text_content().lower()
    match = re.search(r'minutáž:\s+([\d\–\-]+)\s+min', text)
    if match:
        yield from map(int, re.split(r'\D+', match.group(1)))
    else:
        for match in re.finditer(r'\b(\d+)\s+min\b', text):
            yield int(match.group(1))


def parse_kvifftv_url(html_tree):
    try:
        return html_tree.cssselect('[href*="kviff.tv/katalog"]')[0].get('href')
    except IndexError:
        return None
