# Architecture

This diagram represents the architecture of MC Hub when used without authentication.

![Magic Castle CC UI Current Architecture](https://docs.google.com/drawings/d/e/2PACX-1vSKQIzh44C0FiuPD1pn_SspvwD_s2bGoF8wpcHPbthgauMoo2loe5VUjUsMPc-bVBdYdk1W4dxheYlS/pub?w=721&amp;h=530)

## Cluster statuses

The [ClusterStatusCode](../app/models/magic_castle/cluster_status_code.py) class is an enum which represents the current status of a Magic Castle cluster. The following diagram represents the possible transitions between statuses.

![Cluster Status Transition Diagram](./diagrams/cluster_status_transition_diagram.svg)
