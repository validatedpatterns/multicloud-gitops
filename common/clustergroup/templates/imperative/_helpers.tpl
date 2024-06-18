# Pseudo-code
# 1. Get the pattern's CR
# 2. If there is a secret called vp-private-repo-credentials in the current namespace, fetch it
# 3. If it is an http secret, generate the correct URL
# 4. If it is an ssh secret, create the private ssh key and make sure the git clone works

{{/* fetch-ca InitContainer */}}
{{- define "imperative.initcontainers.fetch-ca" }}
- name: fetch-ca
  image: {{ $.Values.clusterGroup.imperative.image }}
  imagePullPolicy: {{ $.Values.clusterGroup.imperative.imagePullPolicy }}
  env:
    - name: HOME
      value: /git/home
  command:
  - 'sh'
  - '-c'
  - >-
    cat /var/run/kube-root-ca/ca.crt /var/run/trusted-ca/ca-bundle.crt /var/run/trusted-hub/hub-kube-root-ca.crt > /tmp/ca-bundles/ca-bundle.crt || true;
    ls -l /tmp/ca-bundles/
  volumeMounts:
  - mountPath: /var/run/kube-root-ca
    name: kube-root-ca
  - mountPath: /var/run/trusted-ca
    name: trusted-ca-bundle
  - mountPath: /var/run/trusted-hub
    name: trusted-hub-bundle
  - mountPath: /tmp/ca-bundles
    name: ca-bundles
{{- end }}

{{/* git-init-ca InitContainer */}}
{{- define "imperative.initcontainers.gitinit-ca" }}
- name: git-init
  image: {{ $.Values.clusterGroup.imperative.image }}
  imagePullPolicy: {{ $.Values.clusterGroup.imperative.imagePullPolicy }}
  env:
    - name: HOME
      value: /git/home
  volumeMounts:
  - name: git
    mountPath: "/git"
  - name: ca-bundles
    mountPath: /etc/pki/tls/certs
  command:
  - 'sh'
  - '-c'
  - >-
    if ! oc get secrets -n openshift-gitops vp-private-repo-credentials &> /dev/null; then
      URL="{{ $.Values.global.repoURL }}";
    else
      if ! oc get secrets -n openshift-gitops vp-private-repo-credentials -o go-template='{{ `{{index .data.sshPrivateKey | base64decode}}` }}' &>/dev/null; then
        U="$(oc get secret -n openshift-gitops vp-private-repo-credentials -o go-template='{{ `{{index .data.username | base64decode }}` }}')";
        P="$(oc get secret -n openshift-gitops vp-private-repo-credentials -o go-template='{{ `{{index .data.password | base64decode }}` }}')";
        URL=$(echo {{ $.Values.global.repoURL }} | sed -E "s/(https?:\/\/)/\1${U}:${P}@/");
      else
        S="$(oc get secret -n openshift-gitops vp-private-repo-credentials -o go-template='{{ `{{index .data.sshPrivateKey | base64decode }}` }}')";
        mkdir -p --mode 0700 "${HOME}/.ssh";
        echo "${S}" > "${HOME}/.ssh/id_rsa";
        chmod 0600 "${HOME}/.ssh/id_rsa";
        URL=$(echo {{ $.Values.global.repoURL }} | sed -E "s/(https?:\/\/)/\1git@/");
        git config --global core.sshCommand "ssh -i "${HOME}/.ssh/id_rsa" -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no";
      fi;
    fi;
    OUT="$(oc get proxy.config.openshift.io/cluster -o jsonpath='{.spec.httpProxy}' 2>/dev/null)";
    if [ -n "${OUT}" ]; then export HTTP_PROXY="${OUT}"; fi;
    OUT="$(oc get proxy.config.openshift.io/cluster -o jsonpath='{.spec.httpsProxy}' 2>/dev/null)";
    if [ -n "${OUT}" ]; then export HTTPS_PROXY="${OUT}"; fi;
    OUT="$(oc get proxy.config.openshift.io/cluster -o jsonpath='{.spec.noProxy}' 2>/dev/null)";
    if [ -n "${OUT}" ]; then export NO_PROXY="${OUT}"; fi;
    if [ "{{ $.Values.global.targetRevision }}" = "HEAD" ]; then BRANCH=""; else BRANCH="--branch {{ $.Values.global.targetRevision }}"; fi;
    mkdir /git/{repo,home};
    git clone --recurse-submodules --single-branch ${BRANCH} --depth 1 -- "${URL}" /git/repo;
    chmod 0770 /git/{repo,home};
{{- end }}
{{/* Final done container */}}
{{- define "imperative.containers.done" }}
- name: "done"
  image: {{ $.Values.clusterGroup.imperative.image }}
  imagePullPolicy: {{ $.Values.clusterGroup.imperative.imagePullPolicy }}
  command:
    - 'sh'
    - '-c'
    - 'echo'
    - 'done'
    - '\n'
{{- end }}

{{/* volume-mounts for all containers */}}
{{- define "imperative.volumemounts_ca" }}
- name: git
  mountPath: "/git"
- name: values-volume
  mountPath: /values/values.yaml
  subPath: values.yaml
- mountPath: /var/run/kube-root-ca
  name: kube-root-ca
- mountPath: /var/run/trusted-ca
  name: trusted-ca-bundle
- mountPath: /var/run/trusted-hub
  name: trusted-hub-bundle
- mountPath: /tmp/ca-bundles
  name: ca-bundles
{{- end }}

{{- define "imperative.volumes_ca" }}
- name: git
  emptyDir: {}
- name: values-volume
  configMap:
    name: {{ $.Values.clusterGroup.imperative.valuesConfigMap }}-{{ $.Values.clusterGroup.name }}
- configMap:
    name: kube-root-ca.crt
  name: kube-root-ca
- configMap:
    name: trusted-ca-bundle
    optional: true
  name: trusted-ca-bundle
- configMap:
    name: trusted-hub-bundle
    optional: true
  name: trusted-hub-bundle
- name: ca-bundles
  emptyDir: {}
{{- end }}
