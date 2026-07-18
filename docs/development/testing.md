# Testing

### Unit and Integration Tests

```bash
make test
# or
uv run pytest
uv run pytest tests/test_tm_repository.py -v
uv run pytest -k "workflow" -v
```

Test categories in `tests/`:

| Pattern | Category | Examples |
|---------|----------|----------|
| `test_*_parser*.py`, `test_validators.py` | Unit | Parser, validators |
| `test_tm_*.py`, `test_sync.py` | Integration | TM, sync, import/export |
| `test_e2e_pipeline.py`, `test_cli_*.py` | End-to-end / CLI | Full pipeline, CLI commands |
| `test_placeholder_persistence.py` | Integration | Masking roundtrip + workflow |

---

Large-scale empirical campaigns stay **outside** this repository; see [CONTRIBUTING.md](../../CONTRIBUTING.md).
