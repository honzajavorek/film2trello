from datetime import date, timedelta
import time
import sys
from pathlib import Path

sys.path.insert(1, str(Path(__file__).parent.parent.absolute()))
from film2trello import (TRELLO_TOKEN, TRELLO_KEY, TRELLO_BOARD,
                         trello, update_labels, update_attachments,
                         get_film, csfd)


api = trello.create_session(TRELLO_TOKEN, TRELLO_KEY)
lists = api.get(f'/boards/{TRELLO_BOARD}/lists')

inbox_list_id = trello.get_inbox_id(lists)
archive_list_id = trello.get_archive_id(lists)

years_ago = date.today() - timedelta(days=365 * 2)
years_old_cards = api.get(f'/lists/{inbox_list_id}/cards?before={years_ago}')

print(f"Found {len(years_old_cards)} years old cards", file=sys.stderr, flush=True)
for card in years_old_cards:
    print(card['name'], file=sys.stderr, flush=True)
    api.put(f"/cards/{card['id']}/", data=dict(idList=archive_list_id))

cards = api.get(f'/lists/{inbox_list_id}/cards')
column = [{'card': card} for card in cards]

for item in column:
    card = item['card']
    print(card['name'], file=sys.stderr, flush=True)
    try:
        film_url = csfd.normalize_url(card['desc'])
        print(film_url, file=sys.stderr, flush=True)
    except csfd.InvalidURLError as e:
        print("Card description doesn't contain CSFD.cz URL", file=sys.stderr, flush=True)
        item['film'] = None
    else:
        film = get_film(film_url)
        update_labels(api, card['id'], film)
        update_attachments(api, card['id'], film)
        item['film'] = film

def sort_key(item):
    film, card = item['film'], item['card']

    min_duration = min(film['durations']) if (film and film['durations']) else 1000
    labels = [label['name'].lower() for label in card['labels'] or []]
    is_available = 0 if (('kviff.tv' in labels) or ('stash' in labels)) else 1

    return (min_duration, is_available, card['name'])

for pos, item in enumerate(sorted(column, key=sort_key), start=1):
    print(f'#{pos}', item['card']['name'], file=sys.stderr, flush=True)
    api.put(f"/cards/{item['card']['id']}/", data=dict(pos=pos))
    time.sleep(0.5)
