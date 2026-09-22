from pathlib import Path

import pytest
from lxml import html

from film2trello import anubis


@pytest.mark.parametrize(
    "fixture_name",
    ["csfd_antibot_cs.html", "csfd_antibot_en.html"],
)
def test_is_antibot_page_detects_anubis_challenge(fixture_name):
    path = Path(__file__).parent / fixture_name
    page_html = html.fromstring(path.read_text())

    assert anubis.is_antibot_page(page_html) is True


def test_is_antibot_page_ignores_regular_page():
    path = Path(__file__).parent / "csfd.html"
    page_html = html.fromstring(path.read_text())

    assert anubis.is_antibot_page(page_html) is False
