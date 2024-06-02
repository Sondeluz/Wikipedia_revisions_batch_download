"""
Script to download the latest revision's parsed text of a list of
Wikipedia articles, without needing to parse the Wikitext or perform
any cleaning (the extracts API does it for us).

It will batch up to 20 articles per request, always respecting the API's
limits.
"""

import requests
from typing import List

N_ARTICLES_PER_REQUEST = 20  # extracts API's limit
USER_AGENT = "My Wikipedia API project (change me!)"


def get_latest_revisions(lang: str, titles: List[str], only_intro=False):
    """
    Returns a dict of article title -> text given the provided
    list of titles for the language of choice
    """
    base_url = f"https://{lang}.wikipedia.org/w/api.php"

    headers = {
        "User-Agent": USER_AGENT
    }

    # Wikipedia already has a extract API functionality for returning raw text (not wikitext formatted),
    # so we don't need to use mwparserfromhell for wikitext or beautifulsoup for html
    # https://www.mediawiki.org/wiki/Extension:TextExtracts#API
    params = {
        "prop": "extracts",
        "explaintext": "",
        "titles": "|".join(titles),
        "exintro": only_intro,  # Return only content before the first section
        "format": "json",
        "action": "query",
        "exlimit": N_ARTICLES_PER_REQUEST,
    }

    response = requests.get(base_url, headers=headers, params=params)
    response_json = response.json()

    # Find the page_id
    article_texts = dict()
    for page_id, inner_dict in response_json["query"]["pages"].items():
        # The API normalizes titles (removes '_' characters, etc.), so we have
        # to look up the original article title
        if ("query" in response_json and "normalized" in response_json["query"]):
            for normalized_dict in response_json["query"]["normalized"]:
                if inner_dict["title"] in normalized_dict["to"]:
                    original_title = normalized_dict["from"]
                    if (
                        "extract" in inner_dict
                    ):  # else: it's an empty article (redirect...)
                        article_texts[original_title] = inner_dict["extract"]
                    break
        else:
            print(f"Failed request for {titles}, response:", response_json)

    return article_texts


if __name__ == "__main__":
    # List of Wikipedia page titles we want to extract
    # (you can obtain them manually or via e.g Wikidata SPARQL queries)
    titles = ["Ladilla_Rusa", "Knower_(duo)"]

    # Language code for the article
    lang = "en"

    # Whether to only retrieve the article's introduction or the whole text
    only_intro = True

    articles = get_latest_revisions(lang, titles, only_intro)
    print(articles["Michael_Schumacher"])
