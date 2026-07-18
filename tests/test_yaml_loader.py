import os
import tempfile

import pytest

from lilt.exceptions import ConfigurationError
from lilt.utils.yaml_loader import load_yaml_config


def test_load_yaml_config_valid():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
        f.write("project:\n  source_lang: English\n  target_lang: Spanish\n")
        f_name = f.name

    try:
        data = load_yaml_config(f_name)
        assert data["project"]["source_lang"] == "English"
        assert data["project"]["target_lang"] == "Spanish"
    finally:
        os.remove(f_name)


def test_load_yaml_config_invalid_syntax():
    # Write a malformed YAML file with a syntax error
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
        f.write("project:\n  source_lang: 'English'  bad_key: value\n")
        f_name = f.name

    try:
        with pytest.raises(ConfigurationError) as exc_info:
            load_yaml_config(f_name)
        assert "YAML configuration syntax error" in str(exc_info.value)

    finally:
        os.remove(f_name)


def test_load_yaml_config_env_interpolation():
    os.environ["LILT_TEST_VAR"] = "InterpolatedValue"
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
        f.write("test_key: ${LILT_TEST_VAR}\n")
        f_name = f.name

    try:
        data = load_yaml_config(f_name)
        assert data["test_key"] == "InterpolatedValue"
    finally:
        os.remove(f_name)
        del os.environ["LILT_TEST_VAR"]
