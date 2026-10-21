# Terraform Cloud agent availability

For projects with a configured agent pool, the hub checks Terraform Cloud before
accepting a user's cluster creation, modification, apply, teardown, rebuild, or
plan retry request. The pool name comes from `agent_pool_name` on the operator's
`openstack_clouds` entry matching the project's `OS_AUTH_URL`, as it does when
configuring the Terraform Cloud project.

Projects without a configured pool skip this check without making any Terraform
Cloud requests. The hub does not read remote execution settings; this assumes
settings are managed through the hub and are not changed directly in Terraform
Cloud.

For agent execution, at least one agent in the pool must report `idle` or `busy`.
A busy agent is healthy and can process queued work. Empty pools and pools
containing only `unknown`, `errored`, or `exited` agents block the request.
The check reads individual agents across all pages; the pool's agent count also
includes unknown agents and is not a health check.

Rejections return HTTP 503 with a message displayed by the hub's existing error
dialog. They happen before starting a background task or changing cluster state.
For projects with a configured pool, if Terraform Cloud cannot be reached, denies
access, or returns an unrecognized response, the hub also blocks the request and
asks the user to retry or contact an administrator. The hub's Terraform API token
needs read access to agent pools and the selected pool's agents.

The background-worker supervisor runs an agent health monitor even when nobody
has the hub open. It checks each distinct configured pool once every five minutes
when healthy, or every 30 seconds when unavailable or unverifiable. Pools shared
by several clouds or projects are checked once per interval. Snapshots are stored
in the shared database, scoped to the Terraform Cloud organization and pool name.

The editor and build/teardown confirmation dialogs read this cached availability
before enabling Apply or confirmation. They show a warning when the agent is
unavailable or its availability cannot be verified. The browser refreshes the
cached result every five minutes when healthy and every 30 seconds otherwise;
these requests do not contact Terraform Cloud. Missing snapshots or snapshots
older than 11 minutes block Apply, including if the health worker has stopped.
Controls are also disabled during the initial check. Changing the selected
project resets the check, and responses from the previous project are ignored.
Planning and benchmark definition editors do not require a live agent.

The read-only `GET /api/projects/<id>/agent-availability` endpoint requires project
membership and returns `available` and `message`. Projects without a configured
pool return available without reading a snapshot or contacting Terraform Cloud.

The server also checks live availability on each operation request, so stale UI
status cannot bypass the guard. Recovery requires no hub restart. Viewing clusters,
discarding teardown plans, and deleting empty clusters remain available.
Expiration and capacity end-of-period cleanup use the same cached and live agent
checks, plus monitored GitHub and Terraform Cloud service status. Cleanup is deferred before planning or applying
when a dependency reports an outage or its health is unverifiable. See
[cluster lifecycle](cluster-lifecycle.md) for retry behavior. Both run in the
shared cleanup worker. Scheduled cluster creation is unchanged.

## Operator notifications and deployment

Apply migration `0025` with the deployment's normal `flask db upgrade` step, and
restart the API and background-worker supervisor. Run only one supervisor per
shared database volume, as with the other scheduled workers.

Configure operator Slack/webhook destinations through the existing global
[`notification_destinations`](configuration.md) setting. The monitor queues:

- `agent_pool.unavailable` when no healthy agent remains (including the first
  observation if the pool is already down).
- `agent_pool.check_failed` when the Terraform API cannot verify availability.
  This is not reported as a confirmed agent outage.
- `agent_pool.recovered` when a previously unavailable or unverified pool is healthy.

Events include the organization, pool name, status, and summary. Initial healthy
observations are silent. Repeated observations of the same state do not enqueue
another notification; this deduplication survives worker restarts. Notifications
and snapshot changes commit together, and the existing notification worker
delivers/retries them. No notifications are sent unless a destination is configured.
Project-specific capacity notification destinations do not receive these events.
The monitor cannot report its own failure while stopped; stale UI status still
blocks Apply, and supervisor failures are available in the worker logs.

This is a preflight check, not a guarantee that the agent will stay online:
Terraform Cloud may take time to report an outage, and an agent can fail after
the request is accepted.

References: [agent status definitions](https://developer.hashicorp.com/terraform/cloud-docs/agents/agent-pools)
and [agents API](https://developer.hashicorp.com/terraform/cloud-docs/api-docs/agents).
