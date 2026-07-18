import os
import tempfile

from lilt.parser.dependency_resolver import DependencyResolver


def test_dependency_resolver_no_tex_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        resolver = DependencyResolver(tmpdir)
        assert resolver.resolve() == []


def test_dependency_resolver_finds_root_and_packages():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create root
        with open(os.path.join(tmpdir, "main.tex"), "w") as f:
            f.write(r"""\documentclass{article}
\usepackage{mypkg}
\input{chapter1}
""")

        # Create mypkg.sty
        with open(os.path.join(tmpdir, "mypkg.sty"), "w") as f:
            f.write(r"\newcommand{\ben}{\begin{eqnarray}}")

        # Create chapter1.tex
        with open(os.path.join(tmpdir, "chapter1.tex"), "w") as f:
            f.write(r"Hello World")

        resolver = DependencyResolver(tmpdir)
        files = resolver.resolve()

        assert len(files) == 3
        assert any(f.endswith("main.tex") for f in files)
        assert any(f.endswith("mypkg.sty") for f in files)
        assert any(f.endswith("chapter1.tex") for f in files)


def test_dependency_resolver_latex_out_mapping():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "book.tex"), "w") as f:
            f.write(r"\documentclass{book}\input{latex.out/chapter}")
        with open(os.path.join(tmpdir, "chapter.tex"), "w") as f:
            f.write("Chapter body")

        resolver = DependencyResolver(tmpdir)
        files = resolver.resolve_from(os.path.join(tmpdir, "book.tex"))

        assert any(f.endswith("chapter.tex") for f in files)
        assert any(f.endswith("book.tex") for f in files)


def test_dependency_resolver_fallback_multiple_roots():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "file1.tex"), "w") as f:
            f.write("Just text")
        with open(os.path.join(tmpdir, "file2.tex"), "w") as f:
            f.write("More text")

        resolver = DependencyResolver(tmpdir)
        files = resolver.resolve()

        assert len(files) == 2
        assert any(f.endswith("file1.tex") for f in files)
        assert any(f.endswith("file2.tex") for f in files)
