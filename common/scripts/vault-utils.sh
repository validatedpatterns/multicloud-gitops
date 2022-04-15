#!/bin/sh

# Assumptions - vault in the demo will be running in non-HA mode so there will only be a vault-0
# vault will be running in the "vault" namespace

vault_delete()
{
	oc -n vault delete pod vault-0 &
	oc -n vault delete pvc data-vault-0 &
}

vault_ready_check()
{
#NAME                                   READY   STATUS    RESTARTS   AGE
#vault-0                                1/1     Running   0          44m
	oc get po -n vault | grep vault-0 | awk '{ print $2, $3 }' 2>/dev/null
}

get_vault_ready()
{
	rdy_output=`vault_ready_check`

	# Things we may have to wait for:
	#   being assigned to a host
	if [ "$?" ]; then
		sleep 5
		until [ "$rdy_output" ]
		do
			sleep 5
			rdy_output=`vault_ready_check`
		done
	fi

	printf "%s" "$rdy_output"
}

vault_unseal()
{
	# Argument is expected to be the text output of the vault operator init command which includes Unseal Keys
	# (5 by default) and a root token.
	if [ -n "$1" ]; then
		file=$1
	else
		file=common/vault.init
	fi

	for unseal in `cat $file | grep "Unseal Key" | awk '{ print $4 }'`
	do
		oc -n vault exec vault-0 -- vault operator unseal $unseal
	done

	vault_login $file
}

vault_init()
{
	# Argument is expected to be the text output of the vault operator init command which includes Unseal Keys
	# (5 by default) and a root token.
	if [ -n "$1" ]; then
		file=$1
	else
		file=common/vault.init
	fi

	if [ -f "$file" ] && grep -q -e '^Unseal' "$file"; then
		echo "$file already exists and contains seal secrets. We're moving it away to ${file}.bak"
		mv -vf "${file}" "${file}.bak"
	fi

	# The vault is ready to be initialized when it is "Running" but not "ready".  Unsealing it makes it ready
	rdy_check=`get_vault_ready`

	if [ "$rdy_check" = "1/1 Running" ]; then
		echo "Vault is already ready, exiting"
		exit 0
	fi

	until [ "$rdy_check" = "0/1 Running" ]
	do
		echo $rdy_check
		rdy_check=`get_vault_ready`
	done

	oc -n vault exec vault-0 -- vault operator init | tee $file

	vault_unseal $file
	vault_login $file

	vault_secrets_init $file
	vault_kubernetes_init $file
	vault_policy_init $file

	# Do not need pki init by default
	# But this is how you could call it if you need it
	#vault_pki_init $file
}

# Retrieves the root token specified in the file $1
vault_get_root_token()
{
	# Argument is expected to be the text output of the vault operator init command which includes Unseal Keys
	# (5 by default) and a root token.
	if [ -n "$1" ]; then
		file=$1
	else
		file=common/vault.init
	fi

	token=`grep "Initial Root Token" $file | awk '{ print $4 }'`
	printf "%s" "$token"
}

# Exec a vault command wrapped with the vault root token specified in the file
# $1
vault_token_exec()
{
	file="$1"
	token=`vault_get_root_token $file`
	shift
	cmd="$@"

	vault_exec $file "VAULT_TOKEN=$token $cmd"
}

vault_exec()
{
	file="$1"
	token=`vault_get_root_token $file`
	shift
	cmd="$@"

	oc -n vault exec -i vault-0 -- sh -c "$cmd"
}

vault_login()
{
	file="$1"
	token=`vault_get_root_token $file`
	shift
	cmd="$@"

	vault_exec $file "vault login $token"
}

oc_get_domain()
{
	oc get ingresses.config/cluster -o jsonpath={.spec.domain}
}

oc_get_pki_domain()
{
	printf "%s" `oc_get_domain | cut -d. -f3-`
}

oc_get_pki_role()
{
	pkidomain=`oc_get_pki_domain`
	certrole=`printf "%s" "$pkidomain" | sed 's|\.|_|g'`
	printf "%s" "$certrole"
}

vault_pki_init()
{
	file="$1"

	pkidomain=`oc_get_pki_domain`
	pkirole=`oc_get_pki_role`

	vault_exec $file "vault secrets enable pki"
	vault_exec $file "vault secrets tune --max-lease-ttl=8760h pki"
	vault_exec $file "vault write pki/root/generate/internal common_name=$pkidomain ttl=8760h"
	vault_exec $file 'vault write pki/config/urls issuing_certificates="http://127.0.0.1:8200/v1/pki/ca" crl_distribution_points="http://127.0.0.1:8200/v1/pki/crl"'
	vault_exec $file "vault write pki/roles/$pkirole allowed_domains=$pkidomain allow_subdomains=true max_ttl=8760h"
}

vault_kubernetes_init()
{
	file="$1"

	vault_exec $file "vault auth enable --path=hub kubernetes"
}

vault_policy_init()
{
	file="$1"

	k8s_host='https://$KUBERNETES_PORT_443_TCP_ADDR:443'
	secret_name="$(oc get -n golang-external-secrets serviceaccount golang-external-secrets -o jsonpath='{.secrets}' | jq -r '.[] | select(.name | test ("golang-external-secrets-token-")).name')"
	sa_token="$(oc get secret -n golang-external-secrets ${secret_name} -o go-template='{{ .data.token | base64decode }}')"

	vault_exec $file "vault write auth/hub/config token_reviewer_jwt=$sa_token kubernetes_host=$k8s_host kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt issuer=https://kubernetes.default.svc"
	vault_exec $file 'vault policy write hub-secret - << EOF
path "secret/data/hub/*"
  { capabilities = ["read"]
}
EOF
'
	vault_exec $file 'vault write auth/hub/role/hub-role bound_service_account_names="golang-external-secrets" bound_service_account_namespaces="golang-external-secrets" policies="default,hub-secret" ttl="15m"'
}

vault_secrets_init()
{
	file="$1"

	vault_exec $file "vault secrets enable -path=secret kv-v2"
}

vault_create_secret()
{
	file="$1"
	shift
	secret_path="$1"
	shift
	secret="$@"

	vault_exec $file "vault kv put $secret_path $secret"
}

$@
