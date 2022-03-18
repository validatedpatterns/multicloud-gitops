BOOTSTRAP=1

.PHONY: default
default: show

%:
	make -f common/Makefile $*

install: deploy
	make vault-init
	make load-secrets
	echo "Installed"
