# Subchart Update

When updating this sub-chart, please remember to tweak the image tag in values.yaml.
That is because we want to use -ubi images if possible and there is no suffix option, so
we just override the tag with the version + "-ubi"

## Steps

1. Edit the version in Chart.yaml
2. Run `helm dependency update .`
3. Run `./update-helm-dependency.sh`
4. Tweak `values.yaml` with the new image versions
5. Run `make test`
6. Commit to Git

## PRs

Please send PRs [here](https://github.com/validatedpatterns/common)
