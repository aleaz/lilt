import os
import tempfile

import yaml
from typer.testing import CliRunner

from lilt.cli.main import app

runner = CliRunner()


def test_configure_infers_macro_arguments():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a mock latex file with an unknown macro
        tex_file = os.path.join(tmpdir, "test.tex")
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(r"\unknownmacro{some arg}")
            f.write("\n")
            f.write(r"\anotherunknown{arg1}{arg2}")

        # Create a basic lilt.yaml config
        config_file = os.path.join(tmpdir, ".lilt", "lilt.yaml")
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        initial_config = {
            "project": {"source_lang": "en", "target_lang": "es"},
            "llm": {"provider": "openai", "model": "test"},
        }
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(initial_config, f)

        # Run the configure command by changing dir
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(app, ["project", "configure", "."])
            assert result.exit_code == 0, (
                f"Command failed with {result.exit_code}. Output: {result.output}\nException: {result.exception}"
            )
            assert "Registered 2 macro(s)" in result.output

            # Verify the config has the inferred arguments
            with open(config_file, encoding="utf-8") as f:
                updated_config = yaml.safe_load(f)

            custom_macros = updated_config.get("parser", {}).get("custom_macros", [])
            assert len(custom_macros) == 2

            macro_dict = {m["name"]: m for m in custom_macros}
            assert "unknownmacro" in macro_dict
            assert macro_dict["unknownmacro"]["args"] == 1

            assert "anotherunknown" in macro_dict
            assert macro_dict["anotherunknown"]["args"] == 2
        finally:
            os.chdir(original_cwd)
