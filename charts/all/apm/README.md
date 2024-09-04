trino-hive-postgresql
   - secret/trino-hive-postgresql
   
   - service/trino-hive-postgresql
   
   - statefulset.apps/trino-hive-postgresql

trino-hive-metastore
   - secret/trino-hive-metastore
   
   - service/trino-hive-metastore
   - service/trino-hive-metastore-lb
   
   - deployment.apps/trino-hive-metastore

trino-common
   - configmap/trino-catalog
   - secret/trino-secrets

trino-worker
   - configmap/trino-worker-configs
   - configmap/trino-worker-schemas
   
   - deployment.apps/trino-worker

trino-coordinator
   - configmap/trino-coordinator-configs
   - configmap/trino-coordinator-schemas
   
   - secret/trino-coordinator-keystore
   - secret/trino-coordinator-keystore-p12
   
   - service/trino-coordinator
   - service/trino-coordinator-lb
   
   - deployment.apps/trino-coordinator

   - route.route.openshift.io/trino-coordinator




   oc get pods --field-selector=status.phase=Terminating -o name | xargs -I {} oc delete {} --force --grace-period=0
