from __future__ import annotations
from enum import Enum
from .terraform_cloud_status import TFCloudStatusCode


class ClusterStatusCode(str, Enum):
    CREATED = "created"
    BACKGROUND_TASK_RUNNING = "background_task_running"
    PLAN_RUNNING = "plan_running"
    PLAN_ERROR = "plan_error"

    BUILD_RUNNING = "build_running"
    BUILD_ERROR = "build_error"

    PROVISIONING_RUNNING = "provisioning_running"
    PROVISIONING_SUCCESS = "provisioning_success"
    PROVISIONING_ERROR = "provisioning_error"

    DESTROY_RUNNING = "destroy_running"
    DESTROY_ERROR = "destroy_error"
    DESTROY_SUCCESS = "destroy_success"

    NOT_FOUND = "not_found"

    @staticmethod
    def from_tfcloudstatus(tf_status: TFCloudStatusCode, is_detroy: bool):
        """
        Those status are not supported with TFCloud
        ClusterStatusCode.BUILD_ERROR
        ClusterStatusCode.PROVISIONING_ERROR
        """
        match tf_status:
            case (
                TFCloudStatusCode.PENDING
                | TFCloudStatusCode.PLAN_QUEUED
                | TFCloudStatusCode.FETCHING
                | TFCloudStatusCode.FETCHING_COMPLETED
                | TFCloudStatusCode.PRE_PLAN_COMPLETED
                | TFCloudStatusCode.QUEUING
                | TFCloudStatusCode.PLANNING
                | TFCloudStatusCode.PRE_PLAN_RUNNING
            ):
                status = ClusterStatusCode.PLAN_RUNNING
            case (
                TFCloudStatusCode.DISCARDED
                | TFCloudStatusCode.ERRORED
                | TFCloudStatusCode.CANCELED
                | TFCloudStatusCode.FORCE_CANCELED
            ):
                # TODO: When an error occur, we can fetch the plan and apply to know the corresponding step.
                # For now, all errors are return as PLAN_ERROR
                status = ClusterStatusCode.PLAN_ERROR
            case TFCloudStatusCode.PLANNED_AND_SAVED | TFCloudStatusCode.PLANNED:
                status = ClusterStatusCode.CREATED
            case (
                TFCloudStatusCode.APPLYING
                | TFCloudStatusCode.APPLY_QUEUED
                | TFCloudStatusCode.COST_ESTIMATING
                | TFCloudStatusCode.COST_ESTIMATED
                | TFCloudStatusCode.POLICY_CHECKING
                | TFCloudStatusCode.POLICY_OVERRIDE
                | TFCloudStatusCode.POLICY_SOFT_FAILED
                | TFCloudStatusCode.POLICY_CHECKED
                | TFCloudStatusCode.POST_PLAN_RUNNING
                | TFCloudStatusCode.POST_PLAN_COMPLETED
            ):
                status = ClusterStatusCode.BUILD_RUNNING
            case TFCloudStatusCode.APPLIED | TFCloudStatusCode.PLANNED_AND_FINISHED:
                status = ClusterStatusCode.PROVISIONING_RUNNING

            case TFCloudStatusCode.CONFIRMED:
                raise NotImplementedError(f"TFCloud status is unsuported: {tf_status=}")

            case _:
                status = ClusterStatusCode.NOT_FOUND

        if (
            is_detroy
        ):  # Extra step for destroy case (use only ClusterStatusCode from here)
            match status:
                case ClusterStatusCode.PLAN_RUNNING | ClusterStatusCode.CREATED:
                    pass
                case ClusterStatusCode.BUILD_RUNNING:
                    status = ClusterStatusCode.DESTROY_RUNNING
                case ClusterStatusCode.PROVISIONING_RUNNING:
                    status = ClusterStatusCode.DESTROY_SUCCESS
                case _:
                    status = ClusterStatusCode.DESTROY_ERROR
        return status

    @staticmethod
    def is_provisioning(current_status: ClusterStatusCode):
        return current_status in [
            ClusterStatusCode.PROVISIONING_RUNNING,
            ClusterStatusCode.PROVISIONING_SUCCESS,
            ClusterStatusCode.PROVISIONING_ERROR,
        ]