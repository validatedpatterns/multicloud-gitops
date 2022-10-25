# Subchart Update

When updating this sub-chart, please remember to tweak the image tag in values.yaml.
That is because we want to use -ubi images if possible and there is no suffix option, so
we just override the tag with the version + "-ubi"
