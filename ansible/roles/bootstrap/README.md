# Ansible Role: bootstrap

This is the bootstrap role to deploy the MultiCloud-GitOps pattern.  This role contains all the imperative tasks that are needed to deploy the MultiCloud-GitOps validated pattern onto an OpenShift cluster.
The main purpose of this role is for RHPDS to deploy this pattern by calling our ansible/site.yaml playbook which in turn calls our bootstrap role.  In the same vein a user can execute the following from the command-line to deploy
the validated pattern:

$ ansible-playbook ansible/site.yaml

## Requirements

* Pre-deployed Openshift or Kubernetes Cluster
* Must be Cluster Admin to successfully execute this role.
* There are a few tools that you will need to run this role which are listed below.

| Tool | Description | Download link |
| ----------- | ----------- | ----------- |
| kubernetes.core | The collection includes a variety of Ansible content to help automate the management of applications in Kubernetes and OpenShift clusters, as well as the provisioning and maintenance of clusters themselves | **ansible-galaxy collection install kubernetes.core** |
| Kubernetes Python Cli | The kubernetes.core collection requires the Kubernetes Python client to interact with Kubernetes' APIs. | **pip3 install kubernetes** |
| Python 3 | Python2 is deprecated from 1st January 2020. Please switch to Python3. | RHEL: <br> **yum -y install rh-python36** |

## Bootstrap Role tasks that will be executed

The bootstrap-industrial-edge role will execute on your localhost.  The high level tasks that are executed are listed below.

```sh
playbook: ansible/site.yaml

  play #1 (localhost): MultiCloud-GitOps bootstrap  TAGS: []
    tasks:
      bootstrap : {{ role_name }}: Getting pattern information  TAGS: []
      bootstrap : {{ role_name }}: debug  TAGS: []
      bootstrap : {{ role_name }}: Deploying Helm Charts  TAGS: []
      bootstrap : {{ role_name }}: Initialize Vault  TAGS: []
      bootstrap : {{ role_name }}: Load Secrets to Vault  TAGS: []
```

### Task: Getting pattern information

This task gathers the validated pattern information.  This information will be used by the validated pattern framework and passed to ArgoCD to support the validated pattern deployment.  The task sets up the following facts for other tasks to use:

* secrets_file
* globals_file
* bootstrap
* target_branch
* target_repo
* hubcluster_apps_domain

### Task: Deploying Helm Charts

Our validated pattern framework makes use of Helm Charts to deploy supporting components for the MultiCloud-GitOps application workload. There are two Helm charts that get installed for the validated pattern which are described in the table below.

| Chart | Description | Location |
| ----- | ----- | ----- |
| multicloud-gitops | A Helm chart to build and deploy the validated pattern | multicloud-gitops/common/install |

### Task: Initialize Vault

In the MultiCloud-GitOps validated pattern we have included Vault as our secrets management tool. Secret management is essential for cloud native solutions and as usual it is ignored until the very end of the software development cycle.  Our Red Hat validated patterns make use of the HashiCorp vault technology to store passwords, private keys, and API credentials used by the applications workloads.

This task initializes the Vault environment.

### Task: Load Secrets to Vault

The MultiCloud-GitOps validated pattern application makes use of secrets that are stored in the Vault environment.  This task is an imperative task that loads the secrets defined in the values-secret.yaml file which are specific to the Validated Pattern application workloads.

## Role Variables

Most of the variables will be dynamically set for you in this role. Variables that we will be looking for are:

| Variable | Description | Default Value |
| --------- | ---------- | ---------- |
| pattern_repo_dir:  | Pattern directory.  We assume that you start the execution of the ansile role in the pattern working cloned directory. |  "{{ lookup('env', 'PWD') }}" |
| argo_target_namespace: | Target namespace for ArgoCD |manuela-ci |
| pattern: | Name of the validated pattern | industrial-edge |
| component: | Name of the component to deploy |datacenter |
| values_secret: | Location of the values-secret.yaml file | "{{ lookup('env', 'HOME') }}/values-secret.yaml" |
| values_global: | Location of the values-global.yaml file | "{{ pattern_repo_dir }}/values-secret.yaml" |
| kubeconfig: | Environment variable for KUBECONFIG | "{{ lookup('env', 'KUBECONFIG') }}"|
| vault_init_file: | Init Vault file which will contain Vault tokens etc | "{{ pattern_repo_dir }}/common/pattern-vault.init"|
| vault_ns: | Namespace for Vault | "vault"|
| vault_pod: | Name of the initial Vault pod | "vault-0"|
| vault_path: | Path to the Vault secrets for the Hub | "secret/hub"|
| debug: | Whether or not to display debug info | False |

> NOTE: The role is designed to use the current *git* branch that you are working on. It is also designed to derive the variables values using your environment.

## Dependencies

None

## Site.yaml Playbook

The initial playbook can be found under ansible/site.yaml and will execute the bootstrap role.

```yaml
- name: Validated Pattern Bootstrap
  hosts: localhost
  connection: local
  roles:
    - bootstrap
```

To start the execution of the role execute the following:

```sh
$ pwd
/home/claudiol/work/blueprints-space/multicloud-gitops
$ ansible-playbook ansible/site.yaml
```

License
-------

BSD

Author Information
------------------

Lester Claudio (claudiol@redhat.com) <br>
Jonathan Rickard (jrickard@redhat.com)<br>
Michele Baldessari (mbaldess@redhat.com)<br>
Martin Jackson (mhjacks@redhat.com)
