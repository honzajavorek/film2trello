"""Anubis's proof-of-work challenge, kept out of the rest of the codebase.

CSFD.cz, KVIFF.TV, and the other film sites this scrapes wall plain HTTP
clients (even ones rotating browser-like headers, see http.py's now-retired
antibot retry loop) behind Anubis's JS proof-of-work challenge. Camoufox - a
real, fingerprint-patched Firefox build - clears it, but its pages need to
sit through the challenge's client-side hash loop before the real page is
there to read. Callers get a browser that already does that, so they never
see a challenge page.
"""

import logging
from typing import Any, TypedDict

from camoufox import DefaultAddons
from camoufox.async_api import AsyncCamoufox
from lxml import html
from playwright.async_api import Page as PlaywrightPage


logger = logging.getLogger("film2trello.anubis")

# Camoufox bundles uBlock Origin by default. It blocks Anubis's own challenge
# script - served from a path generic filter lists flag as tracking, e.g.
# /.within.website/x/cmd/anubis/... - which strands the browser on the
# challenge page instead of ever solving it.
LAUNCH_OPTIONS: dict[str, Any] = {"exclude_addons": [DefaultAddons.UBO]}

ANUBIS_CHALLENGE_SELECTOR = "script#anubis_challenge"

# The title Anubis shows when it denies a request outright, without
# offering a challenge to solve. Unlike the challenge, this isn't something
# to wait out - the only known recovery is a fresh browser session.
DENIED_TITLE = "Oh noes!"

FETCH_ATTEMPTS = 3


class Page(TypedDict):
    request_url: str
    url: str
    html: html.HtmlElement


class DeniedError(RuntimeError):
    pass


def is_antibot_page(page_html: html.HtmlElement) -> bool:
    return bool(page_html.cssselect(ANUBIS_CHALLENGE_SELECTOR))


async def _pass_challenge(page: PlaywrightPage, timeout: float = 60000) -> None:
    """Wait out the challenge page, if one was shown; raise DeniedError if
    Anubis denied the request outright instead.

    The challenge computes a hash puzzle client-side, then reloads into the
    real page once solved. Waiting for that reload's "domcontentloaded" -
    not "load", which can hang on pages carrying ads/trackers that never
    finish loading, nor "networkidle", which these sites' pages never
    reach - gets the real page without reading it mid-reload.
    """
    if await page.locator(ANUBIS_CHALLENGE_SELECTOR).count():
        await page.wait_for_function(
            "(sel) => !document.querySelector(sel)",
            arg=ANUBIS_CHALLENGE_SELECTOR,
            timeout=timeout,
        )
        await page.wait_for_load_state("domcontentloaded", timeout=timeout)
    if await page.title() == DENIED_TITLE:
        body = await page.inner_text("body")
        raise DeniedError(body.strip().splitlines()[0] if body.strip() else "denied")


async def get_html(url: str, **kwargs: Any) -> Page:
    """Fetch a page's HTML via Camoufox.

    Retries with a fresh browser session (and so a fresh fingerprint) if
    Anubis denies the request outright rather than offering a challenge to
    solve, since that isn't recoverable within the same session.
    """
    error: DeniedError | None = None
    for _ in range(FETCH_ATTEMPTS):
        async with AsyncCamoufox(headless=True, **LAUNCH_OPTIONS) as browser:
            page = await browser.new_page()
            await page.goto(url, **kwargs)
            try:
                await _pass_challenge(page)
                page_url = page.url
                page_html = html.fromstring(await page.content())
                page_html.make_links_absolute(page_url)
                return Page(request_url=url, url=page_url, html=page_html)
            except DeniedError as exc:
                logger.warning("Denied, retrying with a fresh session: %s", exc)
                error = exc
    raise error
