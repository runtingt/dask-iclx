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


def get_available_port(good_port_range=(60000, 60099)):
    n_port = None
    for port in range(*good_port_range):
        if check_port(port):
            n_port = port
            break
    if n_port is None:
        raise RuntimeError(f"No available port found in range {good_port_range}")
    return n_port


@pytest.mark.integration
@pytest.mark.skipif(not has_htcondor(), reason="HTCondor not available")
def test_iccluster_basic_functionality():
    """Test basic ICCluster functionality with a real HTCondor submission.

    This test creates a cluster, scales it, and runs a simple task.
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
            "port": get_available_port(),
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
