"""
Adaptation of get_revision_history.py that writes all revisions of
a given article
"""


import requests
from xml.sax.saxutils import escape
import sys

xml_template_head = """
<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.10/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.mediawiki.org/xml/export-0.10/ http://www.mediawiki.org/xml/export-0.10.xsd" version="0.10" xml:lang="es">
  <siteinfo>
    <sitename>Wikipedia</sitename>
    <dbname>eswiki</dbname>
    <base>https://es.wikipedia.org/wiki/Wikipedia:Portada</base>
    <generator>MediaWiki 1.42.0-wmf.19</generator>
    <case>first-letter</case>
    <namespaces>
      <namespace key="-2" case="first-letter">doesn't matter...</namespace>
    </namespaces>
  </siteinfo>
  <page>
    <title>%s</title>
    <ns>0</ns>
    <id>123456</id>
"""

xml_template_tail = """
  </page>
</mediawiki>
"""

xml_template_revision = """
    <revision>
      <id>%s</id>
      <timestamp>%s</timestamp>
      <contributor>
        <username>%s</username>
        <id>%s</id>
      </contributor>
      <comment>doesn't matter...»</comment>
      <model>wikitext</model>
      <format>text/x-wiki</format>
      <text bytes="%s" xml:space="preserve">%s</text>
      <sha1>doesn't matter...</sha1>
    </revision>
"""


def write_revision(f, rev_id, timestamp, username, user_id, text):
    f.write(xml_template_revision % (rev_id, timestamp, username, user_id, len(text), text))


def download_revisions(lang, article_title):
    revisions_written = 0
    with open(f'{article_title}_{lang}.xml', 'w') as f:
        f.write(xml_template_head % (article_title))

        base_url = f"https://{lang}.wikipedia.org/w/api.php"

        # Initial request to get revisions
        params = {
            'action': 'query',
            'format': 'json',
            'prop': 'revisions',
            'titles': article_title,
            'rvprop': 'ids|timestamp|user|userid|content',
            'rvlimit': 1000,
            'offset': revisions_written,
            'rvdir': 'newer' # Quite contradictory, but older to newer order
        }

        while True:
            response = requests.get(base_url, params=params)
            data = response.json()

            # Process the response to get revision IDs
            page = next(iter(data['query']['pages'].values()))
            revisions = page["revisions"]

            revisions_data = []
            for revision in revisions:
                if all(key in revision for key in ['revid', 'timestamp', 'user', 'userid', '*']): # Some revisions lack some fields somehow
                    revisions_data.append({
                        'revid': revision['revid'],
                        'timestamp': revision['timestamp'],
                        'user': escape(revision['user']),
                        'userid': revision['userid'],
                        'content': escape(revision['*'])
                    })

            revisions_written += len(revisions_data)

            for revision in revisions_data:
                write_revision(f, revision['revid'], revision['timestamp'], revision['user'], revision['userid'], revision['content'])

            print(f"\rWritten {revisions_written} revisions...", end='')
            if 'continue' in data:
                params['rvcontinue'] = data['continue']['rvcontinue']
            else:
                f.write(xml_template_tail)
                print("Finished!")
                break


if __name__ == "__main__":
    # Wikipedia page title we want to extract
    # (you can obtain them manually or via e.g Wikidata SPARQL queries)
    title = "Ladilla_Rusa"

    # Language code for the article
    lang = 'en'
    download_revisions(lang, title)
