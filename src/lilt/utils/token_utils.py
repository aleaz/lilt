"""Token counting utilities using tiktoken."""

import tiktoken

_encoder: tiktoken.Encoding | None = None


def _resolve_encoder(model_name: str = "gpt-4o") -> tiktoken.Encoding:
    """Return a tiktoken encoder without requiring network access.

    ``encoding_for_model`` may download encodings (e.g. o200k_base) on first use.
    Fall back to the bundled ``cl100k_base`` encoding when lookup or download fails.
    """
    try:
        return tiktoken.encoding_for_model(model_name)
    except KeyError:
        pass
    except Exception:
        pass
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model_name: str = "gpt-4o") -> int:
    """Calculate the exact number of tokens for a given text using tiktoken."""
    global _encoder
    if _encoder is None:
        _encoder = _resolve_encoder(model_name)
    return len(_encoder.encode(text))
