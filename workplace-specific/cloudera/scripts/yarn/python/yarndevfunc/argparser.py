import argparse
from enum import Enum


class CommandType(Enum):
    SAVE_PATCH = "save_patch"
    CREATE_REVIEW_BRANCH = "create_review_branch"
    BACKPORT_C6 = "backport_c6"
    UPSTREAM_PR_FETCH = "upstream_pr_fetch"
    SAVE_DIFF_AS_PATCHES = "save_diff_as_patches"
    DIFF_PATCHES_OF_JIRA = "diff_patches_of_jira"
    FETCH_JIRA_UMBRELLA_DATA = "fetch_jira_umbrella_data"


class ArgParser:
    @staticmethod
    def parse_args(yarn_functions):
        """This function parses and return arguments passed in"""

        # Top-level parser
        parser = argparse.ArgumentParser()

        # Subparsers
        subparsers = parser.add_subparsers(
            title="subcommands",
            description="valid subcommands",
            help="Available subcommands",
            required=True,
            dest="test",
        )
        ArgParser.add_save_patch_parser(subparsers, yarn_functions)
        ArgParser.add_create_review_branch_parser(subparsers, yarn_functions)
        ArgParser.add_backport_c6_parser(subparsers, yarn_functions)
        ArgParser.add_upstream_pull_request_fetcher(subparsers, yarn_functions)
        ArgParser.add_save_diff_as_patches(subparsers, yarn_functions)
        ArgParser.diff_patches_of_jira(subparsers, yarn_functions)
        ArgParser.add_fetch_jira_umbrella_data(subparsers, yarn_functions)

        # Normal arguments
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            dest="verbose",
            default=None,
            required=False,
            help="More verbose log",
        )

        args = parser.parse_args()
        if args.verbose:
            print("Args: " + str(args))
        return args

    @staticmethod
    def add_save_patch_parser(subparsers, yarn_functions):
        parser = subparsers.add_parser(
            CommandType.SAVE_PATCH.value, help="Saves patch from upstream repository to yarn patches dir"
        )
        parser.set_defaults(func=yarn_functions.save_patch)

    @staticmethod
    def add_create_review_branch_parser(subparsers, yarn_functions):
        parser = subparsers.add_parser(
            CommandType.CREATE_REVIEW_BRANCH.value, help="Creates review branch from upstream patch file"
        )
        parser.add_argument("patch_file", type=str, help="Path to patch file")
        parser.set_defaults(func=yarn_functions.create_review_branch)

    @staticmethod
    def add_backport_c6_parser(subparsers, yarn_functions):
        parser = subparsers.add_parser(
            CommandType.BACKPORT_C6.value,
            help="Backports upstream commit to C6 branch, " "Example usage: <command> YARN-7948 CDH-64201 cdh6.x",
        )
        parser.add_argument("upstream_jira_id", type=str, help="Upstream jira id. Example: YARN-4567")
        # TODO rename this to downstream
        parser.add_argument("cdh_jira_id", type=str, help="Downstream jira id. Example: CDH-4111")
        # TODO rename this to downstream
        parser.add_argument("cdh_branch", type=str, help="Downstream branch name")
        parser.set_defaults(func=yarn_functions.backport_c6)

    @staticmethod
    def add_upstream_pull_request_fetcher(subparsers, yarn_functions):
        parser = subparsers.add_parser(
            CommandType.UPSTREAM_PR_FETCH.value,
            help="Fetches upstream changes from a repo then cherry-picks single commit."
            "Example usage: <command> szilard-nemeth YARN-9999",
        )
        parser.add_argument("github_username", type=str, help="Github username")
        parser.add_argument("remote_branch", type=str, help="Name of the remote branch.")
        parser.set_defaults(func=yarn_functions.upstream_pr_fetch)

    @staticmethod
    def add_save_diff_as_patches(subparsers, yarn_functions):
        parser = subparsers.add_parser(
            CommandType.SAVE_DIFF_AS_PATCHES.value,
            help="Diffs branches and creates patch files with "
            "git format-patch and saves them to a directory."
            "Example: <command> master gpu",
        )
        parser.add_argument("base_refspec", type=str, help="Git base refspec to diff with.")
        parser.add_argument("other_refspec", type=str, help="Git other refspec to diff with.")
        parser.add_argument("dest_basedir", type=str, help="Destination basedir.")
        parser.add_argument("dest_dir_prefix", type=str, help="Directory as prefix to export the patch files to.")
        parser.set_defaults(func=yarn_functions.save_patches)

    @staticmethod
    def diff_patches_of_jira(subparsers, yarn_functions):
        parser = subparsers.add_parser(
            CommandType.DIFF_PATCHES_OF_JIRA.value,
            help="Diffs patches of a particular jira, for the provided branches."
            "Example: YARN-7913 trunk branch-3.2 branch-3.1",
        )
        parser.add_argument("jira_id", type=str, help="Upstream Jira ID.")
        parser.add_argument("branches", type=str, nargs="+", help="Check all patches on theese branches.")
        parser.set_defaults(func=yarn_functions.diff_patches_of_jira)

    @staticmethod
    def add_fetch_jira_umbrella_data(subparsers, yarn_functions):
        parser = subparsers.add_parser(
            CommandType.FETCH_JIRA_UMBRELLA_DATA.value,
            help="Fetches jira umbrella data for a provided Jira ID." "Example: fetch_jira_umbrella_data YARN-5734",
        )
        parser.add_argument("jira_id", type=str, help="Upstream Jira ID.")
        parser.add_argument(
            "--force-mode",
            action="store_true",
            dest="force_mode",
            help="Force fetching data from jira and use git log commands to find all changes.",
        )
        parser.set_defaults(func=yarn_functions.fetch_jira_umbrella_data)
