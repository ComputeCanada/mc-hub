"""Create a benchmark's integrations on save, without creating a deployment run."""
from copy import deepcopy
import logging

from ..database import db
from ..exceptions.invalid_usage_exception import InvalidUsageException
from ..models.benchmark import BenchmarkRun
from ..models.magic_castle.magic_castle import MagicCastle
from ..models.user import UserORM
from .benchmarks import reusable_cluster, verify_empty

logger = logging.getLogger(__name__)


def initialize_benchmark(benchmark):
    """Initialize integrations while the caller holds the benchmark lock."""
    db.session.refresh(benchmark)
    if benchmark.setup_status == "ready":
        return True
    if benchmark.archived or db.session.scalar(db.select(BenchmarkRun.id).filter_by(active_benchmark_id=benchmark.id)):
        raise InvalidUsageException("Finish the active run and cleanup before setting up this benchmark.", status_code=409)
    benchmark.setup_status, benchmark.setup_error = "creating", None
    db.session.commit()
    try:
        orm = reusable_cluster(benchmark.id)
        if orm is not None:
            if not orm.undeployed:
                raise InvalidUsageException("Tear down the benchmark before retrying setup.")
            verify_empty(MagicCastle(orm))
            orm.benchmark_id = benchmark.id
            db.session.commit()
        creator = db.session.scalar(db.select(UserORM).filter_by(scoped_id=benchmark.created_by))
        MagicCastle(orm).plan_creation(
            deepcopy(benchmark.configuration), creator.id if creator else None,
            benchmark_id=benchmark.id, reuse_integrations=orm is not None, initialize_only=True,
        )
        benchmark.setup_status, benchmark.setup_error = "ready", None
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        logger.exception("Benchmark setup failed for %s", benchmark.id)
        benchmark.setup_status = "failed"
        benchmark.setup_error = "Benchmark setup failed. Save again to retry using integrations already created."
        db.session.commit()
        return False
