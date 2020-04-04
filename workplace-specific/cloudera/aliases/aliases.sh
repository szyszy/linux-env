#!/bin/bash

#setup locations
CLOUDERA_DEV_ROOT="$HOME/development/cloudera/"
CLOUDERA_HADOOP_ROOT="$CLOUDERA_DEV_ROOT/hadoop/"
HADOOP_MVN_DIR="$HOME/development/apache/hadoop-maven/"
HADOOP_DEV_DIR="$HOME/development/apache/hadoop/"

CLOUDERA_DIR="$HOME_LINUXENV_DIR/workplace-specific/cloudera/"
export CLOUDERA_DIR

#goto aliases
alias goto-cldr="cd $CLOUDERA_DEV_ROOT"
alias goto-cldr-hadoop="cd $CLOUDERA_HADOOP_ROOT"
alias goto-tasks="cd $HOME/Google Drive File Stream/My Drive/development/tasks/"
alias goto-hadoop="cd $HADOOP_DEV_DIR"
alias goto-hadoop-mvn="cd $HADOOP_MVN_DIR"
alias goto-hadoop-commit="cd $HOME/development/apache/hadoop-commit"
alias goto-systest="cd $CLOUDERA_DEV_ROOT/qe-cmf/systest"
alias goto-cmf="cd $CLOUDERA_DEV_ROOT/cmf"
alias goto-yarn-tasks="cd $HOME/yarn-tasks"

#git specific commands
alias gerrit-branches5="git br -r | grep gerrit | grep -e '5.1\d.*' | cut -d_ -f 2-3 | sort -u | grep -v patch"
alias git-rebase-trunk="git co trunk && echo 'Pulling origin/trunk...' && git pull && git co - && git rebase trunk"

alias j7='export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk1.7.0_80.jdk/Contents/Home'
alias j8='export JAVA_HOME=/Library/Java//JavaVirtualMachines/jdk1.8.0_151.jdk/Contents/Home'

#YARN-related commands
alias upstream-gergo="git log --grep grepas --grep 'Gergo Repas' --oneline  | wc -l"

alias upstream-all-count="git log --grep snemeth --grep Szilard --grep 'Szilard Nemeth' --oneline | grep 'YARN\|SUBMARINE\|HADOOP' | wc -l"
alias upstream-all="git log --grep snemeth --grep Szilard --grep 'Szilard Nemeth' --oneline | grep 'YARN\|SUBMARINE\|HADOOP'"
alias upstream-hadoop="git log --grep snemeth --grep Szilard --grep 'Szilard Nemeth' --oneline | wc -l"
alias upstream-committed="git log --author="snemeth@apache.org" --oneline | wc -l"
alias upstream-yarn2="echo $(($(git log --grep snemeth --grep Szilard --grep 'Szilard Nemeth' --oneline | grep YARN | wc -l | tr -s ' ' | cut -d ' ' -f2) + $(git log --author=snemeth --oneline | wc -l | tr -s ' ' | cut -d ' ' -f2)))"


alias grind-yarn="export GRIND_MAVEN_FLAGS=-Dmaven-dependency-plugin.version=2.10 && \
rm -rf ~/development/cloudera/dist_test/env/.grind/cache/ && \
goto-hadoop-mvn && \
mvn clean install -DskipTests -Dmaven.javadoc.skip=true && \
cd hadoop-yarn-project && \
grind --verbose test --java-version 8"

alias grind-yarn-exceptions="grind --verbose test --java-version 8 \
 -e TestHBaseStorageFlowActivity \
 -e TestHBaseStorageFlowRun \
 -e TestHBaseStorageFlowRunCompaction \
 -e TestHBaseTimelineStorageApps \
 -e TestHBaseTimelineStorageDomain \
 -e TestHBaseTimelineStorageEntities \
 -e TestHBaseTimelineStorageSchema"

alias run-findbugs="mvn clean install -DskipTests && mvn findbugs:findbugs && mvn findbugs:gui"

alias mvn-hadoop-patch="mvn -Ptest-patch clean site site:stage"
alias cluster-roulette="$HOME/Downloads/scripts/cluster-roulette.sh"