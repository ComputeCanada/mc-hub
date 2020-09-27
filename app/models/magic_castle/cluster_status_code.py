from enum import Enum


class ClusterStatusCode(Enum):
    IDLE = "idle"
    CREATED = "created"
    PLAN_RUNNING = "plan_running"
    BUILD_RUNNING = "build_running"
    BUILD_ERROR = "build_error"
    PROVISIONING_RUNNING = "provisioning_running"
    PROVISIONING_SUCCESS = "provisioning_success"
    PROVISIONING_ERROR = "provisioning_error"
    DESTROY_RUNNING = "destroy_running"
    DESTROY_ERROR = "destroy_error"
    NOT_FOUND = "not_found"
