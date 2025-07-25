import logging

from collections import ChainMap
import warnings
import dask
from dask_jobqueue import HTCondorCluster
from dask_jobqueue.htcondor import HTCondorJob
import re
import sys


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def merge(*args):
    # This will merge dicts, but earlier definitions win
    return dict(ChainMap(*filter(None, args)))


def check_job_script_prologue(var, job_script_prologue):
    """
    Check if an environment variable is set in job_script_prologue.

    Parameters
    ----------
    var : str
        Name of the environment variable to check.

    job_script_prologue: list of k=v strings

    Returns
    -------
    bool
        True if the environment variable is set.
    """
    if not job_script_prologue:
        return False
    matches = list(
        filter(lambda x: re.match(rf"\W*export\s+{var}\s*=.*", x), job_script_prologue)
    )
    if matches:
        return True
    return False


def get_xroot_url(eos_path):
    """
    Return the xroot url for a given eos path.

    Parameters
    ----------
    eos_path : str
        Path in eos, ie /eos/user/b/bejones/SWAN_projects

    Returns
    -------
    str
        The xroot url for the file ie root://eosuser.cern.ch//eos/user/b/bejones/SWAN_projects
    """
    # note we have to support the following eos paths:
    # /eos/user/b/bejones/foo/bar
    # /eos/home-b/bejones/foo/bar
    # /eos/home-io3/b/bejones/foo/bar
    # Also note this only supports eoshome.cern.ch at this point
    eos_match = re.match(
        r"^/eos/(?:home|user)(?:-\w+)?(?:/\w)?/(?P<username>\w+)(?P<path>/.+)$",
        eos_path,
    )
    if not eos_match:
        return None
    return f"root://eosuser.cern.ch//eos/user/{eos_match.group('username')[:1]}/{eos_match.group('username')}{eos_match.group('path')}"


class ICJob(HTCondorJob):
    config_name = "ic"

    def __init__(self, scheduler=None, name=None, disk=None, **base_class_kwargs):
        if disk is None:
            num_cores = base_class_kwargs.get("cores", 1)
            disk = f"{int(num_cores) * 20} GB"

        warnings.simplefilter(action="ignore", category=FutureWarning)

        super().__init__(scheduler=scheduler, name=name, disk=disk, **base_class_kwargs)

        warnings.resetwarnings()

        if hasattr(self, "log_directory"):
            self.job_header_dict.pop("Stream_Output", None)
            self.job_header_dict.pop("Stream_Error", None)


class ICCluster(HTCondorCluster):
    __doc__ = (
        HTCondorCluster.__doc__
        + """
    A customized :class:`dask_jobqueue.HTCondorCluster` subclass for spawning Dask workers in the IC HTCondor pool

    It provides the customizations and submit options required for the IC pool.

    Additional CERN parameters:
    worker_image: The container to run the Dask workers inside. Defaults to:
    ``"/cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/batch-team/dask-lxplus/lxdask-al9:latest"``
    container_runtime: If a container runtime is not required, choose ``none``, otherwise ``singularity`` (the default).
    If using ``lcg`` it shouldn't be necessary as long as the scheduler side matches the client, which
    at CERN means the lxplus version corresponding to the lxbatch version.
    lcg: If set to ``True`` will use the LCG environment in CVMFS and use that to run the python interpreter on server
    and client. Needs to be sourced before running the python interpreter. Defaults to False.
    worker_port_range: The range of ports to use for the workers. If None, defaults to ``[60000, 60999]``.
    """
    )
    config_name = "ic"
    job_cls = ICJob

    def __init__(
        self,
        *,
        worker_image=None,
        image_type=None,
        container_runtime=None,
        gpus=None,
        lcg=False,
        worker_port_range=None,
        **base_class_kwargs,
    ):
        """
        :param: worker_image: The container image to run the Dask workers inside.Defaults to the singularity image. Note n/a in case of cvmfs
        :param: container_runtime: The container runtime to run the Dask workers inside. Either ``singularity`` or ``none``, defaults to singularity.
        :param: disk: The amount of disk to request. Defaults to 20 GiB / core
        :param: gpus: The number of GPUs to request. Defaults to ``0``.
        :param lcg: If True, use the LCG environment from cvmfs. Please note you need to haveloaded the environment before running the python interpreter. Defaults to False.
        :param worker_port_range: The range of ports to use for the workers. If None, defaults to ``[60000, 60999]``.
        :param base_class_kwargs: Additional keyword arguments like ``cores`` or ``memory`` to pass to `dask_jobqueue.HTCondorCluster`.
        """

        if image_type is not None:
            warnings.warn(
                "The `image_type` parameter is deprecated. Please use `container_runtime` instead.",
                DeprecationWarning,
            )
            container_runtime = container_runtime or image_type

        if lcg:
            if not re.match(
                "^/cvmfs/sft(?:-nightlies)?.cern.ch/lcg/.+/python[2,3]?$",
                sys.executable,
            ):
                raise ValueError(
                    f"You need to have loaded the LCG environment before running the python interpreter. Current interpreter: {sys.executable}"
                )

        worker_port_range = worker_port_range or [60000, 60099]

        base_class_kwargs = ICCluster._modify_kwargs(
            base_class_kwargs,
            worker_image=worker_image,
            container_runtime=container_runtime,
            gpus=gpus,
            lcg=lcg,
            worker_port_range=worker_port_range,
        )

        warnings.simplefilter(action="ignore", category=FutureWarning)
        warnings.filterwarnings(
            "ignore", message=".*Using a temporary security object.*"
        )

        super().__init__(**base_class_kwargs)

        warnings.resetwarnings()

    @classmethod
    def _modify_kwargs(
        cls,
        kwargs,
        *,
        worker_image=None,
        container_runtime=None,
        gpus=None,
        lcg=False,
        worker_port_range=None,
    ):
        """
        This method implements the special modifications to adapt dask-jobqueue to run on the CERN cluster.

        See the class __init__ for the details of the arguments.
        """
        modified = kwargs.copy()

        container_runtime = container_runtime or dask.config.get(
            f"jobqueue.{cls.config_name}.container-runtime"
        )
        worker_image = worker_image or dask.config.get(
            f"jobqueue.{cls.config_name}.worker-image"
        )

        logdir = modified.get(
            "log_directory",
            dask.config.get(f"jobqueue.{cls.config_name}.log-directory", None),
        )
        if logdir:
            modified["log_directory"] = logdir
        xroot_url = (
            get_xroot_url(modified["log_directory"])
            if logdir and modified["log_directory"].startswith("/eos/")
            else None
        )

        modified["job_extra_directives"] = merge(
            {"universe": "vanilla"},
            {"MY.SingularityImage": f'"{worker_image}"'}
            if container_runtime == "singularity"
            else None,
            {"request_gpus": str(gpus)} if gpus is not None else None,
            {"MY.IsDaskWorker": "true"},
            # getenv justified in case of LCG as both sides have to be the same environment
            {"getenv": "true"} if lcg else None,
            {"output_destination": f"{xroot_url}"} if xroot_url else None,
            {"Output": "worker-$(ClusterId).$(ProcId).out"} if xroot_url else None,
            {"Error": "worker-$(ClusterId).$(ProcId).err"} if xroot_url else None,
            {"Log": "worker-$(ClusterId).log"} if xroot_url else None,
            {"MY.SpoolOnEvict": False} if logdir else None,
            # extra user input
            kwargs.get(
                "job_extra_directives",
                dask.config.get(f"jobqueue.{cls.config_name}.job_extra_directives"),
            ),
            kwargs.get(
                "job_extra", dask.config.get(f"jobqueue.{cls.config_name}.job_extra")
            ),
            # never transfer files
            {"transfer_output_files": '""'},
        )

        # We don't support -spool (for now, at least)
        submit_command_extra = kwargs.get("submit_command_extra", [])
        if "-spool" in submit_command_extra:
            raise NotImplementedError(
                "The '-spool' option is not supported with ICCluster"
            )

        # Add extra args
        modified["worker_extra_args"] = [
            *kwargs.get(
                "worker_extra_args",
                dask.config.get(f"jobqueue.{cls.config_name}.worker_extra_args"),
            ),
            f"--worker-port {worker_port_range[0]}:{worker_port_range[-1]}",
        ]

        # Handle GPUs
        existing_env = (
            kwargs.get("job_extra_directives", {})
            or dask.config.get(f"jobqueue.{cls.config_name}.job_extra_directives", {})
        ).get("environment", "")
        nvml_env = "DASK_DISTRIBUTED__DIAGNOSTICS__NVML=False"
        if gpus is None:
            # Sometimes we can land on a GPU node, even if we don't request GPUs
            # To avoid pynvml.nvml.NVMLError_LibRmVersionMismatch, we turn off GPU monitoring
            if existing_env:
                combined_env = f"{existing_env},{nvml_env}"
            else:
                combined_env = nvml_env

            # Strip the environment from the old job_extra_directives
            old_env = modified.get("job_extra_directives", {}).get("environment", "")
            if old_env:
                del modified["job_extra_directives"]["environment"]

            # Add the new environment variable
            modified["job_extra_directives"] = merge(
                modified.get("job_extra_directives", {}),
                {"environment": combined_env},
            )

        # Enforce security
        modified["security"] = True

        return modified
