"""YAML configuration loading with environment variable substitution."""

import os
import re
from typing import IO, Any

import yaml

from lilt.exceptions import ConfigurationError

# Matches ${ENV_VAR} or ${ENV_VAR:-default_value}
ENV_VAR_PATTERN = re.compile(r".*?\$\{([^}^{]+)\}.*?")


def _env_var_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> Any:
    """PyYAML constructor to resolve environment variables.

    Supports syntax:
    ${VAR_NAME}
    ${VAR_NAME:-default_value}
    """
    if not isinstance(node, yaml.ScalarNode):
        raise yaml.constructor.ConstructorError(
            None, None, f"expected a scalar node, but found {node.tag}", node.start_mark
        )
    value = loader.construct_scalar(node)
    matches = ENV_VAR_PATTERN.findall(value)

    if matches:
        full_value = value
        for g in matches:
            parts = g.split(":-", 1)
            env_var = parts[0]

            if len(parts) > 1:
                default = parts[1]
                env_val = os.getenv(env_var, default)
            else:
                env_val = os.getenv(env_var)
                if env_val is None:
                    raise ConfigurationError(
                        f"Environment variable '{env_var}' is referenced in lilt.yaml "
                        "but is not set. Use ${VAR:-default} or define it in .env."
                    )

            full_value = full_value.replace(f"${{{g}}}", env_val)
        return full_value

    return value


# Register the constructor globally for SafeLoader
yaml.add_implicit_resolver("!env_var", ENV_VAR_PATTERN, None, yaml.SafeLoader)
yaml.add_constructor("!env_var", _env_var_constructor, yaml.SafeLoader)


def load_yaml_config(file_path_or_stream: IO[Any] | str) -> dict[str, Any]:
    """
    Safely load a YAML configuration file with environment variable interpolation support.

    Args:
        file_path_or_stream: A file object or a string path to the YAML file.

    Returns:
        A dictionary containing the parsed YAML configuration.

    Raises:
        ConfigurationError: If the YAML file is malformed.
        OSError: If the file cannot be read.
    """
    try:
        if isinstance(file_path_or_stream, str):
            with open(file_path_or_stream, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        else:
            data = yaml.safe_load(file_path_or_stream)
    except yaml.YAMLError as e:
        filename = (
            file_path_or_stream
            if isinstance(file_path_or_stream, str)
            else getattr(file_path_or_stream, "name", "Stream")
        )
        raise ConfigurationError(
            f"YAML configuration syntax error in '{filename}':\n{e}"
        ) from e

    return data or {}
