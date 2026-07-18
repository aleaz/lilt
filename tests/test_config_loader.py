"""Tests for typed configuration loading."""

import os
import tempfile

import pytest

from lilt.exceptions import ConfigurationError
from lilt.utils.config_loader import load_lilt_config
from lilt.utils.yaml_loader import load_yaml_config


def test_load_lilt_config_valid():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
        f.write(
            "project:\n  source_lang: English\nllm:\n  provider: openai\n  model: m\n"
        )
        path = f.name
    try:
        config = load_lilt_config(path)
        assert config.project.source_lang == "English"
        assert config.llm.provider == "openai"
    finally:
        os.remove(path)


def test_load_lilt_config_rejects_scalar_root():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
        f.write("hello\n")
        path = f.name
    try:
        with pytest.raises(ConfigurationError, match="must be a mapping"):
            load_lilt_config(path)
    finally:
        os.remove(path)


def test_load_lilt_config_rejects_llm_string():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
        f.write("llm: openai\n")
        path = f.name
    try:
        with pytest.raises(ConfigurationError):
            load_lilt_config(path)
    finally:
        os.remove(path)


def test_load_lilt_config_rejects_empty_root():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
        f.write("")
        path = f.name
    try:
        with pytest.raises(ConfigurationError, match="is empty"):
            load_lilt_config(path)
    finally:
        os.remove(path)


def test_load_lilt_config_rejects_null_document():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
        f.write("null\n")
        path = f.name
    try:
        with pytest.raises(ConfigurationError, match="is empty"):
            load_lilt_config(path)
    finally:
        os.remove(path)


def test_load_lilt_config_minimal_project_still_loads():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
        f.write("project:\n  source_lang: English\n  target_lang: Spanish\n")
        path = f.name
    try:
        config = load_lilt_config(path)
        assert config.project.target_lang == "Spanish"
    finally:
        os.remove(path)


def test_load_lilt_config_rejects_unset_env():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
        f.write("llm:\n  api_key: ${LILT_UNSET_TEST_KEY}\n")
        path = f.name
    try:
        with pytest.raises(ConfigurationError, match="LILT_UNSET_TEST_KEY"):
            load_yaml_config(path)
    finally:
        os.remove(path)
