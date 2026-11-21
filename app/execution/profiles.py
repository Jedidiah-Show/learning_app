"""Explicit, server-selected execution profiles (M3.1).

Learners never choose resource limits. Exercises and projects declare a
workload; the application maps that workload to one of these profiles. The
judge worker then applies the profile's CPU, memory, timeout, storage and
concurrency bounds instead of trusting request data.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class ExecutionProfile:
    name: str
    runtime: str
    libraries: Tuple[str, ...]
    cpu_limit: float
    memory_mb: int
    timeout_sec: float
    storage_mb: int
    network_policy: str
    max_concurrency: int
    workloads: Tuple[str, ...]
    persistent_artifacts: bool
    enabled: bool = True
    image: str = ''


PROFILES: Dict[str, ExecutionProfile] = {
    'browser_python': ExecutionProfile(
        name='browser_python',
        runtime='pyodide',
        libraries=('pyodide',),
        cpu_limit=0,
        memory_mb=0,
        timeout_sec=10.0,
        storage_mb=0,
        network_policy='browser-sandbox',
        max_concurrency=100,
        workloads=('formative_run',),
        persistent_artifacts=False,
    ),
    'container_python': ExecutionProfile(
        name='container_python',
        runtime='docker',
        libraries=('python',),
        cpu_limit=0.5,
        memory_mb=512,
        timeout_sec=3.0,
        storage_mb=16,
        network_policy='none',
        max_concurrency=4,
        workloads=('arena_submit', 'arena_run', 'algorithms'),
        persistent_artifacts=True,
    ),
    'container_data_science': ExecutionProfile(
        name='container_data_science',
        runtime='docker',
        libraries=('numpy', 'pandas', 'matplotlib', 'scipy', 'sklearn', 'sympy', 'networkx'),
        cpu_limit=1.0,
        memory_mb=1024,
        timeout_sec=15.0,
        storage_mb=64,
        network_policy='none',
        max_concurrency=2,
        workloads=('data_science', 'ml_exercise'),
        persistent_artifacts=True,
    ),
    'container_ml': ExecutionProfile(
        name='container_ml',
        runtime='docker',
        libraries=('numpy', 'pandas', 'scipy', 'sklearn', 'torch', 'transformers'),
        cpu_limit=2.0,
        memory_mb=2048,
        timeout_sec=60.0,
        storage_mb=256,
        network_policy='none',
        max_concurrency=1,
        workloads=('ml_training', 'ml_evaluation'),
        persistent_artifacts=True,
        enabled=False,
    ),
    'gpu_training': ExecutionProfile(
        name='gpu_training',
        runtime='dedicated-compute',
        libraries=('torch', 'transformers', 'datasets'),
        cpu_limit=4.0,
        memory_mb=8192,
        timeout_sec=3600.0,
        storage_mb=2048,
        network_policy='none',
        max_concurrency=1,
        workloads=('gpu_training', 'fine_tuning'),
        persistent_artifacts=True,
        enabled=False,
    ),
}


class UnknownProfileError(ValueError):
    pass


class ProfileDisabledError(ValueError):
    pass


def list_profiles() -> list:
    """Return a stable copy of the registry for administration/health output."""
    return [PROFILES[name] for name in sorted(PROFILES)]


def get_profile(name: str) -> ExecutionProfile:
    try:
        return PROFILES[name]
    except KeyError as error:
        raise UnknownProfileError(f'Unknown execution profile: {name}') from error


def profile_for_workload(workload: str) -> ExecutionProfile:
    """Select a profile server-side from a workload name."""
    for profile in PROFILES.values():
        if workload in profile.workloads:
            if not profile.enabled:
                raise ProfileDisabledError(
                    f'Execution profile {profile.name} is not enabled'
                )
            return profile
    raise UnknownProfileError(f'No execution profile for workload: {workload}')


def profile_for_problem(problem: dict) -> ExecutionProfile:
    """Select a profile from trusted exercise metadata.

    ``execution_profile`` is read only from the server-side problem catalogue;
    a learner-supplied field cannot influence this call.
    """
    declared = (problem or {}).get('execution_profile')
    if declared:
        return get_profile(str(declared))
    track = (problem or {}).get('track')
    if track == 'machine-learning':
        return get_profile('container_data_science')
    return get_profile('container_python')
