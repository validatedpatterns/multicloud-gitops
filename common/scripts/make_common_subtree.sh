#!/bin/sh

if [ "$1" = "-h" ]; then
	echo "This script will convert common into a subtree and add a remote to help manage it."
	echo "The script takes three positional arguments, as follows:"
	echo
	echo "$0 <subtree_repo> <subtree_branch> <subtree_remote_name>"
	echo
	echo "Run without arguments, the script would run as if these arguments had been passed:"
	echo "$0 https://github.com/hybrid-cloud-patterns/common.git main common-subtree"
	echo
	echo "Please ensure the git subtree command is available. On RHEL/Fedora, the git subtree command"
	echo "is in a separate package called git-subtree"
	exit 1
fi

if [ -f '/etc/redhat-release' ]; then
  rpm -qa | grep git-subtree 2>&1
  if [ ! $? = 0 ]; then
    echo "you need to install git-subtree"
    echo "would you like to install it now?"
    select ANS in yes no
    do
      case $ANS in
        yes)
          sudo dnf install git-subtree -y
          break
          ;;
        no)
          exit
          break
          ;;
        *)
          echo "You must enter yes or no"
          ;;
      esac
    done
  fi
fi

if [ "$1" ]; then
	subtree_repo=$1
else
	subtree_repo=https://github.com/hybrid-cloud-patterns/common.git
fi

if [ "$2" ]; then
	subtree_branch=$2
else
	subtree_branch=main
fi

if [ "$3" ]; then
	subtree_remote=$3
else
	subtree_remote=common-subtree
fi

git diff --quiet || (echo "This script must be run on a clean working tree" && exit 1)

echo "Changing directory to project root"
cd `git rev-parse --show-toplevel`

echo "Removing existing common and replacing it with subtree from $subtree_repo $subtree_remote"
rm -rf common

echo "Committing removal of common"
(git add -A :/ && git commit -m "Removed previous version of common to convert to subtree from $subtree_repo $subtree_branch") || exit 1

echo "Adding (possibly replacing) subtree remote $subtree_remote"
git remote rm "$subtree_remote"
git remote add -f "$subtree_remote" "$subtree_repo" || exit 1
git subtree add --prefix=common "$subtree_remote" "$subtree_branch" || exit 1

echo "Complete.  You may now push these results if you are satisfied"
exit 0
