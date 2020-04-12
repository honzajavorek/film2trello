import sys
from pathlib import Path

sys.path.insert(1, str(Path(__file__).parent.parent.absolute()))
from film2trello import (TRELLO_TOKEN, TRELLO_KEY, TRELLO_BOARD,
                         trello, update_labels, update_attachments,
                         get_film, get_aerovod_film, csfd)


api = trello.create_session(TRELLO_TOKEN, TRELLO_KEY)
lists = api.get(f'/boards/{TRELLO_BOARD}/lists')
inbox_list_id = trello.get_inbox_id(lists)
cards = api.get(f'/lists/{inbox_list_id}/cards')

for card in cards:
    print(card['name'], file=sys.stderr, flush=True)
    try:
        film_url = csfd.normalize_url(card['desc'])
        print(film_url, file=sys.stderr, flush=True)
    except csfd.InvalidURLError as e:
        print("Card description doesn't contain CSFD.cz URL", file=sys.stderr, flush=True)
    else:
        film = get_film(film_url)
        aerovod_film = get_aerovod_film(film_url)
        update_labels(api, card['id'], film, aerovod_film=aerovod_film)
        update_attachments(api, card['id'], film, aerovod_film=aerovod_film)
