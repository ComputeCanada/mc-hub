# Recovering interrupted Terraform planning

Deploy the API and background worker from the same revision and run `flask db
upgrade` before starting them. Migration `0024` adds nullable planning-intent and
worker-lease fields to `terraformcloudrun`; existing clusters are preserved.
Stop the old API and worker processes during this upgrade so they cannot keep
running the old planning code alongside the recovery observer.

For the repository's Docker Compose deployment, from the updated checkout:

```sh
docker compose build api background-worker initialize
docker compose stop api background-worker
docker compose run --rm initialize
docker compose up -d api background-worker
```

For deployments using the production image directly, its default entrypoint runs
`flask db upgrade`. If you override that entrypoint, run the migration explicitly
with the deployment's configuration and database mounts before starting the API.
Update any separately deployed background worker too.

The existing usage observer checks clusters every 30 seconds. Status requests
also attempt recovery, so refreshing the cluster works for API-only deployments.
New planning tasks hold a renewable six-minute lease; another observer cannot
recover them until it expires. Legacy records have no lease and are eligible
immediately after upgrading. A normal plan wait remains bounded to five minutes.

## What recovery does

New deployments persist a fingerprint of their exact Terraform variables before
writing to GitHub, and persist the returned commit before creating its deployment
tag. Interrupted workers can therefore resume discovering the intended run.
A tag-creation retry verifies the full commit and does not create another tag if
the correct tag already exists. A replacement observer acquires the expired lease
atomically; an old worker cannot renew or release that replacement's lease.

For legacy records with a background-task status but no commit or run ID,
recovery verifies that the repository's default-branch head has its matching
`apply-` tag and that its Terraform variables match MC Hub's saved configuration.
Only the generated proxy token's randomized encryption is excluded from this
comparison; user hieradata, workspace, proxy URL, and other variables must match.
It then requires exactly one live, non-destroy deployment run with that full SHA.
If no live run remains, a unique finished run can be observed instead, so errors
are surfaced rather than left waiting. It does not choose the newest workspace
run by position.

If the matching run is pending, recovery checks every nonterminal workspace run
before discarding any blockers. Only older, discardable plans are discarded.
Active runs, newer runs, missing ordering information, multiple matching runs,
and configuration mismatches stop automatic recovery. External API failures keep
the saved intent for a later retry. Recovery does not apply the resulting plan.
Benchmark deployments retain their separate recovery workflow.

## mini-nibi.c3.ca

No cluster-specific database patch is needed. If the repository's tagged head
and saved configuration still identify October 16 commit
`70b1e7d3f89121f8669759a3e541930b311590d0`, recovery will reconnect
`run-BVG5LcSTReKBui1M`. With the workspace state reported during diagnosis, it
will discard the older paused October 15 plan and allow the October 16 run to
proceed. Once Terraform finishes, ordinary polling downloads its plan for review.

Look for `Recovered Terraform run ... for mini-nibi.c3.ca` in API or background
worker logs. `Plan recovery configuration mismatch` or `Plan recovery deferred`
means the remote state needs investigation; recovery leaves the cluster's
configuration intact. Do not use the earlier manual database-repair command
alongside this workflow.
