# Validated Patterns common/ repository

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Start Here

This repository is never used as standalone. It is usually imported in each pattern as a subtree.
In order to import the common/ the very first time you can use
`https://github.com/hybrid-cloud-patterns/multicloud-gitops/blob/main/common/scripts/make_common_subtree.sh`

In order to update your common subtree inside your pattern repository you can either use
`https://github.com/hybrid-cloud-patterns/utilities/blob/main/scripts/update-common-everywhere.sh` or
do it manually by doing the following:

```sh
git remote add -f upstream-common https://github.com/hybrid-cloud-patterns/common.git
git merge -s subtree -Xtheirs -Xsubtree=common upstream-common/ha-vault
```
