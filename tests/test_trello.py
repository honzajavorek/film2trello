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


def test_prepare_labels():
    assert list(trello.prepare_labels([20, 55, 130])) == [
        dict(name='20m', color='blue'),
        dict(name='1h', color='lime'),
        dict(name='2.5h', color='red'),
    ]


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
