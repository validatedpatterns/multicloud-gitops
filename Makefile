BOOTSTRAP=1
SECRETS=~/values-secret.yaml
NAME=$(shell basename `pwd`)
TARGET_REPO=$(shell git remote show origin | grep Push | sed -e 's/.*URL://' -e 's%:[a-z].*@%@%' -e 's%:%/%' -e 's%git@%https://%' )
TARGET_BRANCH=$(shell git branch --show-current)

# This is to eliminate the need to install and worry about a separate shell script somewhere in the directory structure
# There's a lot of GNU Make magic happening here:
#  .ONESHELL passes the whole task into a single shell instance
#  $$ is a Makefile idiom to preserve the single $ otherwise make consumes them
#  tabs are necessary
#  The patch to oc apply uses JSON because it's not as sensitive to indentation and doesn't need heredoc
#  
#  Makefiles that use this target must provide:
#  	PATTERN: The name of the pattern that is using it.  This will be used programmatically for the source namespace
#  	TARGET_NAMESPACE: target namespace to install the secret into
#  	COMPONENT: The component of the target namespace.  In industrial edge, factory or datacenter - and for the secret
#  		it needs to be datacenter because that's where the CI components run.
.ONESHELL:
SHELL = bash
argosecret:
	pattern=$(PATTERN)
	target_ns=$(TARGET_NAMESPACE)
	src_ns="$(PATTERN)-$(COMPONENT)"
	component=$(COMPONENT)
	passwd_resource="secrets/$(COMPONENT)-gitops-cluster"
	secret_name='argocd-env'
	ns=0
	gitops=0

	# Check for Namespaces and Secrets to be ready (it takes the cluster a while to deploy them)
	while : ; do
		echo -n "Checking for namespace $$target_ns to exist..."
		if [ oc get namespace $$target_ns >/dev/null 2>/dev/null ]; then
			echo "not yet"
			ns=0
			sleep 2
			continue
		else
			echo "OK"
			ns=1
		fi

		echo -n "Checking for $$passwd_resource to be populated in $$src_ns..."
		pw=`oc -n $$src_ns extract $$passwd_resource --to=- 2>/dev/null`
		if [ "$$?" == 0 ] && [ -n "$$pw" ]; then
			echo "OK"
			gitops=1
		else
			echo "not yet"
			gitops=0
			sleep 2
			continue
		fi

		echo "Conditions met, managing secret $$secret_name in $$target_ns"
		break
	done

	user=$$(echo admin | base64)
	password=$$(echo $$pw | base64)

	echo "{ \"apiVersion\": \"v1\", \"kind\": \"Secret\", \"metadata\": { \"name\": \"$$secret_name\", \"namespace\": \"$$target_ns\" }, \"data\": { \"ARGOCD_PASSWORD\": \"$$password\", \"ARGOCD_USERNAME\": \"$$user\" }, \"type\": \"Opaque\" }" | oc apply -f-

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
