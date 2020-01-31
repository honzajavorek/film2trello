from functools import partial

import requests


def create_session(token, key):
    def prefix_request(f, method, url, *args, **kwargs):
        url = 'https://trello.com/1/' + url.lstrip('/')
        response = f(method, url, *args, **kwargs)
        response.raise_for_status()
        return response.json()

    session = requests.Session()
    session.request = partial(prefix_request, session.request)
    session.params = dict(token=token, key=key)
    return session


def card_exists(cards, film):
    for card in cards:
        if film['title'] in card['name'] or film['url'] in card['desc']:
            return card['id']


def get_inbox_id(lists):
    return lists[0]['id']


def prepare_card_data(list_id, film):
    return dict(
        name=film['title'],
        idList=list_id,
        desc=film['url'],
    )


def not_in_members(username, members):
    return username not in [member['username'] for member in members]
