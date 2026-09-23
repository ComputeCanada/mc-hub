# Project benchmarks

Project administrators can open **Benchmarks** from the account menu (`/benchmarks`).
The page and API expose only projects the user administers. Ordinary project members
and service tokens cannot manage or read benchmark definitions/results. Hub admin
status alone does not grant project administration; local/no-auth mode retains its
existing administrator behavior.

Create a benchmark using the shared cluster creation form, with these added controls:

- Name and hourly, daily, or weekly frequency.
- Success criterion: **Build completed** (Terraform apply finished) or
  **Provisioning completed (healthy)** (all configured health checks healthy,
  the default).
- Scheduled runs enabled/paused.
- Next scheduled run in UTC (defaults to one interval after saving).
- Maximum run time, from creation through the selected target, including planning: 10–1440
  minutes, default 120.

**Run now** also works while a schedule is paused. Saving a benchmark authorizes
unattended plan application for its specifications and automatic teardown. Each
benchmark owns one cluster hostname, Git repository, and Terraform workspace. Every
run uses the configured cluster name exactly, with no suffix or truncation, and
creates fresh resources in that workspace. `{cluster_name}.int.{domain}` must fit
within 63 characters. The form and API reject longer names.

Cluster names are reserved across the hub because Terraform workspace names share
an organization. Another benchmark or ordinary cluster cannot take a reserved name.
On the first save, MC Hub creates the Git repository from the provider template,
writes the Terraform variables, and creates and configures the Terraform workspace.
Saving waits for this setup to finish without creating a deployment plan or a
benchmark result. This also applies to paused benchmarks. Deployment starts only
with **Run now** or a scheduled run.

The cluster name and domain are fixed when setup begins on the first save; create a new
benchmark to change them. Other specification edits apply to future runs.
The selected Magic Castle version is pinned in the definition and copied into each
run's snapshot.

Schedules are intervals of 1, 24, or 168 hours in UTC, anchored initially by the next
run timestamp. After an eligible scheduler sweep, the next time is one interval
later. They do not follow local daylight-saving changes. Missed schedules coalesce:
there is no backlog after downtime. When an earlier run or its cleanup is active,
the scheduled occurrence is skipped. Manual and scheduled requests share the same
database uniqueness constraint, so a benchmark cannot overlap itself.

Before starting either a manual or scheduled run, the worker reads the shared
service-provider snapshots maintained by MC Hub's existing status monitor. A
reported disruption for any enabled, configured provider (GitHub and Terraform
Cloud by default) keeps the run queued and reserves its benchmark. It checks again
every minute for hourly benchmarks, every hour for daily benchmarks, and every day
for weekly benchmarks, using the definition's current frequency at each check.
It starts automatically when a check reports no disruption. The history
shows **Postponed**, the affected providers, and the next check time. Waiting does
not start the maximum-run-time clock or count as a failed result. Further scheduled
occurrences coalesce while the run is queued.

The existing provider/component configuration also controls these checks. Retained
disruptions, including stale snapshots and incidents awaiting confirmed resolution,
continue to postpone runs. Unknown status or a stale snapshot with no reported
disruption does not block them. These checks do not fetch feeds directly. Runs that
have already started and cleanup continue during disruptions; archiving still
cancels queued runs.

Edits affect future runs only. Each run retains its success criterion, definition
revision, specifications, requester, Terraform run ID, commit SHA, repository, and
timing fields. Pausing stops
future scheduled runs; archiving also removes the definition from the default list.
History remains available using **Show archived**. Runs already executing still
complete cleanup; queued runs are cancelled when they encounter an archived
benchmark. A project cannot be deleted while it has unarchived benchmarks or active
benchmark cleanup.

## Timing and results

**Build completed** measures Terraform Cloud's apply `started-at` to `finished-at`
for the original deployment run. These timestamps come from the
[Applies API](https://developer.hashicorp.com/terraform/cloud-docs/api-docs/applies),
not the worker's observation time. Queueing, planning, worker polling delays, and
later service health checks are excluded from this duration. The locally recorded
apply acceptance remains available separately for diagnostics. Missing or invalid
Terraform timestamps are retried until the run deadline; no local timestamp is
substituted. A plan that finishes without an apply fails the benchmark because it
does not measure a deployment.

**Provisioning completed (healthy)** measures MC Hub's apply acceptance to its
first observation that all configured health checks pass. The scheduler polls
every 10 seconds, with additional process startup and remote API latency; the usage
observer can also record readiness. This criterion retains observation-based timing.

Cleanup begins after the selected target is reached, or after failure or timeout.
The maximum run time still includes planning and queueing. A build completed before
the deadline succeeds even if the worker observes it later. The dashboard shows
mean, median, nearest-rank P95, success rate, a duration trend, and individual run
details. Historical build results without a Terraform apply start retain their
original timestamps in history but do not enter timing aggregates or trends.

Failed and timed-out attempts are included in the success-rate denominator but not
in duration aggregates. Cancelled queued runs are excluded from that denominator.
When an apply response is lost or a process dies before recording acceptance,
healthy runs may succeed with unknown duration; no start time is invented. Build
runs can still be measured using Terraform's execution timestamps. Results retain
their recorded timing after later health changes or teardown.

The dashboard's **Commit and success criterion** selector groups results by the
full Git commit SHA, repository, and success criterion. Each group's summary covers
its entire history; the trend shows matching results among the latest 500 runs.
The default is the most recent group with the definition's current success criterion.
Select another group to inspect older commits or another criterion independently.
Build and healthy durations are never combined, and different SHAs remain separate
even when their specifications happen to match. Runs with unknown SHAs appear in
history but do not enter comparison groups. History identifies each run's commit,
original criterion, and target timestamp.
Infrastructure snapshots in run results omit passwords, public keys, and hieradata.
Saved definitions and internal
snapshots still contain the configuration needed to reproduce a deployment, with
the same database access requirements as ordinary saved cluster configurations.
Benchmark deployments are excluded from the hub's service-adoption dashboard.

## Cleanup and recovery

Success, failure, and timeout all transition into cleanup. The worker tears down
resources and verifies that the workspace has no managed resources or pending runs.
It retains the undeployed cluster definition, repository, and workspace for the next
run. The next run verifies emptiness again and creates a fresh Terraform deployment
run from the saved Git configuration. Unchanged deployment settings reuse that
commit, including the already encrypted proxy token and Puppet values. The worker
does not regenerate ciphertext or write Terraform files just to start another run.
Name, frequency, schedule, timeout, and success-criterion edits keep the same commit;
the criterion still determines which result group receives the run.

Changed deployment settings are written to a new commit on the next run. The first
deployment of a commit imports it through the VCS tag; subsequent deployments use
Terraform's [existing configuration version](https://developer.hashicorp.com/terraform/cloud-docs/api-docs/run#create-a-run)
to create a new run with automatic apply disabled. The worker explicitly applies
that new plan and records its acceptance separately from execution. Historical results retain
their original commit, Terraform run, and timings. The saved commit is pinned;
external edits to the repository do not change an unchanged benchmark's deployment.

Archiving a benchmark also schedules cleanup of its retained definition and
integrations. Once its resources are gone, the repository is archived and the
workspace is tagged/locked, using the ordinary deletion lifecycle. The cluster name
remains reserved because those integrations are retained externally. If a benchmark
has never run, archiving verifies and archives its integrations immediately, without
adding a run to the results.

If initial setup fails, the form retains the saved benchmark ID and displays a retry
message. Save again to resume setup using the repository and workspace already
recorded. A failed or interrupted setup blocks both scheduled runs and **Run now**;
open **Edit** and save to retry. Setup failures are logged by the web service.

Cleanup errors remain visible and are retried. An active Terraform operation must
finish before safe teardown can proceed; the configured timeout does not forcibly
cancel an in-flight Terraform apply. No subsequent run of that benchmark can start
until cleanup is confirmed. Benchmark-owned clusters reject manual lifecycle edits
through the cluster API, and are excluded from the general expiration worker.

The scheduler runs in the existing supervised background container. It executes up
to four lifecycle operations concurrently in isolated processes, prioritizing
cleanup and readiness checks over new creation. Each operation has a five-minute
watchdog, bounded further by the run deadline while deploying. Build completion
checks retain the full watchdog window to verify Terraform timestamps after a
deadline has passed. A stalled operation
is terminated locally and moves to cleanup; remote Terraform work may continue and
is reconciled before resource deletion. Per-benchmark file locks prevent simultaneous
operations, and operation processes exit if their scheduler parent dies. Interrupted
creation transitions into cleanup. Older runs queued before this change can still
resume incomplete setup using integrations already recorded in the database.
Unknown apply acceptance is never
replayed. Infrastructure errors are logged in `docker compose logs background-worker`;
the dashboard displays generic errors to avoid copying credentials from provider
responses into results.

## Deployment

Apply migrations through `0017` before starting updated web and worker containers.
Existing runs keep their original names, measurements, and per-run cleanup policy.
Existing reusable integrations are assigned to their benchmark. Definitions without
completed setup must be saved before their next run. Future runs reserve the
benchmark's configured name and reuse its integrations.
Migration `0016` retains the inputs and Git commit of the prepared configuration.
Existing benchmarks render and retain a commit on their first run after upgrading.
Historical SHAs are not rewritten or merged; older runs that each created a different
commit remain separate groups.
Migration `0017` adds the Terraform apply-start timestamp. Historical build timing
is not backfilled automatically; those runs remain visible but are excluded from
execution-time comparisons. Healthy results are unchanged.
An older definition with a conflicting or overlong name must be edited before its
next run. Historical repositories and workspaces are not adopted or renamed.
Compose's initialization service runs `flask db upgrade`.
Stop the existing deployment before
migrating, as described in [usage statistics](usage-statistics.md). The supervisor
starts the benchmark scheduler automatically. No additional container or dependency
is required. Run only one background supervisor per shared database volume.
