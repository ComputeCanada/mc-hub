# Cluster lifecycle

Clusters whose initial plan has never been applied use the same undeployed lifecycle as torn-down clusters. Both offer **Save configuration**, **Review build plan** when a plan is ready (otherwise **Rebuild**), and **Destroy cluster**. Saving invalidates the pending plan without starting a run; rebuild generates a fresh plan from the saved configuration. Applying a build leaves the undeployed lifecycle. Expiration skips undeployed clusters, including those with a pending plan. Existing initial plans are recognized on status refresh after verifying that their workspace has no Terraform state.

Deployed clusters offer **Tear down**. Review and apply the Terraform destroy plan to remove the deployed resources and their data. The cluster remains in the list as **Not deployed**, with its saved configuration, ownership, active GitHub repository, and Terraform workspace. Expiration performs this same teardown automatically. Busy clusters are retried on a later expiration sweep; undeployed clusters are skipped.

An undeployed cluster offers **Rebuild** and **Destroy cluster**. Saving configuration does not start a run. Rebuild writes the saved variables and creates a fresh plan using the existing repository and workspace, retaining the pinned Magic Castle version. Set a future expiration date or clear the date before rebuilding. Review the plan before applying it. Deleted data is not restored; connection details can change. The hostname and cloud project stay fixed so the existing integrations remain valid.

Destroy removes only an empty cluster definition. The backend checks all pages of workspace runs and verifies that no managed resource instances remain, then discards eligible pending plans and waits for confirmation. It locks the workspace and rechecks runs and resources before deletion. Active planning or applying runs block deletion; they are not canceled. Failed checks retain the cluster and release any lock acquired by this operation. Successful destruction archives the repository, tags the workspace `deleted`, leaves that workspace locked, and removes the cluster record. Neither the repository nor the workspace is permanently deleted. Clusters that failed before workspace creation can also be removed after teardown.

## API changes

- `POST /api/magic-castles/<hostname>/teardown`: create a destroy plan (202), or transition directly to `not_deployed` when there is no Terraform state/workspace. Apply planned teardown using the existing `/apply` endpoint.
- `POST /api/magic-castles/<hostname>/rebuild`: create a fresh build plan for a retained cluster (202).
- `PUT /api/magic-castles/<hostname>`: save configuration without a run when `undeployed` is true.
- `DELETE /api/magic-castles/<hostname>`: remove a verified empty cluster (204). This no longer starts resource teardown.
- Cluster responses include `undeployed`; `not_deployed` is a new durable status. Build planning can temporarily change the status while `undeployed` remains true until apply starts.

Apply database migration `0006` before running the updated application. It adds `undeployed` and `deployment_started_at`; existing clusters retain their current status and creation date. Rebuild provisioning timeouts use the new deployment start time.
