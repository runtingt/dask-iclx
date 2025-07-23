# dask-iclx

[![python version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/) [![codecov](https://codecov.io/github/runtingt/dask-iclx/branch/main/graph/badge.svg?token=ZWGLEIVTNG)](https://codecov.io/github/runtingt/dask-iclx) [![License](https://img.shields.io/badge/License-Apache_2.0-yellow.svg)](https://opensource.org/licenses/Apache-2.0)


Builds on top of Dask-Jobqueue to enable jobs to run on the IC HTCondor cluster.

## Summary

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

<!-- ## CERN extras

There are a few changes in the wrapper to address some of the particular features of the CERN
HTCondor cluster, but there are also a few changes to detail here. -->

<!-- ### Options

`lcg`: If set to `True` this will validate and use the LCG python environment per the managed [LCG](https://lcgdocs.web.cern.ch/lcgdocs/lcgreleases/introduction/)
releases. It will send the environment of the submitting scheduler to the batch worker node. DASK
normally requires that both the scheduler and the worker is the same python versions and libraries.
At CERN this would mean that you should, assuming say the default of `EL9` worker nodes, that
the scheduler is run on something like`lxplus.cern.ch`also running EL9`.
An example use would be to do the following before running dask:
```bash
$ . /cvmfs/sft.cern.ch/lcg/views/LCG_107/x86_64-el9-gcc14-opt/setup.sh
```

`container_runtime`: Can be set to `"singularity"` or `docker` or `"none"`. If a runtime is needed
for the worker, this selects which will be used for the `HTCondor` job the worker runs. In principle
it should not be necessary when using `lcg` and should therefore be set to `"none"`. Default though
is `"singularity"`.

`worker_image`: The image that will be used if `container_runtime` is defined to use one. The default
is defined in `jobqueue-cern.yaml`.

`batch_name`: Optionally set a string that will identify the jobs in `HTCondor`. The default is
`"dask-worker"` -->
