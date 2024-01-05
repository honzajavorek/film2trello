COLORS = {
    "20m": "blue",
    "30m": "sky",
    "45m": "green",
    "1h": "lime",
    "1.5h": "yellow",
    "2h": "orange",
    "2.5h": "red",
    "3+h": "purple",
}

KVIFFTV_LABEL = dict(name="KVIFF.TV", color="black")


def get_board_url(board_id: str) -> str:
    return f"https://trello.com/b/{board_id}"


# def find_card_id(cards: list[dict], title: str, url: str) -> str | None:
#     for card in cards:
#         if title in card["name"] or url in card["desc"]:
#             return card["id"]


# def get_inbox_id(lists: list[dict]) -> str:
#     return lists[0]["id"]


# def get_archive_id(lists):
#     return lists[-1]["id"]


# def prepare_card_data(list_id, film):
#     return dict(
#         name=film["title"],
#         desc=film["url"],
#         idList=list_id,
#         pos="top",
#     )


# def prepare_updated_card_data(list_id):
#     return dict(
#         pos="top",
#         idList=list_id,
#     )


# def not_in_members(username, members):
#     return username not in [member["username"] for member in members]


# def prepare_duration_labels(durations):
#     for duration in durations:
#         name = get_duration_bracket(duration)
#         yield dict(name=name, color=COLORS[name])


# def get_duration_bracket(duration):
#     duration_cca = math.floor(duration / 10.0) * 10
#     if duration <= 20:
#         return "20m"
#     elif duration <= 30:
#         return "30m"
#     elif duration <= 45:
#         return "45m"
#     if duration <= 60:
#         return "1h"
#     if duration_cca <= 90:
#         return "1.5h"
#     if duration_cca <= 120:
#         return "2h"
#     if duration_cca <= 150:
#         return "2.5h"
#     else:
#         return "3+h"


# def get_missing_labels(existing_labels, labels):
#     names = {label["name"] for label in existing_labels}
#     return [label for label in labels if label["name"] not in names]


# def get_missing_attached_urls(existing_attachments, urls):
#     def normalize_url(url):
#         try:
#             return csfd.normalize_url(url)
#         except csfd.InvalidURLError:
#             return url

#     existing_urls = {
#         normalize_url(attach["name"])
#         for attach in existing_attachments
#         if attach["name"] == attach["url"]
#     }
#     return [url for url in urls if normalize_url(url) not in existing_urls]


# def has_poster(attachments):
#     for attachment in attachments:
#         if len(attachment["previews"]):
#             return True
#     return False
