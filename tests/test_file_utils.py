from lilt.utils.file_utils import read_text_file_resilient


def test_read_text_file_resilient_utf8(tmp_path):
    file_path = tmp_path / "test_utf8.tex"
    content = "Hello, world! 🌍"
    file_path.write_text(content, encoding="utf-8")

    assert read_text_file_resilient(file_path) == content


def test_read_text_file_resilient_latin1(tmp_path):
    file_path = tmp_path / "test_latin1.tex"
    # Create a string with characters that are valid in latin-1 but will fail strict utf-8 decoding
    # 0xe9 is 'é' in latin-1. In utf-8 it's an invalid continuation byte if standalone.
    with open(file_path, "wb") as f:
        f.write(b"Caf\xe9 and m\xe1s")

    content = read_text_file_resilient(file_path)
    assert content == "Café and más"
