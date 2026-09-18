# Service adoption statistics

Hub admins can open **Service adoption** from the account menu (`/usage`). Both the
page and `GET /api/usage` restrict access to hub admins; project administration does
not grant access. The existing local/no-auth mode treats its local user as an admin.
The service token does not grant access to reports.

The deployment runs two long-lived containers:

- `api` serves HTTP through Gunicorn, with no scheduled worker subprocesses.
- `background-worker` supervises the usage observer and expiration worker as
  separate processes. Both use Flask application contexts and shared lifecycle
  code with direct database access; neither calls the hub's HTTP API.

Compose also runs a one-time `initialize` container for database migrations,
startup status cleanup, and cluster initialization. Both long-lived containers
wait for it to succeed. All three use the same configuration, database volume,
and cluster storage. Initialization is not repeated on ordinary web or worker
container restarts.

For an existing deployment, stop its containers before initialization so database
migrations and startup status cleanup do not race with live operations:

```sh
docker compose down --remove-orphans
docker compose up -d --build --remove-orphans
```

These commands retain the named database volume. Do not add `--volumes` to `down`.
They also remove the former standalone `cleanup` container. Migration `0011` is
required for usage history and is applied by initialization.

The supervisor restarts an exited child independently, with retry delays from one
to 60 seconds, and stops both children on SIGTERM/SIGINT. Compose restarts the
supervisor container unless it was explicitly stopped. A file lock on the shared
database volume prevents two supervisors from running against that volume. Run
only one background-worker container per hub. Errors and worker restarts are
visible in `docker compose logs background-worker`.

For development or custom deployments, initialize the database first, then run
`python -m mchub.services.background_worker` alongside the web server with the same
configuration, writable database directory, and cluster storage. Custom web and
worker containers must share those mounts. The production web image alone no longer
starts scheduled tasks. The old Gunicorn configuration module remains importable
for compatibility but does not start workers. `MCHUB_HOST`, `MCHUB_PORT`, and the
service token are no longer used by cleanup.

Expiration sweeps run hourly. They share the API's atomic task claims, validation,
teardown and apply functions, skip busy/undeployed clusters, and verify the exact
destroy run before applying. Interrupted expiration claims are reconciled when the
expiration process restarts; claims owned by HTTP workers are left untouched.
External Terraform operations can continue during a process restart and are
reconciled from their remote state. Planning has a five-minute polling deadline;
remote request latency can extend it.

The observer refreshes clusters and then waits 30 seconds between sweeps. Slow
remote requests and outages can delay observations. The dashboard shows the last
completed sweep and warns when it is over three minutes old. Observer errors are
logged; a sweep timestamp does not guarantee that every cluster refreshed
successfully. Monitoring must run continuously for useful timing measurements.

## Definitions

- Successful deployments are cluster lifetimes first observed healthy in the
  selected period. Rebuilds start new lifetimes. Configuration updates have separate
  apply measurements but do not increase deployment counts.
- Unique creators are the original cluster creators associated with those
  successful deployments. Initiating users are retained separately for each apply.
  Unknown creators and service-token actors are not counted as people.
- First-time creators have their earliest recorded successful deployment in the
  selected period across the entire hub, even when filtering a single project.
  Returning creators first deployed before that period. Monthly classifications
  are calculated independently; totals of distinct users/clusters are not sums of
  monthly values.
- Active projects and distinct clusters have at least one successful deployment
  in the selected period. They do not measure whether previously deployed clusters
  are still running.
- Apply-to-healthy time starts when MC Hub receives successful acceptance of an
  apply request and ends at the first observed healthy status. Each Terraform run
  has one record, including updates and retries. Later health changes cannot change
  a completed measurement. Mean, median, and nearest-rank P95 include successful
  attempts with known acceptance times, grouped by apply request date.
- Failed and unfinished attempts are shown separately. A replaced or torn-down
  unfinished attempt remains in history. If acceptance is unknown (for example,
  the process exits after Terraform accepts but before the local write), subsequent
  success can be recorded but no duration is invented.
- Completed lifetime runs from the first accepted apply to confirmed teardown,
  including provisioning and any failed attempts within that lifetime. It is
  grouped by teardown date. Ongoing age is shown separately as of now, for the
  selected project regardless of date range.

Dates use UTC; both selected dates are inclusive. The initial range is the current
calendar month and the preceding 11 months. Ranges are limited to 10 years. Apply
history is paginated in groups of 25.

## Retained data

History uses stable UUIDs for clusters and projects, and survives deletion of their
operational records. A reused hostname or project name does not reuse its identity.
Project names, creator and initiating-user identifiers, repository names, commit
SHAs and Terraform run IDs are retained; configuration contents and credentials
are not copied into analytics. Existing repositories or externally created runs
may have unknown repository/commit fields; new plans created by MC Hub capture
the commit used to find their Terraform run.

Existing deployed clusters are marked as predating tracking when observed. Their
start and first-healthy times remain unknown and are excluded from adoption and
duration aggregates. A subsequent rebuild can be measured normally. Tracking
begins at migration time; history before this point is not reconstructed from Git.
Back up the database to preserve statistics along with other hub data.
