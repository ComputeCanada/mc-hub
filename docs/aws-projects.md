# AWS projects

Create an AWS project with an access key ID, secret access key, optional session
token, and one region. Use **Load available regions** after entering credentials
and select an enabled region. MC Hub verifies discovery and quota-read access
before creating the Terraform Cloud project. Credential changes are checked before
updating its variables. Projects with clusters cannot change region.

The AWS cluster editor offers an optional **Availability zone** selector listing
available, enabled standard zones in the project's region. Selecting a zone
filters instance choices by that zone's offerings and saves `availability_zone`
in the cluster definition and Terraform variables. Clearing it omits the variable
so the template uses its default. Changing the zone triggers a new feasibility
check; an existing instance selection that is not offered there is retained with
an explanation. Zone changes can require replacement resources, which remain
outside the final-state quota estimate. Local and Wavelength Zones are excluded.

The region is stored as `AWS_DEFAULT_REGION` and passed to Terraform Cloud with
the credentials. Generated `terraform.tfvars.json` files also include `region`,
always taken from the project settings rather than the cluster definition. Existing AWS projects must set this field in project settings.
Secrets and session tokens are marked sensitive in Terraform Cloud. The project's
AWS Terraform template must use this region and satisfy the following contract;
MC Hub does not inspect templates or plans:

| Resource | Deployment rule |
| --- | --- |
| EC2 | On-Demand, x86_64, HVM, EBS-backed; default vCPU configuration |
| Instance root disk | One 20 GiB `gp2` volume per instance |
| Elastic IP | One per instance with any of `proxy`, `login`, `dtn`; matching several tags still requires one IP |
| Images | Approved AlmaLinux 9 or Rocky Linux 9 community AMI IDs, compatible with a single disk no larger than 20 GiB |
| Data volumes | Tagged `gp2` volumes, including home, project and scratch; each row creates a disk of the specified GiB size on every instance matching its tag |

The image input passed to the template is an AMI ID. Instance groups accept only
`type`, `count`, and `tags`. Spot, custom CPU configurations, and bare
metal instances are outside this contract. Images requiring Marketplace
subscriptions are excluded. Published community image accounts are documented by
[AlmaLinux](https://wiki.almalinux.org/cloud/AWS.html) and
[Rocky Linux](https://forums.rockylinux.org/t/rocky-linux-official-aws-ami/3049/25).

## Discovery permissions

The credential identity needs these read permissions across the selected account
and region, including resources outside MC Hub:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeRegions",
      "ec2:DescribeAvailabilityZones",
      "ec2:DescribeImages",
      "ec2:DescribeInstanceTypes",
      "ec2:DescribeInstanceTypeOfferings",
      "ec2:DescribeInstances",
      "ec2:DescribeVolumes",
      "ec2:DescribeAddresses",
      "ec2:DescribeCapacityReservations",
      "servicequotas:ListServiceQuotas",
      "pricing:GetProducts"
    ],
    "Resource": "*"
  }]
}
```

This is the discovery policy, not the deployment policy. The Terraform execution
identity also needs the write permissions required by the configured template.
Project validation makes real read calls, including all pages of inventory and
applied quotas; it creates no AWS resources and does not simulate Terraform writes.
Expired credentials, revoked permissions, missing quota values, and service
failures produce an error, never an empty catalog or a green feasibility result.

## Feasibility and API

`GET /api/available-resources/cloud/<id>` and the corresponding `/host/<hostname>`
route return images and instance details, with `provider: "aws"`, the project
region, and an empty `quotas` object. OpenStack retains its numeric quotas.
AWS responses also include `possible_resources.availability_zone`. Zone-discovery
permission is verified when saving the project, alongside the other discovery reads.

`POST` to either resource route accepts the proposed cluster definition and returns:

```json
{
  "feasibility": {
    "status": "blocked",
    "scope": "final_state",
    "checked_at": "2026-09-09T12:00:00+00:00",
    "issues": [{
      "code": "quota_exceeded",
      "resource": "gp2",
      "required": 100,
      "available": 80,
      "message": "gp2: this definition requires 100 GiB; 80 are available for this cluster."
    }]
  },
  "instance_choices": {"node": []}
}
```

Choices are calculated separately for each group at its requested count after
accounting for the other groups. The editor refreshes these after changes, ignores
superseded responses, and preserves invalid selections with an explanation. It
shows **Within quotas**, specific blockers, or a verification error with retry.
Creation, modification, rebuild, and non-destroy apply requests are checked on the
server too.

Discovery reads run concurrently. Image, instance-type, and zone catalogs are
cached for five minutes per credential set and region, with concurrent identical
catalog reads sharing a single fetch. Applied quota values and account inventory
remain fresh for each request; project validation bypasses the catalog cache.
Quota reads use `ListServiceQuotas` filtered by quota ID for the regional
On-Demand pools, gp2 storage, and Elastic IPs, with at most three concurrent calls.
They do not enumerate every EC2/EBS quota. This requires no additional IAM action.
Each quota call logs its service, code, and duration for latency troubleshooting.
The feasibility response includes `instance_defaults` for all missing types,
chosen together against one snapshot, avoiding a new request for each group.
The type selectors show loading indicators only during initial discovery. Later
edits check feasibility in the background while keeping the current choices and
selections available, then update allowed choices when the check completes.
Deployment stays disabled until the latest definition is verified. The editor
waits for an in-flight feasibility request before submitting the latest edits.
INFO logs report each AWS discovery source's
duration and the cloud, domain, and version-discovery stages of the initial GET.

Limits come from applied Service Quotas. Compute usage is separated by On-Demand
family pool and includes capacity reservations without counting their running
instances twice. Storage includes unattached gp2 volumes; IP usage includes
unassociated Amazon-pool EIPs. The editable maximum is the account limit minus
account usage plus this cluster's counted live allocation. Terraform **state** is
used only to identify owned instance, volume, and EIP IDs; deleted and stopped
instances do not receive compute credits. Reservation-held compute capacity is
conservatively retained rather than credited as releasable capacity.

This checks the final cluster definition. It does not reserve capacity or predict
temporary replacement resources. Concurrent changes, AWS capacity shortages, and
constraints outside the contract can still prevent a launch. See AWS's
[On-Demand quotas](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-on-demand-instances.html)
and [EBS quotas](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-resource-quotas.html).

`POST /api/projects/aws/regions` accepts `{ "env": { ... } }` for new projects, or
an authorized `project_id` and optional credential overrides for existing ones.
It returns the account's enabled regions. Credentials are never included in the
response. Region discovery currently bootstraps through `us-east-1` and supports
the standard AWS partition.

## Instance prices and GPUs

AWS projects have an optional `max_instance_hourly_price` setting, editable by
project administrators. A blank/null value removes the ceiling; zero excludes all
priced instances. The ceiling is inclusive, in USD per instance-hour, and enforced
by the API before applying a cluster. It is stored in MC Hub, not Terraform.
Run database migrations when upgrading to add this nullable project column.

Selectors show public Linux/shared-tenancy On-Demand compute prices in the project
region, sorted cheapest first, and GPU count, manufacturer, model and per-GPU VRAM
from EC2 metadata. Storage, IP addresses, transfer, taxes and account discounts are
outside these prices. This is not a total cluster budget.

Price List GetProducts uses the us-east-1 endpoint with a filter for the project's
region. Project creation and credential updates verify `pricing:GetProducts` even
if the cache is warm. Prices are cached for 24 hours per credential/region scope,
with concurrent requests coalesced. Quota usage remains fresh. Missing prices are
shown explicitly and excluded when a ceiling is configured. Discovery failures
produce an error, never a false green light. Existing selections over a lowered
ceiling remain visible but require replacement before apply; destroy is unaffected.

The AWS volume editor retains the template's home, project and scratch rows and
supports **Add volume row**. Sizes are positive integers in GiB. Root and data
volumes share the gp2 storage quota; feasibility and instance choices account for
data disks multiplied by the number of instances matching their tag. Each volume
row must match at least one active instance. Storage is outside the hourly compute
price and project price ceiling. Existing deployed volume edit protections apply.
