# Project capacity planner

Open **Capacity planner** from the account menu or a project's **Capacity** button.
Select a start and end date (midnight in your browser's local timezone),
then use the cluster editor to describe the resources. **Check planned capacity**
shows overlapping quota shortages; **Save capacity plan** saves even when quota is
insufficient. Dates are stored as UTC instants; the period ends at the beginning
of the end date. The end is exclusive, so adjacent periods do not overlap.

All project members see planned resource demand, owners, dates, and creation status.
Only a plan's owner and project administrators can access its full configuration or
cancel it. Full configurations can contain passwords and Puppet configuration;
they are stored in the application's database and are not included in project-wide
list responses. Pending plans can be cancelled before creation starts. To change a
pending plan, cancel it and create a replacement.

With automatic creation enabled, the worker starts creation at or after the start
time. Provisioning takes additional time. Otherwise, use **Create manually** on the
plan, then review and apply the normal Terraform plan. Creating through this button
links the cluster to the plan. Creating an unrelated cluster from the ordinary
creation page does not link it to a capacity plan.

**At the end time, linked cluster resources and their data are automatically torn
down.** MC-Hub keeps the undeployed cluster configuration, repository, and Terraform
workspace, following its existing teardown lifecycle. Teardown waits for busy
operations and retries failures. Start/end times are scheduling targets, not strict
guarantees: the worker checks every 30 seconds and cloud operations take time.

## Forecast assumptions

OpenStack forecasts compare overlapping plans with the project's full quota limits,
without subtracting current cloud usage. Active plans continue to count throughout
their declared periods after deployment. Resources used outside these plans are not
included in the OpenStack forecast; actual available quota is checked at automatic
creation time.

AWS forecasts combine current available quota with additional planned demand and
hold current usage constant throughout the horizon. Successfully deployed linked
clusters are already included in current usage and are not counted twice. In-flight
or partially failed deployments may be counted conservatively until confirmed.

OpenStack estimates include instances, vCPUs, RAM (MiB), public IPs, boot volumes,
and volumes attached by instance tag. Explicit root disk sizes are conservatively
counted as boot volumes. AWS uses the existing regional On-Demand quota pools,
gp2 storage (GiB), and Elastic IP accounting. Instance/image availability, external
usage, concurrent deployments, and quota changes can invalidate an earlier check.
GPU counts are shown separately in the form, plan list, and forecast, even without
a GPU quota. Counts multiply each instance group's size by its GPU allocation.
AWS counts use GPU metadata and account for fractional partitions. OpenStack counts
use the flavor naming conventions `g<count>[-<VRAM>gb]-...` and `gpu...-<model>x<count>`;
GPU allocations in flavors without those conventions or GPU metadata cannot be
identified. Previously saved plans have GPU counts derived when the forecast loads.

These plans are coordination records, not provider reservations or guarantees of
physical capacity. Quota is rechecked when saving and at automatic creation time.

## Operations

Apply database migration `0021` using the deployment's normal `flask db upgrade`
step and restart the web service and background-worker supervisor. The supervisor
includes `mchub.services.capacity_worker`; keep one supervisor per database volume.
No additional credentials or configuration are required.

Automatic start claims are durable and are not retried blindly after a failure or
worker restart. Review the reported failure and any partial cluster before retrying
manually. Cleanup identifies the cluster by its immutable lifetime ID, so reusing a
hostname cannot cause a different cluster to be torn down. End-of-period cleanup
continues even if the original owner leaves the project.

API routes (all project-scoped):

- `GET /api/projects/<id>/capacity`: upcoming plans and forecast; also shows failures
  and pending cleanup after their scheduled end.
- `POST /api/projects/<id>/capacity/preview`: check a candidate without saving.
- `POST /api/projects/<id>/capacity`: save `{starts_at, ends_at, definition, auto_create}`.
  Timestamps must include timezone offsets.
- `GET /api/projects/<id>/capacity/<plan_id>`: owner/admin configuration detail.
- `DELETE /api/projects/<id>/capacity/<plan_id>`: cancel an unstarted plan.

Manual cluster creation accepts `capacity_plan_id` in its existing request body.
The server checks ownership/project membership, claims the plan once, and associates
its cluster lifetime with the end-of-period cleanup.
