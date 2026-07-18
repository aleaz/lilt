import subprocess
from unittest.mock import MagicMock, patch

import pytest

from lilt.exceptions import BuildError
from lilt.services.pipeline_service import PipelineService


def test_compile_pdf_success(tmpdir):
    service = PipelineService(str(tmpdir))

    # Mock subprocess.run and os.path.exists
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="Compilation successful.")

        with patch("os.path.exists") as mock_exists:
            # Tell the system that NO bibliography files exist
            mock_exists.return_value = False

            service.compile_pdf("main.tex", str(tmpdir))

            # pdflatex should only run ONCE if there are no citations/cross-references needed
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert args[0][0] == "pdflatex"
            assert "main.tex" in args[0]
            assert kwargs["cwd"] == str(tmpdir)
            assert "TEXINPUTS" in kwargs["env"]


def test_compile_pdf_with_biber(tmpdir):
    service = PipelineService(str(tmpdir))

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="Compilation successful.")

        with patch("os.path.exists") as mock_exists:
            # Tell the system that .bcf exists (meaning biber is required)
            def exists_side_effect(path):
                return bool(path.endswith(".bcf"))

            mock_exists.side_effect = exists_side_effect

            service.compile_pdf("main.tex", str(tmpdir))

            # Should be called 3 times: pdflatex -> biber -> pdflatex
            assert mock_run.call_count == 3
            assert mock_run.call_args_list[0][0][0][0] == "pdflatex"
            assert mock_run.call_args_list[1][0][0][0] == "biber"
            assert mock_run.call_args_list[2][0][0][0] == "pdflatex"


def test_compile_pdf_failure(tmpdir):
    service = PipelineService(str(tmpdir))

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "pdflatex", output="Fatal error"
        )

        with pytest.raises(BuildError) as excinfo:
            service.compile_pdf("main.tex", str(tmpdir))

        assert "pdflatex failed" in str(excinfo.value)
        assert "Fatal error" in str(excinfo.value)
