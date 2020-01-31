import pytest

import film2trello


@pytest.mark.parametrize('username,expected', [
    (None, None),
    ('', None),
    ('None', None),
    ('honzajavorek', 'honzajavorek'),
])
def test_parse_username(username, expected):
    assert film2trello.parse_username(username) == expected


def sanitize_exception():
    film2trello.sanitize_exception(f'''
        This is my token: {film2trello.TRELLO_TOKEN}
        And this is my key: {film2trello.TRELLO_KEY}
    ''') == '''
        This is my token: <TRELLO_TOKEN>
        And this is my key: <TRELLO_KEY>
    '''


def test_compress_javascript():
    film2trello.compress_javascript('''
        (function() {
          window.alert('Hello!');
          console.log('Hello!');
        })()
    ''') == "(function() { window.alert('Hello!'); console.log('Hello!'); })()"
