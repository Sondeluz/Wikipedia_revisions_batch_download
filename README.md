A set of scripts for:

- Batch download and parsing of the latest revisions for a given list of Wikipedia articles (`get_latest_revision_text.py`)
- Batch download and parsing of the entire revision history of a given Wikipedia article (`get_revision_history.py`)

While these functionalities are available on popular Wikipedia API libraries, these scripts focus on very fast and efficient batch downloading of any given number of articles, while still respecting the API limits. Moreover, `get_revision_history.py` allows downloading the complete revision history of an article without the limitations of the [Special:Export](https://www.mediawiki.org/wiki/Help:Export) API, which will struggle to return the history of very popular articles (e.g for celebrity articles with lots of vandalism and edits, `Special:Export` will behave erratically and skip revisions, while this script doesn't).

The scripts only use native Python libraries, with `get_revision_history.py` additionally depending on `mwparserfromhell` and `NLTK` for cleaning and parsing, and `get_revision_history.py` on `ijson` for iterative JSON reading. They are available as-is with no guarantees of working in the future.

**Important note: Although under the API limits, downloading the entire revision history of popular articles can be quite taxing, so please know what you are doing before using them. I haven't written a public API to prevent abuse of these functionalities.**
