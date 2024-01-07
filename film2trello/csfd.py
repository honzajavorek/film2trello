import re
from typing import Generator

from lxml import html


TITLE_YEAR_RE = re.compile(r"\((\d{4})\)\s*$")

PARENT_URL_RE = re.compile(
    r"""
        (?P<prefix>.+/film)
        (?P<parent>/\d+(-[^/]+)?)
        (?P<child>/[^/]+)
        (?P<suffix>/prehled/?)
    """,
    re.VERBOSE,
)

KVIFF_URL_RE = re.compile(r"https?://(www\.)?kviff\.tv/katalog/[^\s\"']+")

CSFD_URL_RE = re.compile(r"https?://(www\.)?csfd\.cz/film/[^\s\"']+")


def get_kvifftv_url(text: str) -> str | None:
    if match := KVIFF_URL_RE.search(text):
        return match.group(0)
    return None


def get_csfd_url(text: str) -> str | None:
    if match := CSFD_URL_RE.search(text):
        return match.group(0)
    return None


def parse_title(csfd_html: html.HtmlElement) -> str:
    title_text = csfd_html.cssselect("title")[0].text_content().strip()
    main_title_text = title_text.split("|")[0].strip()

    if match := TITLE_YEAR_RE.search(main_title_text):
        year = int(match.group(1))
    else:
        raise ValueError(f"Could not parse year from title: {title_text}")
    title = TITLE_YEAR_RE.sub("", main_title_text).strip()

    try:
        first_lang = csfd_html.cssselect(".film-names li")[0]
    except IndexError:
        return f"{title} ({year})"
    else:
        first_lang_text = re.sub(r"\s*\(více\)", "", first_lang.text_content().strip())

        if title == first_lang_text:
            return f"{title} ({year})"
        return f"{title} / {first_lang_text} ({year})"


def parse_poster_url(csfd_html: html.HtmlElement) -> str | None:
    srcset = csfd_html.cssselect(".film-posters img")[0].get("srcset")
    if not srcset:
        return None

    srcset_list = re.split(r"\s+", srcset)
    urls = [f"https:{url}" for url in srcset_list[::2]]
    zoom = [int(re.sub(r"\D", "", z)) for z in srcset_list[1::2]]

    srcset_parsed = dict(zip(zoom, urls))
    return srcset_parsed[max(srcset_parsed.keys())]


def parse_durations(csfd_html: html.HtmlElement) -> Generator[int, None, None]:
    text = csfd_html.cssselect(".origin")[0].text_content().lower()
    if match := re.search(r"minutáž:\s+([\d\–\-]+)\s+min", text):
        yield from map(int, re.split(r"\D+", match.group(1)))
    else:
        for match in re.finditer(r"\b(\d+)\s+min\b", text):
            yield int(match.group(1))


def parse_kvifftv_url(csfd_html: html.HtmlElement) -> str | None:
    try:
        return csfd_html.cssselect('[href*="kviff.tv/katalog"]')[0].get("href")
    except IndexError:
        return None


def parse_target_url(csfd_html: html.HtmlElement) -> str:
    try:
        base_url = csfd_html.cssselect("link[rel='canonical']")[0].get("href")
    except IndexError:
        base_url = csfd_html.cssselect("meta[property='og:url']")[0].get("content")
    csfd_html.make_links_absolute(base_url)

    try:
        film_type = (
            csfd_html.cssselect(".film-header-name .type")[0].text_content().strip()
        )
    except IndexError:
        film_type = None

    if film_type == "(epizoda)":
        season_url = (
            csfd_html.cssselect(".film-header h2 a:nth-child(2)")[0]
            .get("href")
            .rstrip("/")
        )
        return f"{season_url}/prehled/"

    if film_type == "(seriál)":
        episodes_list_heading = csfd_html.cssselect(".main-movie-profile h3")[0]
        if episodes_list_heading.text_content().strip().startswith("Série("):
            first_season_url = (
                csfd_html.cssselect(".film-episodes-list a")[0].get("href").rstrip("/")
            )
            return f"{first_season_url}/prehled/"

    overview_url = csfd_html.cssselect(".main-movie-profile .tabs a")[0].get("href")
    return overview_url


def get_parent_url(csfd_url: str) -> str:
    if match := PARENT_URL_RE.search(csfd_url):
        return (
            match.group("prefix")
            + match.group("parent")
            + match.group("suffix").rstrip("/")
            + "/"
        )
    return csfd_url
