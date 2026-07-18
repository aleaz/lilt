import tempfile

from lilt.services.project_service import ProjectService


def test_init_writes_advanced_config_comments():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ProjectService(tmpdir)
        service.initialize_workspace()

        with open(service.config_path, encoding="utf-8") as f:
            content = f.read()

        assert "reflection_enabled" in content
        assert "prompt_dir" in content
        assert "protected_terms" in content
        assert "opaque_environments" in content
        assert "stages:" in content
        assert content.strip().startswith("project:")
