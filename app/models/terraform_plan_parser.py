from jsonpath_ng.ext import parse


class TerraformPlanParser:
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
        return [
            {
                "address": resource["address"],
                "type": resource["type"],
                "change": {"actions": resource["change"]["actions"]},
            }
            for resource in plan["resource_changes"]
        ]

    @staticmethod
    def get_done_changes(initial_plan, terraform_apply_output: str):
        """ 
        Computes the difference between an initial Terraform plan and a current plan and determines
        which resource changes are "done", meaning they have been applied by terraform. 

        Note:
        When the initial change action is ["read"] for a resource, Terraform removes the resource change from
        the list of changes after it has been performed, instead of having a change action of ["no-op"].

        :param initial_plan: The initial Terraform plan.
        :param terraform_apply_output: The output of terraform apply or terraform destroy.
        :return: The resource changes, with a "done" boolean attribute, for instance:
        [
            {
                "address": "module.openstack.openstack_networking_floatingip_v2.fip[0]",
                "type": "openstack_networking_floatingip_v2",
                "change": {"actions": ["create"], "done": True},
            },
            ...
        ]
        """
        done_resources_changes = TerraformPlanParser.get_resources_changes(initial_plan)
        for done_resource_change in done_resources_changes:
            resource_address = done_resource_change["address"]

            creation_index = terraform_apply_output.find(
                f"{resource_address}: Creation complete"
            )
            destruction_index = terraform_apply_output.find(
                f"{resource_address}: Destruction complete"
            )
            modifications_index = terraform_apply_output.find(
                f"{resource_address}: Modifications complete"
            )
            done = False

            # https://www.terraform.io/docs/internals/json-format.html#change-representation
            if done_resource_change["change"]["actions"] == ["no-op"]:
                done = True
            elif done_resource_change["change"]["actions"] == ["create"]:
                done = creation_index != -1
            elif done_resource_change["change"]["actions"] == ["read"]:
                done = True
            elif done_resource_change["change"]["actions"] == ["update"]:
                done = modifications_index != -1
            elif done_resource_change["change"]["actions"] == ["delete", "create"]:
                done = (
                    creation_index != -1
                    and destruction_index != -1
                    and destruction_index < creation_index
                )
            elif done_resource_change["change"]["actions"] == ["create", "delete"]:
                done = (
                    creation_index != -1
                    and destruction_index != -1
                    and destruction_index > creation_index
                )
            elif done_resource_change["change"]["actions"] == ["delete"]:
                done = destruction_index != -1

            done_resource_change["change"]["done"] = done
        return done_resources_changes

