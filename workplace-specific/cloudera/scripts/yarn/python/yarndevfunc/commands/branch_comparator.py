import logging
import os
from enum import Enum
from typing import Dict, List, Tuple, Set
from colr import color
from pythoncommons.date_utils import DateUtils
from pythoncommons.file_utils import FileUtils
from commands.upstream_jira_umbrella_fetcher import CommitData
from constants import ANY_JIRA_ID_PATTERN
from git_wrapper import GitWrapper
from yarndevfunc.utils import StringUtils, ResultPrinter

LOG = logging.getLogger(__name__)


class BranchType(Enum):
    FEATURE = "feature branch"
    MASTER = "master branch"


class BranchData:
    def __init__(self, type: BranchType, branch_name: str):
        self.type: BranchType = type
        self.name: str = branch_name

        # Set later
        self.gitlog_results: List[str] = []
        # Commit objects in reverse order (from oldest to newest)
        # Commits stored in a list, in order from last to first commit (descending)
        self.commit_objs: List[CommitData] = []
        self.commits_before_merge_base: List[CommitData] = []
        self.commits_after_merge_base: List[CommitData] = []
        self.hash_to_index: Dict[str, int] = {}  # Dict: commit hash to commit index
        # TODO hash_to_commit is unused
        self.hash_to_commit: Dict[str, str] = {}  # Dict: commit hash to CommitData object
        self.jira_id_to_commit: Dict[str, CommitData] = {}  # Dict: Jira ID (e.g. YARN-1234) to CommitData object
        self.unique_commits: List[CommitData] = []
        self.merge_base_idx: int = -1

    @property
    def number_of_commits(self):
        return len(self.gitlog_results)

    def set_merge_base(self, merge_base_hash: str):
        # TODO if hash not found throw exception
        self.merge_base_idx = self.hash_to_index[merge_base_hash]
        # TODO raise exception if self.commit_objs is empty
        self.commits_before_merge_base = self.commit_objs[: self.merge_base_idx]
        self.commits_after_merge_base = self.commit_objs[self.merge_base_idx :]


# TODO use this class
class SummaryData(object):
    pass


class Branches:
    def __init__(self, output_dir: str, repo: GitWrapper, branch_dict: dict, fail_on_missing_jira_id=False):
        self.output_dir = output_dir
        self.repo = repo
        self.branch_data: Dict[BranchType, BranchData] = {}
        for br_type in BranchType:
            branch_name = branch_dict[br_type]
            self.branch_data[br_type] = BranchData(br_type, branch_name)
        self.fail_on_missing_jira_id = fail_on_missing_jira_id

        # Set later
        self.merge_base: str = ""
        self.summary_data = SummaryData()
        self.common_commits: List[CommitData] = []

    def get_branch(self, br_type: BranchType) -> BranchData:
        return self.branch_data[br_type]

    @staticmethod
    def _generate_filename(basedir, prefix, branch_name) -> str:
        return FileUtils.join_path(basedir, f"{prefix}{StringUtils.replace_special_chars(branch_name)}")

    def validate(self, br_type: BranchType):
        br_data = self.branch_data[br_type]
        branch_exist = self.repo.is_branch_exist(br_data.name)
        if not branch_exist:
            LOG.error(f"{br_data.type.name} does not exist with name '{br_data.name}'")
        return branch_exist

    def execute_git_log(self, print_stats=True, save_to_file=True):
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            branch.gitlog_results = self.repo.log(branch.name, oneline_with_date_and_author=True)
            # Store commit objects in reverse order (ascending by date)
            branch.commit_objs = list(
                reversed(
                    [
                        CommitData.from_git_log_str(
                            commit_str,
                            format="oneline_with_date_and_author",
                            pattern=ANY_JIRA_ID_PATTERN,
                            allow_unmatched_jira_id=True,
                        )
                        for commit_str in branch.gitlog_results
                    ]
                )
            )
            commits_with_missing_jira_id = list(filter(lambda c: not c.jira_id, branch.commit_objs))
            LOG.debug(f"Found commits with empty Jira ID: {commits_with_missing_jira_id}")
            if self.fail_on_missing_jira_id:
                raise ValueError(f"Found {len(commits_with_missing_jira_id)} commits with empty Jira ID!")

            for idx, commit in enumerate(branch.commit_objs):
                branch.hash_to_commit[commit.hash] = commit
                branch.hash_to_index[commit.hash] = idx
                branch.jira_id_to_commit[commit.jira_id] = commit
        # This must be executed after branch.hash_to_index is set
        self.get_merge_base()

        if print_stats:
            self._print_stats()
        if save_to_file:
            self._save_git_log_to_file()

    def _print_stats(self):
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            LOG.info(f"Found {branch.number_of_commits} commits on feature branch: {branch.name}")

    def _save_git_log_to_file(self):
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            # We would like to maintain descending order of commits in printouts
            self.write_to_file("git log output", branch, list(reversed(branch.commit_objs)))

    def _save_commits_before_after_merge_base_to_file(self):
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            self.write_to_file("before merge base commits", branch, branch.commits_before_merge_base)
            self.write_to_file("before after base commits", branch, branch.commits_after_merge_base)

    def get_merge_base(self):
        merge_base = self.repo.merge_base(
            self.branch_data[BranchType.FEATURE].name, self.branch_data[BranchType.MASTER].name
        )
        if len(merge_base) > 1:
            raise ValueError(f"Ambiguous merge base: {merge_base}.")
        self.merge_base = merge_base[0]
        LOG.info(f"Merge base of branches: {self.merge_base}")
        for br_type in BranchType:
            branch: BranchData = self.branch_data[br_type]
            branch.set_merge_base(self.merge_base.hexsha)

    def compare(self, commit_author_exceptions):
        self._save_commits_before_after_merge_base_to_file()
        feature_br: BranchData = self.branch_data[BranchType.FEATURE]
        master_br: BranchData = self.branch_data[BranchType.MASTER]

        self._sanity_check_commits_before_merge_base(feature_br, master_br)
        self._check_after_merge_base_commits(feature_br, master_br, commit_author_exceptions)

    def _sanity_check_commits_before_merge_base(self, feature_br: BranchData, master_br: BranchData):
        if len(master_br.commits_before_merge_base) != len(feature_br.commits_before_merge_base):
            raise ValueError(
                "Number of commits before merge_base does not match. "
                f"Feature branch has: {len(feature_br.commits_before_merge_base)} commits, "
                f"Master branch has: {len(master_br.commits_before_merge_base)} commits"
            )
        # Commit hashes up to the merge-base commit should be the same for both branches
        for idx, commit1 in enumerate(master_br.commits_before_merge_base):
            commit2 = feature_br.commits_before_merge_base[idx]
            if commit1.hash != commit2.hash:
                raise ValueError(
                    f"Commit hash mismatch below merge-base commit.\n"
                    f"Index: {idx}\n"
                    f"Hash of commit on {feature_br.name}: {commit2.hash}\n"
                    f"Hash of commit on {master_br.name}: {commit1.hash}"
                )
        LOG.info(
            f"Detected {len(master_br.commits_before_merge_base)} common commits between "
            f"'{feature_br.name}' and '{master_br.name}'"
        )

    def _check_after_merge_base_commits(
        self, feature_br: BranchData, master_br: BranchData, commit_author_exceptions: List[str]
    ):
        # TODO do something with this list
        common_but_commit_msg_differs: List[Tuple[CommitData, CommitData]] = []

        # TODO write these to file
        master_commits_without_jira_id: List[CommitData] = list(
            filter(lambda c: not c.jira_id, master_br.commits_after_merge_base)
        )
        feature_commits_without_jira_id: List[CommitData] = list(
            filter(lambda c: not c.jira_id, feature_br.commits_after_merge_base)
        )
        LOG.warning(
            f"Found {len(master_commits_without_jira_id)} master branch commits with empty Jira ID: {master_commits_without_jira_id}"
        )
        LOG.warning(
            f"Found {len(feature_commits_without_jira_id)} feature branch commits with empty Jira ID: {feature_commits_without_jira_id}"
        )

        # Create a dict of (commit message, CommitData), filtering all the commits that has author from the exceptional authors.
        # Assumption: Commit message is unique for all commits
        master_commits_without_jira_id_filtered = dict(
            [
                (c.message, c)
                for c in filter(lambda c: c.author not in commit_author_exceptions, master_commits_without_jira_id)
            ]
        )
        feature_commits_without_jira_id_filtered = dict(
            [
                (c.message, c)
                for c in filter(lambda c: c.author not in commit_author_exceptions, feature_commits_without_jira_id)
            ]
        )
        LOG.warning(
            f"Found {len(master_commits_without_jira_id_filtered)} master branch commits with empty Jira ID "
            f"(after applied author filter: {commit_author_exceptions}): {master_commits_without_jira_id_filtered}"
        )
        LOG.warning(
            f"Found {len(feature_commits_without_jira_id_filtered)} feature branch commits with empty Jira ID "
            f"(after applied author filter: {commit_author_exceptions}): {feature_commits_without_jira_id_filtered}"
        )

        # List of tuples. First item: Master branch commit obj, second item: feature branch commit obj
        self.common_commits: List[Tuple[CommitData, CommitData]] = []
        common_jira_ids: Set[str] = set()
        common_commit_msgs: Set[str] = set()
        for master_commit in master_br.commits_after_merge_base:
            master_commit_msg = master_commit.message
            if not master_commit.jira_id:
                # If this commit is without jira id and author was not an element of exceptional authors,
                # then try to match commits across branches by commit message.
                if master_commit_msg in master_commits_without_jira_id_filtered:
                    LOG.debug(
                        "Trying to match commit by commit message as Jira ID is missing. Details: \n"
                        f"Branch: master branch\n"
                        f"Commit message: ${master_commit_msg}\n"
                    )
                    if master_commit_msg in feature_commits_without_jira_id_filtered:
                        # TODO Write these special commits to separate file
                        LOG.warning(
                            "Found matching commit by commit message. Details: \n"
                            f"Branch: master branch\n"
                            f"Commit message: ${master_commit_msg}\n"
                        )
                        self.common_commits.append(
                            (master_commit, feature_commits_without_jira_id_filtered[master_commit_msg])
                        )
                        common_commit_msgs.add(master_commit_msg)
            elif master_commit.jira_id in feature_br.jira_id_to_commit:
                # Normal path: Try to match commits across branches by Jira ID
                feature_commit = feature_br.jira_id_to_commit[master_commit.jira_id]
                LOG.debug(
                    "Found same commit on both branches (by Jira ID):\n"
                    f"Master branch commit: {master_commit.as_oneline_string()}\n"
                    f"Feature branch commit: {feature_commit.as_oneline_string()}"
                )

                # TODO Handle multiple jira ids?? example: "CDPD-10052. HADOOP-16932"
                # TODO Handle reverts?
                if master_commit_msg != feature_commit.message:
                    # TODO Write these special commits to separate file
                    LOG.warning(
                        "Jira ID is the same for commits, but commit message differs: \n"
                        f"Master branch commit: {master_commit.as_oneline_string()}\n"
                        f"Feature branch commit: {feature_commit.as_oneline_string()}"
                    )
                    common_but_commit_msg_differs.append((master_commit, feature_commit))

                # Either if commit message matched or not, count this as a common commit as Jira ID matched
                self.common_commits.append((master_commit, feature_commit))
                common_jira_ids.add(master_commit.jira_id)

        master_br.unique_commits = self._filter_relevant_unique_commits(
            master_br.commits_after_merge_base,
            master_commits_without_jira_id_filtered,
            common_jira_ids,
            common_commit_msgs,
        )
        feature_br.unique_commits = self._filter_relevant_unique_commits(
            feature_br.commits_after_merge_base,
            feature_commits_without_jira_id_filtered,
            common_jira_ids,
            common_commit_msgs,
        )
        LOG.info(f"Identified {len(master_br.unique_commits)} unique commits on branch: {master_br.name}")
        LOG.info(f"Identified {len(feature_br.unique_commits)} unique commits on branch: {feature_br.name}")
        self.write_to_file("unique commits", master_br, master_br.unique_commits)
        self.write_to_file("unique commits", feature_br, feature_br.unique_commits)

    @staticmethod
    def _filter_relevant_unique_commits(
        commits: List[CommitData], commits_without_jira_id_filtered, common_jira_ids, common_commit_msgs
    ) -> List[CommitData]:
        result = []
        # 1. Values of commit list can contain commits without Jira ID
        # and we don't want to count them as unique commits unless the commit is a
        # special authored commit and it's not a common commit by its message
        # 2. If Jira ID is in common_jira_ids, it's not a unique commit, either.
        for commit in commits:
            special_unique_commit = (
                not commit.jira_id
                and commit.message in commits_without_jira_id_filtered
                and commit.message not in common_commit_msgs
            )
            normal_unique_commit = commit.jira_id is not None and commit.jira_id not in common_jira_ids
            if special_unique_commit or normal_unique_commit:
                result.append(commit)
        return result

    def write_to_file(self, output_type: str, branch: BranchData, commits: List[CommitData]):
        file_prefix: str = output_type.replace(" ", "-") + "-"
        f = self._generate_filename(self.output_dir, file_prefix, branch.name)
        LOG.info(f"Saving {output_type} for branch {branch.type.name} to file: {f}")
        FileUtils.save_to_file(f, StringUtils.list_to_multiline_string([c.as_oneline_string() for c in commits]))


class TableWithHeader:
    def __init__(self, header_title, table: str):
        self.header = (
            StringUtils.generate_header_line(
                header_title, char="═", length=len(StringUtils.get_first_line_of_multiline_str(table))
            )
            + "\n"
        )
        self.table = table

    def __str__(self):
        return self.header + self.table


class BranchComparator:
    # TODO Add documentation
    """"""

    def __init__(self, args, downstream_repo, output_dir):
        self.repo = downstream_repo
        dt_string = DateUtils.now_formatted("%Y%m%d_%H%M%S")
        self.output_dir = FileUtils.ensure_dir_created(FileUtils.join_path(output_dir, f"session-{dt_string}"))
        self.branches: Branches = Branches(
            self.output_dir, self.repo, {BranchType.FEATURE: args.feature_branch, BranchType.MASTER: args.master_branch}
        )
        self.commit_author_exceptions = args.commit_author_exceptions

    def run(self, args):
        # TODO Turn on Debug logging by default
        LOG.info(
            "Starting Branch comparator... \n "
            f"Output dir: {self.output_dir}\n"
            f"Master branch: {args.master_branch}\n "
            f"Feature branch: {args.feature_branch}\n "
        )
        self.validate_branches()
        # TODO DO NOT FETCH FOR NOW, Uncomment if finished with testing
        # self.repo.fetch(all=True)
        self.compare()

    def validate_branches(self):
        both_exist = self.branches.validate(BranchType.FEATURE)
        both_exist &= self.branches.validate(BranchType.MASTER)
        if not both_exist:
            raise ValueError("Both feature and master branch should be an existing branch. Exiting...")

    def compare(self):
        self.branches.execute_git_log(print_stats=True, save_to_file=True)
        self.branches.compare(self.commit_author_exceptions)

        # Print and save summary
        summary_string = self.render_summary_string()
        LOG.info(summary_string)
        filename = FileUtils.join_path(self.output_dir, "summary.txt")
        LOG.info(f"Saving summary to file: {filename}")
        FileUtils.save_to_file(filename, summary_string)

        # TODO 1. Write fancy table to console with unique commits (DO NOT INCLUDE COMMON COMMITS)
        # TODO 2. Stdout mode: Instead of writing to individual files, write everything to console --> Useful for CDSW runs!
        # TODO 3. Run git_compare.sh and store results + diff git_compare.sh results with my script result, report if different!
        # TODO 4. Handle revert commits?

    def render_summary_string(self):
        # Generate tables first, in order to know the length of the header rows

        result_files_table = TableWithHeader(
            "RESULT FILES",
            ResultPrinter.print_table(
                FileUtils.find_files(self.output_dir, regex=".*", full_path_result=True),
                lambda file: (file,),
                header=["Row", "File"],
                print_result=False,
                max_width=80,
                max_width_separator=os.sep,
            ),
        )

        master_br = self.branches.get_branch(BranchType.MASTER)
        feature_br = self.branches.get_branch(BranchType.FEATURE)
        uniq_master_commits_table = TableWithHeader(
            f"UNIQUE ON BRANCH {master_br.name}",
            ResultPrinter.print_table(
                master_br.unique_commits,
                lambda commit: (commit.jira_id, commit.message, commit.date),
                header=["Row", "Jira ID", "Commit message", "Commit date"],
                print_result=False,
                max_width=80,
                max_width_separator=" ",
            ),
        )
        uniq_feature_commits_table = TableWithHeader(
            f"UNIQUE ON BRANCH {feature_br.name}",
            ResultPrinter.print_table(
                feature_br.unique_commits,
                lambda commit: (commit.jira_id, commit.message, commit.date),
                header=["Row", "Jira ID", "Commit message", "Commit date"],
                print_result=False,
                max_width=80,
                max_width_separator=" ",
            ),
        )

        common_commits = [c[0] for c in self.branches.common_commits]
        common_commits_table = TableWithHeader(
            "COMMON COMMITS SINCE BRANCHES DIVERGED",
            ResultPrinter.print_table(
                common_commits,
                lambda commit: (commit.jira_id, commit.message, commit.date),
                header=["Row", "Jira ID", "Commit message", "Commit date"],
                print_result=False,
                max_width=80,
                max_width_separator=" ",
            ),
        )
        all_commits_list: List[CommitData] = [] + master_br.unique_commits + feature_br.unique_commits + common_commits
        all_commits_list.sort(key=lambda c: c.date, reverse=True)

        all_commits_rows = []
        for commit in all_commits_list:
            jira_id = commit.jira_id
            present_on_branches = []
            if jira_id in master_br.jira_id_to_commit and jira_id in feature_br.jira_id_to_commit:
                present_on_branches = [True, True]
            elif jira_id in master_br.jira_id_to_commit:
                present_on_branches = [True, False]
            elif jira_id in feature_br.jira_id_to_commit:
                present_on_branches = [False, True]

            curr_row = [jira_id, commit.message, commit.date]
            curr_row.extend(present_on_branches)
            curr_row = self.colorize_row(curr_row, convert_bools=True)
            all_commits_rows.append(curr_row)

        header = ["Row", "Jira ID", "Commit message", "Commit date"]
        header.extend([master_br.name, feature_br.name])
        all_commits_table = TableWithHeader(
            "ALL COMMITS (MERGED LIST)",
            ResultPrinter.print_table(
                all_commits_rows,
                lambda row: row,
                header=header,
                print_result=False,
                max_width=50,
                max_width_separator=" ",
            ),
        )

        # Generate summary string
        summary_str = "\n\n" + (
            StringUtils.generate_header_line(
                "SUMMARY", char="═", length=len(StringUtils.get_first_line_of_multiline_str(common_commits_table.table))
            )
            + "\n"
        )

        # TODO print self.summary_data
        # summary_str += f"Number of jiras: {self.no_of_jiras}\n"
        # summary_str += f"Number of commits: {self.no_of_commits}\n"
        # summary_str += f"Number of files changed: {self.no_of_files}\n"
        summary_str += str(result_files_table)
        summary_str += "\n\n"
        summary_str += str(uniq_feature_commits_table)
        summary_str += "\n\n"
        summary_str += str(uniq_master_commits_table)
        summary_str += "\n\n"
        summary_str += str(common_commits_table)
        summary_str += "\n\n"
        summary_str += str(all_commits_table)
        summary_str += "\n\n"
        return summary_str

    # TODO code is duplicated - Copied from upstream_jira_umbrella_fetcher.py
    @staticmethod
    def colorize_row(curr_row, convert_bools=False):
        res = []
        missing_backport = False
        if not all(curr_row[1:]):
            missing_backport = True

        # Mark first cell with red if any of the backports are missing
        # Mark first cell with green if all backports are present
        # Mark any bool cell with green if True, red if False
        for idx, cell in enumerate(curr_row):
            if (isinstance(cell, bool) and cell) or not missing_backport:
                if convert_bools and isinstance(cell, bool):
                    cell = "X" if cell else "-"
                res.append(color(cell, fore="green"))
            else:
                if convert_bools and isinstance(cell, bool):
                    cell = "X" if cell else "-"
                res.append(color(cell, fore="red"))
        return res
