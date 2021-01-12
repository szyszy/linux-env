#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
#cd $DIR

## LINUX-ENV ALIASES
alias linuxenv-reload="$LINUX_ENV_REPO/setup-env.sh"
alias linuxenv-todos="grep '#TODO' -r $LINUX_ENV_REPO"
alias linuxenv-debug-on="echo \"enabled\" > ${ENV_DEBUG_SETUP_FILE}"
alias linuxenv-debug-off="echo \"disabled\" > ${ENV_DEBUG_SETUP_FILE}"
alias linuxenv-edit="subl ~/development/my-repos/linux-env/"

## KNOWLEDGE BASE
alias knowledgebase-edit="subl ~/development/my-repos/knowledge-base"
alias knowledgebase-private-edit="subl ~/development/my-repos/knowledge-base-private"


## GOTO ALIASES
alias goto-linuxenv-repo="cd $LINUX_ENV_REPO"
alias goto-kb-repo="cd $KB_REPO"
alias goto-kb-private-repo="cd $KB_PRIVATE_REPO"


## GIT ALIASES
alias git-commits-above-master="git log --oneline HEAD ^master | wc -l"
alias git-mybranches="git branch | grep 'own-'"
alias git-commit-msg="git log -n 1 --pretty=format:%s"
alias git-remove-trailing-ws="git diff-tree --no-commit-id --name-only -r HEAD | xargs sed -i 's/[[:space:]]*$//'"
#alias git-save-all-commits="git format-patch $(git rev-list --max-parents=0 HEAD)..HEAD -o /tmp/patches"

#https://stackoverflow.com/a/40884093/1106893 --> 4b825dc642cb6eb9a060e54bf8d69288fbee4904 is the id of the "empty tree"
alias git-save-all-commits="rm /tmp/patches/*; git format-patch 4b825dc642cb6eb9a060e54bf8d69288fbee4904..HEAD -o /tmp/patches"


## OTHER ALIASES
alias rm='safe-rm'
alias currentweek="date +%V"
alias vpn-szyszy="sudo openvpn --client --config ~/openvpn-szyszy/client.ovpn --ca ~/openvpn-szyszy/ca.crt"
alias date-formatted="date +%Y%m%d_%H_%M_%S"
alias sl="sl --help" # steam-locomotive: https://www.cyberciti.biz/tips/displays-animations-when-accidentally-you-type-sl-instead-of-ls.html
alias grep='grep --color=auto'
alias dfh='df -h'
alias bashrc='vim ~/.bashrc'
alias logs="find /var/log -type f -exec file {} \; | grep 'text' | cut -d' ' -f1 | sed -e's/:$//g' | grep -v '[0-9]$' | xargs tail -f"
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'

## ls ALIASES
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

#colorls
alias lc='colorls -lA --sd'

##Aliases for my DEV projects
alias save-tabs-android="python3 /Users/szilardnemeth/development/my-repos/google-chrome-toolkit/googlechrometoolkit/save_open_tabs_android.py"


## OTHER ALIASES
# Add an "alert" alias for long running commands.  Use like so:
# sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'
eval $(thefuck --alias)
alias mc='LANG=en_EN.UTF-8 mc'

#TODO create alias: resync all changes from linuxenv repo (copies all files)
#TODO make this a function
alias zip-files="sudo find / -iname *1564501696813_0001_01_000001* -print0 | sudo tar -czvf backup-1564501696813_0001-20190730.tar.gz --null -T -"

#https://stackoverflow.com/a/49752003/1106893
alias zsh-printcolors="for code in {000..255}; do print -P -- "$code: %F{$code}Color%f"; done"


###WHITESPACE PIPE TRICK: https://superuser.com/a/1503113
# SP  ' '  0x20 = · U+00B7 Middle Dot
# TAB '\t' 0x09 = ￫ U+FFEB Halfwidth Rightwards Arrow
# CR  '\r' 0x0D = § U+00A7 Section Sign (⏎ U+23CE also works fine)
# LF  '\n' 0x0A = ¶ U+00B6 Pilcrow Sign (was "Paragraph Sign")
alias whitespace="sed 's/ /·/g;s/\t/￫/g;s/\r/§/g;s/$/¶/g'"