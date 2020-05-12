# Magic Castle UI
Web interface to launch Magic Castles without knowing anything about Terraform.

## Requirements

- Docker
- Bash interpreter

## Setup for OpenStack Cloud

1. Source your project openrc file.
    ```
    source _project_-openrc.sh
    ```
2. Run start.sh. This will build and run the docker container for the Flask Server.
   ```
   ./start.sh
   ```


## Compute Canada Web Deployment Architecture

The app will eventually be accessible with a Compute Canada account to launch a Magic Castle cluster in shared project in Compute Canada cloud. Here is an early draft of the app design:

![Magic Castle CC UI Architecture](https://docs.google.com/drawings/d/e/2PACX-1vRe4JZSPiKY7tW5xO3WpsWoA8h0XC6zAjiMBwbgn-UIY6PMBC_5X-gJj9AbmdRCoEU4OXORh04xexO5/pub?w=721&amp;h=498 "Magic Castle CC UI Architecture")
