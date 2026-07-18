import os
import tempfile

import yaml

from lilt.parser.ast_parser import LatexParser


def test_semantic_alias_matching():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "lilt.yaml")
        config = {
            "parser": {
                "environment_aliases": {
                    "ben": {"type": "begin", "env": "eqnarray"},
                    "een": {"type": "end", "env": "eqnarray"},
                }
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        parser = LatexParser(config_path=config_path)

        text = r"Here is some text \ben a + b = c \een more text"
        segments = parser.parse_text(text)

        assert len(segments) == 1
        # The block should be masked as ENV
        assert '<env id="1"/>' in segments[0].masked_text
        assert "a + b = c" not in segments[0].masked_text


def test_semantic_alias_fallback_mixed():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "lilt.yaml")
        config = {
            "parser": {
                "environment_aliases": {
                    "ben": {"type": "begin", "env": "eqnarray"},
                    "een": {"type": "end", "env": "eqnarray"},
                }
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        parser = LatexParser(config_path=config_path)

        # Using \end{eqnarray} instead of \een
        text = r"Here is some text \ben a + b = c \end{eqnarray} more text"
        segments = parser.parse_text(text)

        assert len(segments) == 1
        assert '<env id="1"/>' in segments[0].masked_text
        assert "a + b = c" not in segments[0].masked_text


def test_semantic_alias_robustness_with_syntax_errors():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "lilt.yaml")
        config = {
            "parser": {
                "environment_aliases": {
                    "ben": {"type": "begin", "env": "eqnarray"},
                }
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        parser = LatexParser(config_path=config_path)

        # Using \end{eqnarray} but with a syntax error \end{foo} in the middle!
        text = r"Here is some text \ben a + \end{foo} b = c \end{eqnarray} more text"
        segments = parser.parse_text(text)

        assert len(segments) == 1
        assert '<env id="1"/>' in segments[0].masked_text
        assert "a +" not in segments[0].masked_text
        assert "b = c" not in segments[0].masked_text
