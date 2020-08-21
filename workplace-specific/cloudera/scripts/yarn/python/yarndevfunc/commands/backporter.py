import logging

from yarndevfunc.constants import ORIGIN, HEAD, GERRIT_REVIEWER_LIST, COMMIT_FIELD_SEPARATOR

LOG = logging.getLogger(__name__)


class Backporter:
    def __init__(self, args, upstream_repo, downstream_repo, cherry_pick_base_ref, default_branch):
        self.args = args
        self.upstream_repo = upstream_repo
        self.downstream_repo = downstream_repo

        self.upstream_jira_id = self.args.upstream_jira_id
        self.cdh_jira_id = self.args.cdh_jira_id
        self.cdh_branch = self.args.cdh_branch
        self.cherry_pick_base_ref = cherry_pick_base_ref
        self.default_branch = default_branch

    def run(self):
        """
        This script assumes that the commit is already on trunk!
        :return:
        """
        self.sync_upstream_repo()
        commit_hash = self.get_upstream_commit_hash()

        # DO THE REST OF THE WORK IN THE DOWNSTREAM REPO
        self.downstream_repo.fetch(all=True)
        self.cherry_pick_commit(commit_hash)
        self.rewrite_commit_message()
        self.post_commit_actions()

    def get_upstream_commit_hash(self):
        git_log_result = self.upstream_repo.log(HEAD, oneline=True, grep=self.upstream_jira_id)
        # Restore original branch in either error-case or normal case
        self.upstream_repo.checkout_previous_branch()
        if not git_log_result:
            raise ValueError("No match found for upsream commit with name: %s", self.upstream_jira_id)
        if len(git_log_result) > 1:
            raise ValueError(
                "Ambiguous upsream commit with name: %s. Results: %s", self.upstream_jira_id, git_log_result
            )
        commit_hash = git_log_result[0].split(COMMIT_FIELD_SEPARATOR)[0]
        return commit_hash

    def sync_upstream_repo(self):
        # TODO decide on the cdh branch whether this is C5 or C6 backport (remote is different)
        curr_branch = self.upstream_repo.get_current_branch_name()
        LOG.info("Current branch: %s", curr_branch)
        self.upstream_repo.fetch(all=True)
        self.upstream_repo.checkout_branch(self.default_branch)
        self.upstream_repo.pull(ORIGIN)

    def cherry_pick_commit(self, commit_hash):
        # TODO handle if branch already exist (is it okay to silently ignore?) or should use current branch with switch?

        # Example checkout command: git checkout -b "$CDH_JIRA_NO-$CDH_BRANCH" cauldron/${CDH_BRANCH}
        new_branch_name = "{}-{}".format(self.cdh_jira_id, self.cdh_branch)
        success = self.downstream_repo.checkout_new_branch(new_branch_name, self.cherry_pick_base_ref)
        if not success:
            raise ValueError(
                "Cannot checkout new branch {} based on ref {}".format(new_branch_name, self.cherry_pick_base_ref)
            )

        exists = self.downstream_repo.is_branch_exist(commit_hash)
        if not exists:
            raise ValueError(
                "Cannot find commit with hash {}. "
                "Please verify if downstream repo has a remote to the upstream repo!",
                commit_hash,
            )
        cherry_pick_result = self.downstream_repo.cherry_pick(commit_hash, x=True)

        if not cherry_pick_result:
            raise ValueError(
                "Failed to cherry-pick commit: {}. "
                "Perhaps there were some merge conflicts, "
                "please resolve them and run: git cherry-pick --continue".format(commit_hash)
            )

    def rewrite_commit_message(self):
        """
        Add downstream (CDH jira) number as a prefix.
        Since it triggers a commit, it will also add gerrit Change-Id to the commit.
        :return:
        """
        self.downstream_repo.rewrite_head_commit_message(prefix="{}: ".format(self.cdh_jira_id))

    def post_commit_actions(self):
        build_cmd = (
            "!! Remember to build project to verify the backported commit compiles !!"
            "Run this command to build the project: {}".format(
                "mvn clean install -Pdist -DskipTests -Pnoshade  -Dmaven.javadoc.skip=true"
            )
        )
        gerrit_push_cmd = (
            "Run this command to push to gerrit: "
            "git push cauldron HEAD:refs/for/{cdh_branch}%{reviewers}".format(
                cdh_branch=self.cdh_branch, reviewers=GERRIT_REVIEWER_LIST
            )
        )
        LOG.info(
            "Commit was successful! {build_cmd}\n{gerrit_cmd}".format(build_cmd=build_cmd, gerrit_cmd=gerrit_push_cmd)
        )
