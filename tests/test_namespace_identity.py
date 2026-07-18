import os
import tempfile

from lilt.utils.namespace import derive_namespace, find_namespace_collisions


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


def test_find_namespace_collisions_double_underscore_encoding():
    with tempfile.TemporaryDirectory() as tmpdir:
        chapters = os.path.join(tmpdir, "chapters")
        os.makedirs(chapters)
        nested = os.path.join(chapters, "intro.tex")
        flat = os.path.join(tmpdir, "chapters__intro.tex")
        open(nested, "w").close()
        open(flat, "w").close()

        assert derive_namespace(tmpdir, nested) == derive_namespace(tmpdir, flat)
        collisions = find_namespace_collisions(tmpdir, nested)
        assert os.path.realpath(flat) in {os.path.realpath(p) for p in collisions}
        assert find_namespace_collisions(tmpdir, flat)
        other = os.path.join(tmpdir, "other.tex")
        open(other, "w").close()
        assert not find_namespace_collisions(tmpdir, other)
