import argparse
import json
from jira_parser import JiraParser
import matplotlib.pyplot as plt
import os
from typing import List, Tuple, Set
import shutil

import utils

PROJECTS = [
    "PDFBOX",
    "DERBY",
    "CASSANDRA",
    "YARN",
    "HDFS",
    "HADOOP",
    "MAPREDUCE",
    "ZOOKEEPER",
    "CONNECTORS",  # ManifoldCF https://issues.apache.org/jira/projects/CONNECTORS/summary
    "BIGTOP",
    "OFBIZ",
    "DIRSTUDIO",  # Directory Studio https://issues.apache.org/jira/projects/DIRSTUDIO/summary
    "DIRMINA",  # MINA https://issues.apache.org/jira/projects/DIRMINA/summary
    "CAMEL",  # Camel https://issues.apache.org/jira/projects/CAMEL/summary
    "AXIS2"  # Axis2 https://issues.apache.org/jira/projects/AXIS2/summary
]

PROJECTS_WITH_QA_BOTS = [
    "HBASE",  # HBase https://issues.apache.org/jira/projects/HBASE/summary
    "HIVE",  # Hive https://issues.apache.org/jira/projects/HIVE/summary
]

PROJECTS_WITH_PULL_REQUESTS = [
    "TAJO",  # Tajo https://issues.apache.org/jira/projects/TAJO/summary
    "NUTCH"  # Nutch https://issues.apache.org/jira/projects/NUTCH/summary
]


def parse_arguments():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-j", "--jira-project", help="Target Jira project")
    return arg_parser.parse_args()


def collect_issue_summary(project: str, issue: dict, save=True) -> \
        Tuple[str, int, Set[str], Set[str], Set[str], Set[str], Set[str], Set[str]]:
    """

    :param project: Related project
    :param issue: Issue represented as a dictionary
    :param save: Whether to save the statistics on hard drive
    :return:
    """

    # FIELD 1: issue key
    issue_key = str(issue["issue_key"])

    # FIELD 2: issue ID; used to increase the efficiency of sorting the data
    issue_id = int(issue_key.split('-')[1])

    # Parse Description and Remote Links. Remote links are not different from any other type of URLs,
    # so we will just append them to the description of the issue in order to avoid code duplication.
    description_and_remote_links = issue["description"] + " " + " ".join(
        [remote_link["url"] for remote_link in issue["remotelinks"]]
    )

    # FIELD 3: unparsed URLs
    # FIELD 4: revision IDs
    # FIELD 5: URLs detected as mailing lists
    # FIELD 6: URLs detected as PDF documents
    # FIELD 7: Other issues
    urls, revisions, mailing_lists, pdf_documents, archives, other_issues = \
        utils.extract_references(description_and_remote_links, project)

    # Parse Comments
    for comment in issue["comments"]:
        comment_details = utils.extract_references(comment["body"], project)
        urls.update(comment_details[0])
        revisions.update(comment_details[1])
        mailing_lists.update(comment_details[2])
        pdf_documents.update(comment_details[3])
        archives.update(comment_details[4])
        other_issues.update(comment_details[5])

    for issue in issue["issuelinks"]:
        other_issues.add(issue["issue_key"])

    summary = (issue_key,
               issue_id,
               urls,
               revisions,
               mailing_lists,
               pdf_documents,
               archives,
               other_issues)

    if save:
        __save_references(project, summary)
    return summary


def collect_issues_summary(project: str, save=True) -> List[
    Tuple[str, int, Set[str], Set[str], Set[str], Set[str], Set[str], Set[str]]]:
    """
    For each Issue inside Projects/<project>/Issues, extract all types of references and return a data type containing
    all the necessary data
    :param project: Project to extract references from
    :param save: Whether to save extracted references to JSON documents
    :return: List of tuples containing data
    """
    directory = os.path.join("Projects", project, "Issues")
    if not os.path.isdir(directory):
        print("The folder does not exist. Make sure you fetched and parsed at least one issue.")
        return []
    issues_dir = os.listdir(directory)
    issues = []

    for filename in issues_dir:
        path = os.path.join(directory, filename)
        with open(path, 'r') as issue_file:
            issue = json.load(issue_file)
            summary = collect_issue_summary(project, issue, save)
            issues.append(summary)
    return issues


def __save_references(project: str,
                      issue_summary: Tuple[
                          str, int, Set[str], Set[str], Set[str], Set[str], Set[str], Set[str]
                      ]) -> None:
    """
    Save references for an issue in JSON format.
    :param project: Project to write references for
    :param issue_summary: Data type describing necessary data
    :return: None
    """
    summary_dir = os.path.join("Projects", project, "Summary")
    if not os.path.isdir(summary_dir):
        os.mkdir(summary_dir)

    issue_dict = {
        "issue_key": issue_summary[0],
        "issue_id": issue_summary[1],
        "urls": list(issue_summary[2]),
        "revisions": list(issue_summary[3]),
        "mailing_lists": list(issue_summary[4]),
        "pdf_documents": list(issue_summary[5]),
        "archives": list(issue_summary[6]),
        "other_issues": list(issue_summary[7])
    }
    path = os.path.join(summary_dir, issue_summary[0] + ".json")
    utils.save_as_json(issue_dict, path)


def generate_statistics(project: str) -> List[Tuple[int, int, int, int, int, int, int, int]]:
    """
    Based on the references for each issue, generate the frequency of each type of references and split the data
    into blocks of 100 issues for a broader analysis of the data.
    :param project: Project to parse references from
    :return: List of tuples representing generated statistics with the following fields:
        1. Current block description (e.g. 100 means block 1-100, 400 means block 301-400)
        2. Total number of references in block
        3. Number of revisions
        4. Number of mailing lists
        5. Number of PDF documents URLs
        6. Number of other issues
        7. Number of uncategorized URLs
    """
    issues = []
    summary_directory = os.path.join("Projects", project, "Summary")

    for filename in os.listdir(summary_directory):
        path = os.path.join(summary_directory, filename)
        with open(path, 'r') as file:
            data = json.load(file)
            issues.append(
                (str(data["issue_key"]),
                 int(data["issue_id"]),
                 list(data["urls"]),
                 list(data["revisions"]),
                 list(data["mailing_lists"]),
                 list(data["pdf_documents"]),
                 list(data["archives"]),
                 list(data["other_issues"]))
            )
    issues = sorted(issues, key=lambda x: x[1])

    # Since the number of references in each issue can be very little, it makes sense to combine them in blocks of 100
    # in order to have a better overview of the development of the project.
    blocks = []
    block_size = 100
    block_idx = 0
    while True:
        start_idx = block_idx * block_size
        block = issues[start_idx:start_idx + block_size]
        if len(block) == 0:
            break
        blocks.append(block)
        block_idx += 1

    # Now it's time to collect statistics
    block_idx = 1
    statistics = []
    for block in blocks:
        total = 0
        revisions = 0
        mailing_lists = 0
        pdf_documents = 0
        archives = 0
        other_issues = 0
        other_urls = 0
        for issue in block:
            revisions += len(issue[3])
            mailing_lists += len(issue[4])
            pdf_documents += len(issue[5])
            archives += len(issue[6])
            other_issues += len(issue[7])
            other_urls += len(issue[2])
            for i in range(2, 8):
                total += len(issue[i])
        statistics.append(
            (block_idx * 100, total, revisions, mailing_lists, pdf_documents, archives, other_issues, other_urls))
        block_idx += 1
    return statistics


def make_plot(project: str, plots_dir: str,
              statistics: List[Tuple[int, int, int, int, int, int, int]], blocks: List[int],
              param_idx: int, param_title: str):
    x = blocks
    y = [param[param_idx] for param in statistics]
    plt.plot(x, y)
    plt.xlabel("Issue IDs")
    plt.ylabel("Frequency of {}".format(param_title))
    plt.title("Changes in frequency of {} through the evolution of the project {}".format(param_title, project))
    plt.savefig(os.path.join(plots_dir, param_title + ".png"), bbox_inches='tight')
    plt.close()


def make_plots(project: str, statistics: List[Tuple[int, int, int, int, int, int, int, int]]):
    blocks = [param[0] for param in statistics]
    types = [
        (1, "Total references"),
        (2, "Revisions"),
        (3, "Mailing Lists"),
        (4, "PDF documents"),
        (5, "Archives"),
        (6, "Other issues"),
        (7, "Other URLs")
    ]

    plots_dir = os.path.join("Projects", project, "Plots")
    shutil.rmtree(plots_dir, ignore_errors=True)
    os.mkdir(plots_dir)

    for t in types:
        make_plot(project, plots_dir, statistics, blocks, t[0], t[1])


if __name__ == "__main__":
    args = parse_arguments()
    if args.jira_project:
        PROJECTS = [args.jira_project]
    for project in PROJECTS:
        parser = JiraParser(project)
        parser.fetch_issues_raw()
        parser.parse_issues()
        summary = collect_issues_summary(project)
        statistics = generate_statistics(project)
        make_plots(project, statistics)
