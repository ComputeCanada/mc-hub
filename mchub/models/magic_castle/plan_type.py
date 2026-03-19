from enum import Enum


class PlanType(Enum):
    BUILD = "build"
    DESTROY = "destroy"
    NONE = None
