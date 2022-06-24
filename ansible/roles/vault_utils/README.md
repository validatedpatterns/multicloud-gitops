Role Name
=========

Bunch of utilities to manage the vault inside k8s imperatively

Requirements
------------

ansible-galaxy collection install community.kubernetes

Role Variables
--------------



Dependencies
------------



Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    - hosts: servers
      roles:
         - { role: username.rolename, x: 42 }


Internals
---------
Here is the rough high-level algorithm used to unseal the vault:
1. Check vault status. If vault is not initialized go to 2. If initialized go to 3.
2. Initialize vault and store unseal keys + login token either on a local file
   or inside a secret in k8s (file_unseal var controls this)
3. Check vault status. If vault is unsealed go to 5. else to to 4.
4. Unseal the vault using the secrets read from the file or the secret
   (file_unseal controls this)
5. Configure the vault (should be idempotent)

License
-------

Apache

Author Information
------------------

