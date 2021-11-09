BOOTSTRAP=1
SECRETS=~/values-secret.yaml
NAME=$(shell basename `pwd`)
TARGET_REPO=$(shell git remote show origin | grep Push | sed -e 's/.*URL://' -e 's%:[a-z].*@%@%' -e 's%:%/%' -e 's%git@%https://%' )
# git branch --show-current is also available as of git 2.22, but we will use this for compatibility
TARGET_BRANCH=$(shell git rev-parse --abbrev-ref HEAD)

#  Makefiles that use this target must provide:
#  	PATTERN: The name of the pattern that is using it.  This will be used programmatically for the source namespace
#  	TARGET_NAMESPACE: target namespace to install the secret into
#  	COMPONENT: The component of the target namespace.  In industrial edge, factory or datacenter - and for the secret
#  		it needs to be datacenter because that's where the CI components run.
#  	SECRET_NAME: The name of the secret to manage
argosecret:
	PATTERN="$(PATTERN)" TARGET_NAMESPACE="$(TARGET_NAMESPACE)" COMPONENT="$(COMPONENT)" SECRET_NAME="$(SECRET_NAME)" common/scripts/secret.sh

#  Makefiles in the individual patterns should call these targets explicitly
#  e.g. from industrial-edge: make -f common/Makefile show
show:
	helm template common/install/ --name-template $(NAME) --set main.git.repoURL="$(TARGET_REPO)" --set main.git.revision=$(TARGET_BRANCH) --set main.options.bootstrap=$(BOOTSTRAP) -f $(SECRETS)

init:
	git submodule update --init --recursive

deploy:
	helm install $(NAME) common/install/ --set main.git.repoURL="$(TARGET_REPO)" --set main.git.revision=$(TARGET_BRANCH) --set main.options.bootstrap=$(BOOTSTRAP) -f $(SECRETS)

upgrade:
	helm upgrade $(NAME) common/install/ --set main.git.repoURL="$(TARGET_REPO)" --set main.git.revision=$(TARGET_BRANCH) --set main.options.bootstrap=$(BOOTSTRAP) -f $(SECRETS)

uninstall:
	helm uninstall $(NAME)

.phony: install
