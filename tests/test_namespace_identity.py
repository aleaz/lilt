import os
import tempfile

from lilt.utils.namespace import derive_namespace


def test_derive_namespace_root_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "main.tex")
        open(tex_path, "w").close()
        assert derive_namespace(tmpdir, tex_path) == "main"


def test_derive_namespace_nested_files_distinct():
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_a = os.path.join(tmpdir, "chapters")
        dir_b = os.path.join(tmpdir, "appendix")
        os.makedirs(dir_a)
        os.makedirs(dir_b)
        file_a = os.path.join(dir_a, "intro.tex")
        file_b = os.path.join(dir_b, "intro.tex")
        open(file_a, "w").close()
        open(file_b, "w").close()

        ns_a = derive_namespace(tmpdir, file_a)
        ns_b = derive_namespace(tmpdir, file_b)
        assert ns_a == "chapters__intro"
        assert ns_b == "appendix__intro"
        assert ns_a != ns_b


def test_derive_namespace_relative_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        original = os.getcwd()
        try:
            os.chdir(tmpdir)
            nested = os.path.join("parts", "chapter.tex")
            os.makedirs("parts")
            open(nested, "w").close()
            assert derive_namespace(tmpdir, nested) == "parts__chapter"
        finally:
            os.chdir(original)
