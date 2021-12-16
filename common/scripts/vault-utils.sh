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
#vault-agent-injector-8d9cfcd47-skklw   1/1     Running   0          121m
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

	echo $rdy_output
}

vault_unseal()
{
	for unseal in `cat $1 | grep "Unseal Key" | awk '{ print $4 }'`
	do
		oc -n vault exec vault-0 -- vault operator unseal $unseal
	done
}

vault_init()
{
	if [ -n "$1" ]; then
		file=$1
	else
		file=common/vault.init
	fi

	rdy_check=`get_vault_ready`
	until [ "$rdy_check" = "0/1 Running" ]
	do
		echo $rdy_check
		rdy_check=`get_vault_ready`
	done

	oc -n vault exec vault-0 -- vault operator init | tee $file
	vault_unseal $file
}

$@
