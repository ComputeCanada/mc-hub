from jsonpath_ng.ext import parse


class TerraformPlanParser:
    """
    Class in charge of parsing the json representation outputted by terraform plan
    and parsing the progress outputted by terraform apply. 

    Relevant Terraform documentation:
    https://www.terraform.io/docs/internals/json-format.html#change-representation
    """

    @staticmethod
    def get_resources_changes(plan):
        """
        Outputs the relevant fields in the Terraform plan's resource changes.

        :return: The resource changes. For example:

        [
            {
                "address": "module.openstack.openstack_networking_floatingip_v2.fip[0]",
                "type": "openstack_networking_floatingip_v2",
                "change": {"actions": ["create"]},
            },
            ...
        ]
        """
        raw_resource_changes = plan.get("resource_changes")
        if raw_resource_changes:
            return [
                {
                    "address": resource["address"],
                    "type": resource["type"],
                    "change": {"actions": resource["change"]["actions"]},
                }
                for resource in raw_resource_changes
            ]
        else:
            return []

    @staticmethod
    def get_done_changes(initial_plan, terraform_apply_output: str):
        """ 
        Computes the difference between an initial Terraform plan and the output from terraform apply and determines
        which resource changes are "queued", "running" or "done". 

        Note:
        When the initial change action is ["read"] for a resource, Terraform removes the resource change from
        the list of changes after it has been performed, instead of having a change action of ["no-op"].

        :param initial_plan: The initial Terraform plan.
        :param terraform_apply_output: The output of terraform apply or terraform destroy.
        :return: The resource changes, with a "progress" attribute (either "queued", "running" or "done"), for instance:
        [
            {
                "address": "module.openstack.openstack_networking_floatingip_v2.fip[0]",
                "type": "openstack_networking_floatingip_v2",
                "change": {"actions": ["create"], "progress": "queued"},
            },
            ...
        ]
        """
        done_resources_changes = TerraformPlanParser.get_resources_changes(initial_plan)
        for done_resource_change in done_resources_changes:
            resource_address = done_resource_change["address"]

            creation_running_index = terraform_apply_output.find(
                f"{resource_address}: Creating..."
            )
            destruction_running_index = terraform_apply_output.find(
                f"{resource_address}: Destroying..."
            )
            modification_running_index = terraform_apply_output.find(
                f"{resource_address}: Modifying..."
            )

            creation_complete_index = terraform_apply_output.find(
                f"{resource_address}: Creation complete"
            )
            destruction_complete_index = terraform_apply_output.find(
                f"{resource_address}: Destruction complete"
            )
            modifications_complete_index = terraform_apply_output.find(
                f"{resource_address}: Modifications complete"
            )
            progress = "queued"

            if done_resource_change["change"]["actions"] == ["no-op"]:
                progress = "done"
            elif done_resource_change["change"]["actions"] == ["create"]:
                if creation_complete_index != -1:
                    progress = "done"
                elif creation_running_index != -1:
                    progress = "running"
            elif done_resource_change["change"]["actions"] == ["read"]:
                progress = "done"
            elif done_resource_change["change"]["actions"] == ["update"]:
                if modifications_complete_index != -1:
                    progress = "done"
                elif modification_running_index != -1:
                    progress = "running"
            elif done_resource_change["change"]["actions"] == ["delete", "create"]:
                if (
                    creation_complete_index != -1
                    and destruction_complete_index != -1
                    and destruction_complete_index < creation_complete_index
                ):
                    progress = "done"
                elif destruction_running_index != -1:
                    progress = "running"
            elif done_resource_change["change"]["actions"] == ["create", "delete"]:
                if (
                    creation_complete_index != -1
                    and destruction_complete_index != -1
                    and destruction_complete_index > creation_complete_index
                ):
                    progress = "done"
                elif creation_running_index != -1:
                    progress = "running"
            elif done_resource_change["change"]["actions"] == ["delete"]:
                if destruction_complete_index != -1:
                    progress = "done"
                elif destruction_running_index != -1:
                    progress = "running"

            done_resource_change["change"]["progress"] = progress
        return done_resources_changes

