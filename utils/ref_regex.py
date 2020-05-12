import os
import re

from typing import List, Set

# Taken from http://www.noah.org/wiki/RegEx_Python#URL_regex_pattern
URL_REGEX = r'http[s]?://(?:[\~\#a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[\~\#0-9a-fA-F][\~\#0-9a-fA-F]))+'
REVISION_REGEX = r'(?:r|[Rr]ev. |[Rr]evision |[Cc]ommit )[0-9]+'
NUMBER_REGEX = r'\d+'

url_matcher = re.compile(URL_REGEX)
revision_matcher = re.compile(REVISION_REGEX)
number_matcher = re.compile(NUMBER_REGEX)


def extract_urls(text: str, filter_revisions=False) -> List[str]:
    urls = url_matcher.findall(clean_text(text))
    urls = list(
        map(
            # if a URL ends with '.', '\' or '?', then we should remove that character
            lambda url: url[:-1] if url[-1] in ['.', '\\', '?'] else url,
            urls
        )
    )
    if filter_revisions:
        urls = list(
            filter(
                lambda url: not url.startswith("https://svn.apache.org"),
                urls
            )
        )
    return urls


def extract_issues(text: str, project_name: str) -> List[str]:
    """
    Extract all issue IDs from the text. Each issue ID has the form <project_name>-{int_id}.
    :param text: Text to extract issue IDs from
    :param project_name: Name of the project to match issue IDs
    :return: List of issue IDs
    """
    issue_matcher = re.compile("{}-{}".format(project_name, r'\d+'))
    return list(issue_matcher.findall(text))


def extract_revisions(text: str, uniform: bool = False) -> List[str]:
    """
    Extract all revisions mentioned in the text.
    If "uniform" is set to True, then all revisions are converted to the form "rXXXXX".
    :param text: Text to extract revisions from
    :param uniform: Whether to convert revisions to the form "rXXXXX"
    :return: Extracted revisions
    """
    revisions = list(revision_matcher.findall(text))
    if uniform:
        revisions = list(
            map(
                lambda revision: "r{}".format(extract_numbers(revision)[0]),
                revisions
            )
        )
    return revisions


def extract_numbers(text: str) -> List[str]:
    """
    Extract numbers from the text.
    :param text: Text to extract numbers from
    :return: List of strings containing a single number each
    """
    return list(re.findall(r'\d+', text))


def clean_text(text: str) -> str:
    """
    Prepare text to be parsed by URL regex.
    By now, the regex doesn't parse URLs 100% correctly, so they may end up having redundant characters.

    The reason is that the regex tries to catch all possible formats of URLs, including those which are typed by hand.
    Such URLS may contain specific characters like brackets, '<', '>' and backslash.
    Developers usually just copy-paste URLs from a browser's address bar, and browsers, for their part, have those URLs
    already formatted to exclude those characters (e.g. '[' -> "%5B", ')' -> "%29")

    TODO: Either:
        1. Adjust the regex to match URLs already formatted by a browser
        2. Join replace() calls below into a regex
    :param text: Text to remove characters from
    :return: Cleaned text
    """
    chars_to_remove = [r'\n', '(', ')', '[', ']', '<', '>', '\\']
    for char in chars_to_remove:
        text = text.replace(char, ' ')
    return text