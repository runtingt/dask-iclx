# dask-iclx

[![python version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/) [![Local tests](https://img.shields.io/endpoint?url=https%3A%2F%2Fwww.hep.ph.ic.ac.uk%2F~tr1123%2Fdask-iclx%2Flatest.json)](https://www.hep.ph.ic.ac.uk/~tr1123/dask-iclx/latest.html) [![codecov](https://codecov.io/github/runtingt/dask-iclx/branch/main/graph/badge.svg?token=ZWGLEIVTNG)](https://codecov.io/github/runtingt/dask-iclx) [![License](https://img.shields.io/badge/License-Apache_2.0-yellow.svg)](https://opensource.org/licenses/Apache-2.0)

Adapts the [dask-lxplus](https://github.com/cernops/dask-lxplus/) package to enable jobs to run on the IC HTCondor cluster.

## Usage

```python
from distributed import Client
from dask_iclx import ICCluster
import socket

with ICCluster(
    cores = 1,
    memory = '3000MB',
    disk = '10GB',
    death_timeout = '60',
    lcg = False,
    nanny = False,
    container_runtime = 'none',
    log_directory = '/vols/experiment/username/dask-logs',
    scheduler_options = {
        'port': 60000,
        'host': socket.gethostname(),
    },
    job_extra = {
        "+MaxRuntime": "1200",
    },
    name="ClusterName",
) as cluster:
    n_workers = 1
    with Client(cluster) as client:
        futures = []
        cluster.scale(n_workers)
        for _ in range(n_workers):
            f = client.submit(lambda: socket.gethostname())
            futures.append(f)
        print(client.gather(futures))  # ['lxb10.hep.ph.ic.ac.uk']
```

## IC/CERN extras

There are a few changes in the wrapper to address some of the particular features of the IC
HTCondor cluster, but there are also a few changes to detail here.

### Options

- `lcg`: If set to `True` this will validate and use the LCG python environment per the managed [LCG](https://lcgdocs.web.cern.ch/lcgdocs/lcgreleases/introduction/) releases. An example use would be to do the following before running:

    ```bash
    source /cvmfs/sft.cern.ch/lcg/views/LCG_107/x86_64-el9-gcc14-opt/setup.sh
    ```

- `container_runtime`: Can be set to `"singularity"` or `"none"`. If a runtime is needed for the worker, this selects which will be used for the `HTCondor` job the worker runs. In principle it should not be necessary when using `lcg` and should therefore be set to `"none"`. Default though is `"singularity"`.

- `worker_image`: The image that will be used if `container_runtime` is defined to use one. The default defined in `jobqueue-ic.yaml`.

- `name`: Optionally set a string that will identify the jobs in `HTCondor`.
