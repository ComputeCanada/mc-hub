from enum import Enum


class ClusterStatusCode(Enum):
    IDLE = 'idle'
    BUILD_RUNNING = 'build_running'
    BUILD_SUCCESS = 'build_success'
    BUILD_ERROR = 'build_error'
    DESTROY_RUNNING = 'destroy_running'
    DESTROY_ERROR = 'destroy_error'
    NOT_FOUND = 'not_found'
