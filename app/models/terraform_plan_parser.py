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
    def get_done_changes(initial_plan, current_plan):
        """ 
        Computes the difference between an initial Terraform plan and a current plan and determines
        which resource changes are "done", meaning they have been applied by terraform. 

        Note:
        When the initial change action is ["read"] for a resource, Terraform removes the resource change from
        the list of changes after it has been performed, instead of having a change action of ["no-op"].

        :param initial_plan: The initial Terraform plan.
        :param current_plan: The current Terraform plan.
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
        current_resources_changes = TerraformPlanParser.get_resources_changes(
            current_plan
        )
        for done_resource_change in done_resources_changes:
            done = False
            for current_resource_change in current_resources_changes:
                if (
                    done_resource_change["address"]
                    == current_resource_change["address"]
                ):
                    done = current_resource_change["change"]["actions"] == ["no-op"]
                    break
            else:
                done = True
            done_resource_change["change"]["done"] = done
        return done_resources_changes

