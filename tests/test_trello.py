import responses
import requests
import pytest

from film2trello import trello


@responses.activate
def test_create_session():
    api = trello.create_session(key='abc', token='123')
    api.headers = {'User-Agent': 'hello'}

    responses.add(responses.GET,
                  'https://trello.com/1/list/?key=abc&token=123&boo=1',
                  match_querystring=True, json=[{'name': 'foo'}],
                  headers={'User-Agent': 'hello'}, status=200)

    body = api.get('/list/', params=dict(boo=1))

    assert body == [{'name': 'foo'}]
    assert len(responses.calls) == 1


@responses.activate
def test_create_session_raises():
    api = trello.create_session(key='abc', token='123')

    responses.add(responses.GET,
                  'https://trello.com/1/list/?key=abc&token=123',
                  match_querystring=True, json={'error': True},
                  status=400)

    with pytest.raises(requests.RequestException):
        api.get('/list/')


def test_card_exists_matches_title():
    assert trello.card_exists([
        dict(id='1', name='Foo Bar (2020)', desc=''),
        dict(id='2', name='Poslední skaut / The Last Boy Scout (1991)', desc=''),
    ], dict(
        title='Poslední skaut / The Last Boy Scout (1991)',
        url='https://www.csfd.cz/film/8283-posledni-skaut/',
    )) == '2'


def test_card_exists_matches_url():
    assert trello.card_exists([
        dict(id='1', name='', desc='https://www.csfd.cz/film/8283-posledni-skaut/'),
        dict(id='2', name='', desc='https://example.com'),
    ], dict(
        title='Poslední skaut / The Last Boy Scout (1991)',
        url='https://www.csfd.cz/film/8283-posledni-skaut/',
    )) == '1'


def test_card_exists_doesnt_match():
    assert trello.card_exists([
        dict(id='1', name='', desc='https://example.com'),
        dict(id='2', name='', desc='https://example.com'),
    ], dict(
        title='Poslední skaut / The Last Boy Scout (1991)',
        url='https://www.csfd.cz/film/8283-posledni-skaut/',
    )) == None


def test_get_inbox_list_id():
    assert trello.get_inbox_id([
        dict(id='1'),
        dict(id='2'),
        dict(id='3'),
        dict(id='4'),
    ]) == '1'


def test_prepare_card_data():
    assert trello.prepare_card_data('1', dict(
        title='Poslední skaut / The Last Boy Scout (1991)',
        url='https://www.csfd.cz/film/8283-posledni-skaut/',
    )) == dict(
        name='Poslední skaut / The Last Boy Scout (1991)',
        idList='1',
        desc='https://www.csfd.cz/film/8283-posledni-skaut/',
        pos='top',
    )


def test_prepare_updated_card_data():
    assert trello.prepare_updated_card_data() == dict(
        pos='top',
    )


def test_not_in_members_when_it_is():
    assert trello.not_in_members('honzajavorek', [
        dict(username='vladimir'),
        dict(username='honzajavorek'),
    ]) == False


def test_not_in_members_when_it_isnt():
    assert trello.not_in_members('honzajavorek', [
        dict(username='vladimir'),
        dict(username='kvetoslava'),
    ]) == True


def test_not_in_members_when_members_empty():
    assert trello.not_in_members('honzajavorek', []) == True


def test_prepare_duration_labels():
    assert list(trello.prepare_duration_labels([20, 55, 130])) == [
        dict(name='20m', color='blue'),
        dict(name='1h', color='lime'),
        dict(name='2.5h', color='red'),
    ]


def test_get_missing_labels():
    existing_labels = [
        {'id': '...', 'idBoard': '...', 'name': '2.5h', 'color': 'red'},
        {'id': '...', 'idBoard': '...', 'name': '3+h', 'color': 'purple'},
    ]
    labels = [
        dict(name='Aerovod', color='black'),
        dict(name='3+h', color='purple'),
        dict(name='2.5h', color='red'),
    ]

    assert trello.get_missing_labels(existing_labels, labels) == [
        dict(name='Aerovod', color='black'),
    ]


def test_get_missing_attached_urls():
    existing_attachments = [
        {
            'id': '...',
            'date': '2020-04-06T11:20:15.762Z',
            'name': 'https://www.csfd.cz/film/642698-slunovrat/prehled/',
            'url': 'https://www.csfd.cz/film/642698-slunovrat/prehled/',
        },
        {
            'id': '...',
            'date': '2020-04-06T11:20:31.176Z',
            'name': 'poster.jpg',
            'url': '...',
        },
    ]
    urls = [
        'https://www.csfd.cz/film/642698/',
        'https://aerovod.cz/katalog/slunovrat',
    ]

    assert trello.get_missing_attached_urls(existing_attachments, urls) == [
        'https://aerovod.cz/katalog/slunovrat',
    ]


def test_has_poster():
    existing_attachments = [
        {
            'id': '...',
            'bytes': None,
            'name': 'https://www.csfd.cz/film/642698-slunovrat/prehled/',
            'previews': [],
            'url': 'https://www.csfd.cz/film/642698-slunovrat/prehled/',
        },
        {
            'id': '...',
            'bytes': 34286,
            'name': 'poster.jpg',
            'previews': [{}, {}, {}],
            'url': '...',
        },
    ]
    urls = [
        'https://www.csfd.cz/film/642698/',
        'https://aerovod.cz/katalog/slunovrat',
    ]

    assert trello.has_poster(existing_attachments) == True
    assert trello.has_poster(existing_attachments[:1]) == False
    assert trello.has_poster(existing_attachments[1:]) == True


@pytest.mark.parametrize('duration,expected', [
    (15, '20m'),
    (20, '20m'),
    (25, '30m'),
    (30, '30m'),
    (35, '45m'),
    (40, '45m'),
    (45, '45m'),
    (50, '1h'),
    (55, '1h'),
    (60, '1h'),
    (65, '1.5h'),
    (80, '1.5h'),
    (90, '1.5h'),
    (100, '2h'),
    (120, '2h'),
    (130, '2.5h'),
    (150, '2.5h'),
    (154, '2.5h'),
    (200, '3+h'),
])
def test_get_duration_bracket(duration, expected):
    assert trello.get_duration_bracket(duration) == expected
