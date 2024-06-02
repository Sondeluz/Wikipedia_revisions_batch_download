"""
Script to download an entire article's revision history with an additional
parsing step using mwparserfromhell and some extra text cleaning and processing.

We need to respect the Wikipedia's revision API limits and parse and clean thousands
of revisions, so this may take up to half an hour for the biggest articles (e.g Donald
Trump in the English Wikipedia).

Multiprocessing is used extensively, and the parsing and cleaning step is performed
after having downloaded all revisions

The result will be a json file containing a list of dictionaries with "timestamp"
and "content" keys, with its entries ordered from older to newer revisions

Note that if you only want the latest revision of an article, 'get_latest_revision_text.py'
does this in a much better way, as the 'extracts' API does the text processing for us
"""

import requests
import json
import re
import ijson
import itertools
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor

import mwparserfromhell
from nltk.tokenize import WhitespaceTokenizer


# How many text cleaning workers to spawn (up to your CPU's #threads)
N_WORKERS = 4
USER_AGENT = "My Wikipedia API project (change me!)"


def clean_doc(doc):
    # Remove sections from the article that may cause confusions
    def remove_everything_after(doc, substr):
        substr_idx = doc.find(substr)
        if substr_idx != -1:
            return 1, doc[:substr_idx]

        return 0, doc

    # These section names are standard, so it should remove them
    # everywhere except in small or unpopular articles that may
    # not be well taken care of
    removed_notes, doc = remove_everything_after(doc, "Notes\n")
    removed_links, doc = remove_everything_after(doc, "External links\n")
    removed_refs, doc = remove_everything_after(doc, "References\n")

    # We want to reconstruct the document afterwards, so we use the simplest
    # tokenizer possible
    tokens = WhitespaceTokenizer().tokenize(doc)

    # Remove numbers, but keep everything else
    doc = " ".join([token for token in tokens if not token.isnumeric()])

    # Also remove any citations that may have gotten through
    citation_regex = r'\[[0-9]+\]'
    doc = re.sub(citation_regex, '', doc)

    return doc


def write_revisions(f, revisions_data):
    for i, revision in enumerate(revisions_data):
        timestamp = revision['timestamp']
        text = revision['content']
        # Convert the API's custom timestamp to a unix one for better portability
        dt_object = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        unix_timestamp = int(dt_object.timestamp())

        revision_entry = {'timestamp': unix_timestamp, 'content': text}

        json.dump(revision_entry, f, ensure_ascii=False, indent=4)
        if i < (len(revisions_data) - 1):
            f.write(",\n")


def get_all_revision_ids(lang, article_title):
    revisions_written = 0
    with open(f'{article_title}_{lang}.json', 'w') as f:
        f.write("[\n")  # JSON head

        base_url = f"https://{lang}.wikipedia.org/w/api.php"

        headers = {
            "User-Agent": USER_AGENT
        }

        params = {
            'action': 'query',
            'format': 'json',
            'prop': 'revisions',
            'titles': article_title,
            # Avoid asking for unnecessary properties
            'rvprop': 'timestamp|content',
            'rvlimit': 1000,
            'offset': revisions_written,
            # Quite contradictory, but older to newer order
            'rvdir': 'newer',
            'rvsection': 0
        }

        while True:
            response = requests.get(base_url, headers=headers, params=params)
            data = response.json()

            # Process the response to get revision IDs
            page = next(iter(data['query']['pages'].values()))
            revisions = page["revisions"]

            revisions_data = []
            for revision in revisions:
                if all(key in revision for key in ['timestamp', '*']):
                    # A very small number of revisions lack contents,
                    # avoid erroring out
                    revisions_data.append({
                        'timestamp': revision['timestamp'],
                        'content': revision['*']
                    })

            revisions_written += len(revisions_data)

            write_revisions(f, revisions_data)

            print(f"\rWritten {revisions_written} revisions...", end='')
            if 'continue' in data:
                params['rvcontinue'] = data['continue']['rvcontinue']
                f.write(",\n")
            else:
                f.write("\n]")  # JSON's tail
                print("Finished!")
                break


def process_chunk(chunk):
    return [(entry["timestamp"], entry["content"]) for entry in sorted(chunk, key=lambda x: x["timestamp"])]


def clean_revision(timestamp_content):
    timestamp, content = timestamp_content
    return timestamp, clean_doc(mwparserfromhell.parse(content).strip_code())


def clean_revisions_in_batches(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        json_parser = ijson.items(file, 'item')
        chunk_size = 100
        i = 1

        clean_revisions = []
        with ProcessPoolExecutor(max_workers=N_WORKERS) as executor:
            for chunk in iter(lambda: list(itertools.islice(json_parser, chunk_size)), []):
                # Process each chunk concurrently
                revisions = process_chunk(chunk)
                clean_results = list(executor.map(clean_revision, revisions))
                clean_revisions.extend(clean_results)
                print(f"\rProcessed {chunk_size * i} revisions", end="")
                i += 1

    return clean_revisions


if __name__ == "__main__":
    # Wikipedia page title we want to extract
    # (you can obtain them manually or via e.g Wikidata SPARQL queries)
    title = "Ladilla_Rusa"

    # Language code for the article
    lang = 'en'
    get_all_revision_ids(lang, title)

    # Parse and clean the downloaded revisions in batches, using multiprocessing.
    # We do this after downloading because parsing Wikitext and then cleaning the
    # text is very costly, so doing it inbetween API requests would be extremely slow.
    #
    # Additionally, we need to be careful when reading the revisions file. Since
    # the article may be extremely big (Donald Trump's entire history is 11GiB),
    # reading it directly will fill the memory. Due to this, we use ijson to
    # iteratively read the JSON file we previously wrote.
    clean_revisions = clean_revisions_in_batches(f"{title}_{lang}.json")
    with open(f"{title}_{lang}_clean.json", "w") as f:
        json.dump(clean_revisions, f, ensure_ascii=False, indent=4)
