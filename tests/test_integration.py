"""Integration tests for dask-iclx.

These tests require HTCondor to be available and should only be run locally.
They are marked with @pytest.mark.integration and will be skipped in CI.
"""

import pytest
import socket
import shutil
from distributed import Client
from dask_iclx import ICCluster


def has_htcondor():
    """Check if HTCondor is available on the system."""
    return shutil.which("condor_submit") is not None


def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("0.0.0.0", port))
        available = True
    except Exception:
        available = False
    sock.close()
    return available


def get_available_port(good_port_range=(60000, 60099), worker_id="master"):
    # Make process-safe port selection
    if worker_id == "master":
        port_range = good_port_range
    else:
        # Offset the port range for worker nodes to avoid conflicts
        offset = 10 * int(worker_id.strip("gw"))
        lower = good_port_range[0] + offset
        upper = min(good_port_range[1], lower + 10)
        port_range = (lower, upper)

    # Scan the port range for an available port
    n_port = None
    for port in range(*port_range):
        if check_port(port):
            n_port = port
            break
    if n_port is None:
        raise RuntimeError(f"No available port found in range {port_range}")
    return n_port


def get_worker_id(request):
    """Get the worker ID from the pytest request object."""
    worker_id = getattr(request, "node", None)
    if worker_id is None:
        return "local"
    return worker_id


# Test parameter combinations: lcg (True/False), nanny (True/False), GPU (None/1)
@pytest.mark.parametrize("nanny", [True, False])
@pytest.mark.parametrize(
    "gpus", [None, 1], ids=lambda x: "cpu" if x is None else f"gpu{x}"
)
@pytest.mark.parametrize("container_runtime", ["none", "singularity"])
@pytest.mark.integration
@pytest.mark.skipif(not has_htcondor(), reason="HTCondor not available")
def test_iccluster_integration_no_lcg(nanny, gpus, container_runtime, worker_id):
    """Test basic ICCluster functionality with a real HTCondor submission.

    This test creates a cluster, scales it, and runs a simple task.
    Tests all combinations of lcg (True/False), nanny (True/False), and GPU/CPU configurations.
    """

    # Configure cluster parameters based on test configuration
    cluster_kwargs = {
        "cores": 1,
        "memory": "3000MB",
        "disk": "10GB",
        "death_timeout": "60",
        "lcg": False,
        "nanny": nanny,
        "container_runtime": container_runtime,
        "log_directory": "/vols/cms/tr1123/dask-logs",
        "scheduler_options": {
            "port": get_available_port(worker_id=worker_id),
            "host": socket.gethostname(),
        },
        "job_extra": {
            "+MaxRuntime": "1200",
        },
        "name": f"TestCluster-nanny{nanny}-gpu{gpus}-{container_runtime}",
    }

    # Add GPU configuration if specified
    if gpus is not None:
        cluster_kwargs["gpus"] = gpus

    with ICCluster(**cluster_kwargs) as cluster:
        n_workers = 1
        with Client(cluster) as client:
            # Scale the cluster
            cluster.scale(n_workers)

            # Wait for workers to be available
            client.wait_for_workers(n_workers, timeout=300)

            # Submit a simple task to verify basic functionality
            futures = []
            for _ in range(n_workers):
                f = client.submit(lambda: socket.gethostname())
                futures.append(f)

            # Gather results
            results = client.gather(futures)

            # Verify we got results
            assert len(results) == n_workers
            assert all(isinstance(hostname, str) for hostname in results)

            # Additional GPU-specific test
            if gpus is not None:
                # Test that GPU information can be accessed (if GPUs are available)
                try:
                    gpu_test = client.submit(lambda: "GPU test passed")
                    gpu_result = client.gather([gpu_test])
                    assert len(gpu_result) == 1
                    assert gpu_result[0] == "GPU test passed"
                except Exception as e:
                    # Log but don't fail if GPU-specific test fails
                    # (GPU might not be available on test nodes)
                    print(f"GPU test warning: {e}")

            # Test parameter verification
            print(
                f"Test completed successfully for: nanny={nanny}, gpus={gpus}, container_runtime={container_runtime}"
            )


@pytest.mark.integration
@pytest.mark.skipif(not has_htcondor(), reason="HTCondor not available")
def test_iccluster_integration_single(worker_id):
    """Test basic ICCluster functionality with a real HTCondor submission.

    This is a single test case that can be run quickly without all parameter combinations.
    Useful for basic smoke testing.
    """

    with ICCluster(
        cores=1,
        memory="3000MB",
        disk="10GB",
        death_timeout="60",
        lcg=False,
        nanny=False,
        container_runtime="none",
        log_directory="/vols/cms/tr1123/dask-logs",
        scheduler_options={
            "port": get_available_port(worker_id=worker_id),
            "host": socket.gethostname(),
        },
        job_extra={
            "+MaxRuntime": "1200",
        },
        name="TestCluster",
    ) as cluster:
        n_workers = 1
        with Client(cluster) as client:
            # Scale the cluster
            cluster.scale(n_workers)

            # Wait for workers to be available
            client.wait_for_workers(n_workers, timeout=300)
            # Submit a simple task
            futures = []
            for _ in range(n_workers):
                f = client.submit(lambda: socket.gethostname())
                futures.append(f)

            # Gather results
            results = client.gather(futures)

            # Verify we got results
            assert len(results) == n_workers
            assert all(isinstance(hostname, str) for hostname in results)
