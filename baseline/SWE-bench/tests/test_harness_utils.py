import unittest
from unittest.mock import MagicMock, patch
from swebench.harness.utils import run_threadpool
from swebench.harness.test_spec.python import clean_environment_yml


class UtilTests(unittest.TestCase):
    @patch("swebench.harness.utils.tqdm")
    def test_pbar_updates_correctly_with_all_failures(self, mock_tqdm):
        # Create mock progress bar
        mock_pbar = MagicMock()

        # Configure mock chain
        mock_tqdm.return_value = mock_pbar
        mock_pbar.__enter__.return_value = mock_pbar
        mock_pbar.__exit__.return_value = None

        def failing_func(_):
            raise ValueError("Test error")

        # Run the function
        payloads = [(1,), (2,), (3,)]
        succeeded, failed = run_threadpool(failing_func, payloads, max_workers=2)

        # Verify mock_pbar was used correctly
        self.assertEqual(3, len(failed))
        self.assertEqual(3, mock_pbar.update.call_count)
        self.assertEqual(3, mock_pbar.set_description.call_count)
        mock_pbar.set_description.assert_called_with("0 ran successfully, 3 failed")

    def test_environment_yml_cleaner(self):
        """
        We want to make sure that our cleaner only modifies the pip section of the environment.yml
        and that it does not modify the other dependencies sections.

        We expect "types-pkg_resources" to be replaced with "types-setuptools" in the pip section.
        """
        env_yaml = (
            "# To set up a development environment using conda run:\n"
            "#\n"
            "#   conda env create -f environment.yml\n"
            "#   conda activate mpl-dev\n"
            '#   pip install --verbose --no-build-isolation --editable ".[dev]"\n'
            "#\n"
            "---\n"
            "name: matplotlib-master\n"
            "channels:\n"
            "  - conda-forge\n"
            "dependencies:\n"
            "  # runtime dependencies\n"
            "  - cairocffi\n"
            "  - c-compiler\n"
            "  - cxx-compiler\n"
            "  - contourpy>=1.0.1\n"
            "  - cycler>=0.10.0\n"
            "  - fonttools>=4.22.0\n"
            "  - pip\n"
            "  - pip:\n"
            "    - mpl-sphinx-theme~=3.8.0\n"
            "    - sphinxcontrib-video>=0.2.1\n"
            "    - types-pkg_resources\n"
            "    - pikepdf\n"
            "  # testing\n"
            "  - types-pkg_resources\n"
            "  - black<24\n"
            "  - coverage\n"
            "  - tox\n"
        )
        expected_env_yaml = (
            "# To set up a development environment using conda run:\n"
            "#\n"
            "#   conda env create -f environment.yml\n"
            "#   conda activate mpl-dev\n"
            '#   pip install --verbose --no-build-isolation --editable ".[dev]"\n'
            "#\n"
            "---\n"
            "name: matplotlib-master\n"
            "channels:\n"
            "  - conda-forge\n"
            "dependencies:\n"
            "  # runtime dependencies\n"
            "  - cairocffi\n"
            "  - c-compiler\n"
            "  - cxx-compiler\n"
            "  - contourpy>=1.0.1\n"
            "  - cycler>=0.10.0\n"
            "  - fonttools>=4.22.0\n"
            "  - pip\n"
            "  - pip:\n"
            "    - mpl-sphinx-theme~=3.8.0\n"
            "    - sphinxcontrib-video>=0.2.1\n"
            "    - types-setuptools\n"  # should be replaced
            "    - pikepdf\n"
            "  # testing\n"
            "  - types-pkg_resources\n"  # should not be modified
            "  - black<24\n"
            "  - coverage\n"
            "  - tox\n"
        )
        cleaned = clean_environment_yml(env_yaml)
        self.assertEqual(cleaned, expected_env_yaml)
