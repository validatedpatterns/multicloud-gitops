BOOTSTRAP=1

.PHONY: default
default: show

%:
	make -f common/Makefile $*

install: deploy
	echo "Installed"
