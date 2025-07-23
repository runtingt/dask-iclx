import pytest
from unittest.mock import patch
from pyfakefs.fake_filesystem_unittest import Patcher
import warnings
from dask_iclx.cluster import (
    merge,
    check_job_script_prologue,
    get_xroot_url,
    ICJob,
    ICCluster,
)


class TestUtilityFunctions:
    """Test utility functions in cluster module."""

    def test_merge_empty_args(self):
        """Test merge function with empty arguments."""
        result = merge()
        assert result == {}

    def test_merge_single_dict(self):
        """Test merge function with single dictionary."""
        d1 = {"a": 1, "b": 2}
        result = merge(d1)
        assert result == d1

    def test_merge_multiple_dicts(self):
        """Test merge function with multiple dictionaries."""
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 3, "c": 4}
        d3 = {"c": 5, "d": 6}
        result = merge(d1, d2, d3)
        # Earlier definitions win
        expected = {"a": 1, "b": 2, "c": 4, "d": 6}
        assert result == expected

    def test_merge_with_none_values(self):
        """Test merge function with None values."""
        d1 = {"a": 1}
        d2 = None
        d3 = {"b": 2}
        result = merge(d1, d2, d3)
        expected = {"a": 1, "b": 2}
        assert result == expected


class TestJobScriptPrologue:
    """Test check_job_script_prologue function."""

    def test_empty_prologue(self):
        """Test with empty job script prologue."""
        assert not check_job_script_prologue("PATH", [])
        assert not check_job_script_prologue("PATH", None)

    def test_variable_found(self):
        """Test when variable is found in prologue."""
        prologue = [
            "export PYTHONHOME=/usr/local/bin/python",
            'export LD_LIBRARY_PATH="/usr/local/lib"',
            "export PATH=/usr/bin:/bin",
        ]
        assert check_job_script_prologue("PYTHONHOME", prologue)
        assert check_job_script_prologue("LD_LIBRARY_PATH", prologue)
        assert check_job_script_prologue("PATH", prologue)

    def test_variable_not_found(self):
        """Test when variable is not found in prologue."""
        prologue = [
            "export PYTHONHOME=/usr/local/bin/python",
            'export LD_LIBRARY_PATH="/usr/local/lib"',
        ]
        assert not check_job_script_prologue("NONEXISTENT", prologue)
        assert not check_job_script_prologue("PATH", prologue)

    def test_variable_with_whitespace(self):
        """Test variable detection with whitespace variations."""
        prologue = [
            " export   VAR1  =  value1",
            "\texport\tVAR2\t=\tvalue2",
            "  export VAR3= value3  ",
        ]
        assert check_job_script_prologue("VAR1", prologue)
        assert check_job_script_prologue("VAR2", prologue)
        assert check_job_script_prologue("VAR3", prologue)


class TestXrootUrl:
    """Test get_xroot_url function."""

    def test_valid_user_paths(self):
        """Test valid user paths."""
        test_cases = [
            "/eos/user/b/bejones/SWAN_projects",
            "/eos/home-b/bejones/SWAN_projects",
            "/eos/home-io3/b/bejones/SWAN_projects",
        ]
        expected = "root://eosuser.cern.ch//eos/user/b/bejones/SWAN_projects"

        for path in test_cases:
            result = get_xroot_url(path)
            assert result == expected

    def test_different_usernames(self):
        """Test different usernames."""
        path = "/eos/user/a/alice/data"
        expected = "root://eosuser.cern.ch//eos/user/a/alice/data"
        result = get_xroot_url(path)
        assert result == expected

    def test_nested_paths(self):
        """Test nested directory paths."""
        path = "/eos/user/x/xuser/deep/nested/path/file.txt"
        expected = "root://eosuser.cern.ch//eos/user/x/xuser/deep/nested/path/file.txt"
        result = get_xroot_url(path)
        assert result == expected

    def test_invalid_paths(self):
        """Test invalid paths that should return None."""
        invalid_paths = [
            "/invalid/path",
            "/eos/invalid/path",
            "/eos/user/",
            "/eos/user/b/",
            "not/absolute/path",
            "",
        ]

        for path in invalid_paths:
            result = get_xroot_url(path)
            assert result is None


class TestICJob:
    """Test ICJob class."""

    @patch("dask_jobqueue.htcondor.HTCondorJob.__init__")
    def test_icjob_init_default_disk(self, mock_super_init):
        """Test ICJob initialization with default disk calculation."""
        mock_super_init.return_value = None

        ICJob(cores=4)

        # Should calculate disk as cores * 20 GB
        mock_super_init.assert_called_once()
        args, kwargs = mock_super_init.call_args
        assert kwargs["disk"] == "80 GB"

    @patch("dask_jobqueue.htcondor.HTCondorJob.__init__")
    def test_icjob_init_custom_disk(self, mock_super_init):
        """Test ICJob initialization with custom disk."""
        mock_super_init.return_value = None

        ICJob(disk="50 GB")

        mock_super_init.assert_called_once()
        args, kwargs = mock_super_init.call_args
        assert kwargs["disk"] == "50 GB"

    @patch("dask_jobqueue.htcondor.HTCondorJob.__init__")
    def test_icjob_warnings_handling(self, mock_super_init):
        """Test that warnings are properly handled."""
        mock_super_init.return_value = None

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ICJob()
            # Should not raise any warnings due to filtering
            assert len(w) == 0

    def test_icjob_log_directory_stream_removal(self, fs):
        """Test that Stream_Output and Stream_Error are automatically removed when log_directory is set."""
        # Create ICJob with log_directory - this will run the actual ICJob.__init__ code
        fs.create_dir("/some/path")
        job = ICJob(log_directory="/some/path")

        # Verify that the ICJob.__init__ logic actually ran and removed the stream keys
        assert "Stream_Output" not in job.job_header_dict
        assert "Stream_Error" not in job.job_header_dict
        assert "Error" in job.job_header_dict
        assert "Log" in job.job_header_dict
        assert "LogDirectory" in job.job_header_dict


class TestICClusterInit:
    """Test ICCluster initialization."""

    @patch("dask_iclx.cluster.ICCluster._modify_kwargs")
    @patch("dask_jobqueue.HTCondorCluster.__init__")
    def test_image_type_deprecation_warning(self, mock_super_init, mock_modify_kwargs):
        """Test that image_type parameter raises deprecation warning."""
        mock_super_init.return_value = None
        mock_modify_kwargs.return_value = {}

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ICCluster(image_type="singularity")

            # Check that deprecation warning was raised
            assert any(
                issubclass(warning.category, DeprecationWarning) for warning in w
            )
            assert any("image_type" in str(warning.message) for warning in w)

    @patch("dask_iclx.cluster.ICCluster._modify_kwargs")
    @patch("dask_jobqueue.HTCondorCluster.__init__")
    @patch("sys.executable", "/invalid/python/path")
    def test_lcg_validation_error(self, mock_super_init, mock_modify_kwargs):
        """Test that LCG validation raises ValueError with invalid python path."""
        mock_super_init.return_value = None
        mock_modify_kwargs.return_value = {}

        with pytest.raises(ValueError) as excinfo:
            ICCluster(lcg=True)

        assert "You need to have loaded the LCG environment" in str(excinfo.value)

    @patch("dask_iclx.cluster.ICCluster._modify_kwargs")
    @patch("dask_jobqueue.HTCondorCluster.__init__")
    @patch(
        "sys.executable",
        "/cvmfs/sft.cern.ch/lcg/views/LCG_107/x86_64-el9-gcc14-opt/bin/python3",
    )
    def test_lcg_validation_success(self, mock_super_init, mock_modify_kwargs):
        """Test that LCG validation passes with valid python path."""
        mock_super_init.return_value = None
        mock_modify_kwargs.return_value = {}

        # Should not raise an exception
        ICCluster(lcg=True)

    @patch("dask_iclx.cluster.ICCluster._modify_kwargs")
    @patch("dask_jobqueue.HTCondorCluster.__init__")
    def test_default_worker_port_range(self, mock_super_init, mock_modify_kwargs):
        """Test default worker port range setting."""
        mock_super_init.return_value = None
        mock_modify_kwargs.return_value = {}

        ICCluster()

        # Check that _modify_kwargs was called with default port range
        mock_modify_kwargs.assert_called_once()
        args, kwargs = mock_modify_kwargs.call_args
        assert kwargs["worker_port_range"] == [60000, 60099]


class TestICClusterModifyKwargs:
    """Test ICCluster._modify_kwargs method."""

    @patch("dask.config.get")
    def test_modify_kwargs_basic(self, mock_config_get):
        """Test basic kwargs modification."""
        mock_config_get.side_effect = lambda key, default=None: {
            "jobqueue.ic.container-runtime": "singularity",
            "jobqueue.ic.worker-image": "/default/image",
            "jobqueue.ic.log-directory": None,
            "jobqueue.ic.job_extra_directives": {},
            "jobqueue.ic.job_extra": {},
            "jobqueue.ic.batch-name": "dask-worker",
            "jobqueue.ic.worker_extra_args": [],
        }.get(key)

        kwargs = {"cores": 2, "memory": "4GB"}
        result = ICCluster._modify_kwargs(
            kwargs,
            container_runtime="singularity",
            worker_image="custom/image",
            worker_port_range=[60000, 60099],
        )

        assert "job_extra_directives" in result
        assert result["job_extra_directives"]["universe"] == "vanilla"
        assert result["job_extra_directives"]["MY.SingularityImage"] == '"custom/image"'

    @patch("dask.config.get")
    def test_modify_kwargs_singularity(self, mock_config_get):
        """Test kwargs modification for singularity runtime."""
        mock_config_get.side_effect = lambda key, default=None: {
            "jobqueue.ic.container-runtime": "singularity",
            "jobqueue.ic.worker-image": "/default/image",
            "jobqueue.ic.log-directory": None,
            "jobqueue.ic.job_extra_directives": {},
            "jobqueue.ic.job_extra": {},
            "jobqueue.ic.batch-name": "dask-worker",
            "jobqueue.ic.worker_extra_args": [],
        }.get(key)

        kwargs = {}
        result = ICCluster._modify_kwargs(
            kwargs,
            container_runtime="singularity",
            worker_image="/cvmfs/image",
            worker_port_range=[60000, 60099],
        )

        assert result["job_extra_directives"]["universe"] == "vanilla"
        assert result["job_extra_directives"]["MY.SingularityImage"] == '"/cvmfs/image"'

    @patch("dask.config.get")
    def test_modify_kwargs_eos_log_directory(self, mock_config_get):
        """Test kwargs modification with EOS log directory."""
        mock_config_get.side_effect = lambda key, default=None: {
            "jobqueue.ic.container-runtime": "singularity",
            "jobqueue.ic.worker-image": "/default/image",
            "jobqueue.ic.log-directory": None,
            "jobqueue.ic.job_extra_directives": {},
            "jobqueue.ic.job_extra": {},
            "jobqueue.ic.batch-name": "dask-worker",
            "jobqueue.ic.worker_extra_args": [],
        }.get(key)

        kwargs = {"log_directory": "/eos/user/t/testuser/logs"}
        result = ICCluster._modify_kwargs(
            kwargs, container_runtime="singularity", worker_port_range=[60000, 60099]
        )

        expected_xroot = "root://eosuser.cern.ch//eos/user/t/testuser/logs"
        assert result["job_extra_directives"]["output_destination"] == expected_xroot
        assert (
            result["job_extra_directives"]["Output"]
            == "worker-$(ClusterId).$(ProcId).out"
        )

    @patch("dask.config.get")
    def test_modify_kwargs_gpus(self, mock_config_get):
        """Test kwargs modification with GPU requests."""
        mock_config_get.side_effect = lambda key, default=None: {
            "jobqueue.ic.container-runtime": "singularity",
            "jobqueue.ic.worker-image": "/default/image",
            "jobqueue.ic.log-directory": None,
            "jobqueue.ic.job_extra_directives": {},
            "jobqueue.ic.job_extra": {},
            "jobqueue.ic.batch-name": "dask-worker",
            "jobqueue.ic.worker_extra_args": [],
        }.get(key)

        kwargs = {}
        result = ICCluster._modify_kwargs(
            kwargs, gpus=2, worker_port_range=[60000, 60099]
        )

        assert result["job_extra_directives"]["request_gpus"] == "2"

    @patch("dask.config.get")
    def test_modify_kwargs_gpus_existing_env(self, mock_config_get):
        """Test kwargs modification with no GPUs, but existing environment variable."""
        mock_config_get.side_effect = lambda key, default=None: {
            "jobqueue.ic.container-runtime": "singularity",
            "jobqueue.ic.worker-image": "/default/image",
            "jobqueue.ic.log-directory": None,
            "jobqueue.ic.job_extra_directives": {},
            "jobqueue.ic.job_extra": {},
            "jobqueue.ic.batch-name": "dask-worker",
            "jobqueue.ic.worker_extra_args": [],
        }.get(key)

        kwargs = {"job_extra_directives": {"environment": "MY_ENV_VAR=1"}}
        result = ICCluster._modify_kwargs(kwargs, worker_port_range=[60000, 60099])

        # Get the environment variable from the modified kwargs
        env_vars = result["job_extra_directives"].get("environment", "").split(",")
        assert len(env_vars) == 2
        assert "MY_ENV_VAR=1" in env_vars
        assert "DASK_DISTRIBUTED__DIAGNOSTICS__NVML=False" in env_vars

    @patch("dask.config.get")
    def test_modify_kwargs_lcg_environment(self, mock_config_get):
        """Test kwargs modification with LCG environment."""
        mock_config_get.side_effect = lambda key, default=None: {
            "jobqueue.ic.container-runtime": "singularity",
            "jobqueue.ic.worker-image": "/default/image",
            "jobqueue.ic.log-directory": None,
            "jobqueue.ic.job_extra_directives": {},
            "jobqueue.ic.job_extra": {},
            "jobqueue.ic.batch-name": "dask-worker",
            "jobqueue.ic.worker_extra_args": [],
        }.get(key)

        kwargs = {}
        result = ICCluster._modify_kwargs(
            kwargs, lcg=True, worker_port_range=[60000, 60099]
        )

        assert result["job_extra_directives"]["getenv"] == "true"

    def test_modify_kwargs_spool_error(self):
        """Test that -spool option raises NotImplementedError."""
        kwargs = {"submit_command_extra": ["-spool"]}

        with pytest.raises(NotImplementedError) as excinfo:
            ICCluster._modify_kwargs(kwargs, worker_port_range=[60000, 60099])

        assert "'-spool' option is not supported" in str(excinfo.value)


# Pytest fixtures
@pytest.fixture
def fs():
    with Patcher() as patcher:
        yield patcher.fs
