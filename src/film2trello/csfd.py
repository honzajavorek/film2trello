import asyncio
import logging
import re
import time
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from typing import Any, TypedDict

from camoufox import DefaultAddons
from camoufox.async_api import AsyncCamoufox
from lxml import html
from playwright.async_api import Browser as PlaywrightBrowser, Page as PlaywrightPage


logger = logging.getLogger("film2trello.csfd")


TITLE_YEAR_RE = re.compile(r"\((\d{4})\)\s*$")

TITLE_SPECIAL_NAME_RE = re.compile(r"\s+\([^\)]+\snázev\)$")

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

TV_SHOW_SUFFIXES = ("seriál", "série", "epizoda")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_alternate_title(text: str) -> str:
    text = normalize_whitespace(text)
    text = re.sub(r"\s+\((více|méně)\)$", "", text)
    return re.sub(r"\s+(více|méně)$", "", text).strip()


def get_base_url(csfd_html: html.HtmlElement) -> str:
    for selector, attribute in [
        ("link[rel='canonical']", "href"),
        ("meta[property='og:url']", "content"),
    ]:
        if (elements := csfd_html.cssselect(selector)) and (
            url := elements[0].get(attribute)
        ):
            return url
    raise ValueError("Could not find a base URL on the page")


def ensure_overview_url(url: str) -> str:
    normalized = url.rstrip("/")
    if normalized.endswith("/prehled"):
        return f"{normalized}/"
    return f"{normalized}/prehled/"


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
        first_lang_text = clean_alternate_title(first_lang.text_content())
        if title == first_lang_text or TITLE_SPECIAL_NAME_RE.search(first_lang_text):
            return f"{title} ({year})"
        return f"{title} / {first_lang_text} ({year})"


def parse_poster_url(csfd_html: html.HtmlElement) -> str | None:
    if poster_images := csfd_html.cssselect(".film-posters img"):
        if srcset := poster_images[0].get("srcset"):
            srcset_list = re.split(r"\s+", srcset)
            urls = [f"https:{url}" for url in srcset_list[::2]]
            zoom = [int(re.sub(r"\D", "", z)) for z in srcset_list[1::2]]
            srcset_parsed = dict(zip(zoom, urls))
            return srcset_parsed[max(srcset_parsed.keys())]
        return None
    return None


def parse_durations(csfd_html: html.HtmlElement) -> Generator[int]:
    text = normalize_whitespace(
        csfd_html.cssselect(".origin")[0].text_content().lower()
    )
    if match := re.search(r"minutáž:\s+([\d\–\-]+)\s+min", text):
        yield from map(int, re.split(r"\D+", match.group(1)))
        return

    yield from dict.fromkeys(
        int(match.group(1)) for match in re.finditer(r"\b(\d+)\s+min\b", text)
    )


def parse_kvifftv_url(csfd_html: html.HtmlElement) -> str | None:
    try:
        return csfd_html.cssselect('[href*="kviff.tv/katalog"]')[0].get("href")
    except IndexError:
        return None


def parse_netflix_url(csfd_html: html.HtmlElement) -> str | None:
    try:
        return csfd_html.cssselect('[href*="netflix.com/title/"]')[0].get("href")
    except IndexError:
        return None


def parse_csfd_url(kvifftv_html: html.HtmlElement) -> str | None:
    try:
        return kvifftv_html.cssselect('[href*="csfd.cz/film/"]')[0].get("href")
    except IndexError:
        return None


def parse_target_url(csfd_html: html.HtmlElement) -> str:
    base_url = get_base_url(csfd_html)
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
        return ensure_overview_url(season_url)

    if film_type == "(seriál)":
        episode_links = [
            link.get("href")
            for link in csfd_html.cssselect(".film-episodes-list a")
            if link.get("href")
        ]
        for episode_link in episode_links:
            if re.search(r"/\d+-serie-\d+(/|$)", episode_link):
                return ensure_overview_url(episode_link)

    if tabs := csfd_html.cssselect(".main-movie-profile .tabs a"):
        overview_url = tabs[0].get("href")
        if overview_url.startswith("http"):
            return ensure_overview_url(overview_url)
    return ensure_overview_url(base_url)


def get_parent_url(csfd_url: str) -> str:
    if match := PARENT_URL_RE.search(csfd_url):
        return (
            match.group("prefix")
            + match.group("parent")
            + match.group("suffix").rstrip("/")
            + "/"
        )
    return csfd_url


def parse_is_tvshow(csfd_html: html.HtmlElement) -> bool:
    if title_suffixes := csfd_html.cssselect(".film-header-name .type"):
        suffix = title_suffixes[0].text_content().strip().lower()
        for tv_show_suffix in TV_SHOW_SUFFIXES:
            if tv_show_suffix in suffix:
                return True
    return False


# Camoufox bundles uBlock Origin by default. It blocks Anubis's own challenge
# script - served from a path generic filter lists flag as tracking, e.g.
# /.within.website/x/cmd/anubis/... - which strands the browser on the
# challenge page instead of ever solving it.
LAUNCH_OPTIONS: dict[str, Any] = {"exclude_addons": [DefaultAddons.UBO]}

CHALLENGE_SELECTOR = "script#anubis_challenge"

# The title Anubis shows when it denies a request outright, without
# offering a challenge to solve. Unlike the challenge, this isn't something
# to wait out - the only known recovery is a fresh browser session.
DENIED_TITLE = "Oh noes!"

FETCH_ATTEMPTS = 3

# Seconds. Launching the browser has no timeout of its own, so without one a
# stuck launch (e.g. a starved machine) would hang the whole run silently.
LAUNCH_TIMEOUT = 60


class Page(TypedDict):
    request_url: str
    url: str
    html: html.HtmlElement


class DeniedError(RuntimeError):
    pass


def is_antibot_page(page_html: html.HtmlElement) -> bool:
    return bool(page_html.cssselect(CHALLENGE_SELECTOR))


async def _pass_challenge(page: PlaywrightPage, timeout: float = 60000) -> None:
    """Wait out the challenge page, if one was shown; raise DeniedError if
    Anubis denied the request outright instead.

    The challenge computes a hash puzzle client-side, then reloads into the
    real page once solved. Waiting for that reload's "domcontentloaded" -
    not "load", which can hang on pages carrying ads/trackers that never
    finish loading, nor "networkidle", which these sites' pages never
    reach - gets the real page without reading it mid-reload.
    """
    if await page.locator(CHALLENGE_SELECTOR).count():
        logger.info("Anubis challenge detected, solving it")
        started = time.monotonic()
        await page.wait_for_function(
            "(sel) => !document.querySelector(sel)",
            arg=CHALLENGE_SELECTOR,
            timeout=timeout,
        )
        await page.wait_for_load_state("domcontentloaded", timeout=timeout)
        logger.info("Anubis challenge solved in %.1fs", time.monotonic() - started)
    if await page.title() == DENIED_TITLE:
        body = await page.inner_text("body")
        raise DeniedError(body.strip().splitlines()[0] if body.strip() else "denied")


class BrowserSession:
    """A Camoufox browser kept open across multiple fetches.

    Anubis sets an auth cookie once a challenge is solved, so reusing one
    browser (and its cookie jar) across many pages skips the puzzle after
    the first solve instead of paying it on every single fetch.
    """

    def __init__(self) -> None:
        self._camoufox: AsyncCamoufox | None = None
        self._browser: PlaywrightBrowser | None = None

    async def open(self) -> None:
        logger.info("Launching Camoufox browser")
        started = time.monotonic()
        self._camoufox = AsyncCamoufox(headless=True, **LAUNCH_OPTIONS)
        async with asyncio.timeout(LAUNCH_TIMEOUT):
            self._browser = await self._camoufox.__aenter__()
        logger.info("Browser launched in %.1fs", time.monotonic() - started)

    async def close(self) -> None:
        if self._camoufox is not None:
            await self._camoufox.__aexit__(None, None, None)
        self._camoufox = None
        self._browser = None

    async def get_html(self, url: str, **kwargs: Any) -> Page:
        error: DeniedError | None = None
        kwargs.setdefault("wait_until", "domcontentloaded")
        for attempt in range(1, FETCH_ATTEMPTS + 1):
            assert self._browser is not None, "call open() first"
            logger.info("Loading %s (attempt %d/%d)", url, attempt, FETCH_ATTEMPTS)
            started = time.monotonic()
            page = await self._browser.new_page()
            try:
                await page.goto(url, **kwargs)
                await _pass_challenge(page)
                page_url = page.url
                page_html = html.fromstring(await page.content())
                page_html.make_links_absolute(page_url)
                logger.info("Loaded %s in %.1fs", page_url, time.monotonic() - started)
                return Page(request_url=url, url=page_url, html=page_html)
            except DeniedError as exc:
                error = exc
            finally:
                await page.close()
            # Not recoverable within the same session - restart with a
            # fresh browser, and so a fresh fingerprint and cookie jar.
            logger.warning("Denied, restarting with a fresh session: %s", error)
            await self.close()
            await self.open()
        raise error


@asynccontextmanager
async def browser_session() -> AsyncGenerator[BrowserSession]:
    session = BrowserSession()
    await session.open()
    try:
        yield session
    finally:
        await session.close()
