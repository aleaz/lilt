## Description

Please include a summary of the change and which issue is fixed. Please also include relevant motivation and context.

Fixes # (issue)

## Type of change

Please delete options that are not relevant.

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Verification

Please describe the tests that you ran to verify your changes.

- [ ] `make check-all` passes successfully locally
- [ ] I have added tests that prove my fix is effective or that my feature works

## Checklist

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings in mypy or ruff
- [ ] If behavior in `src/lilt/` changed, the relevant L1 guide under `docs/architecture/` was updated (per [documentation update policy](../docs/architecture/README.md#documentation-update-policy))
- [ ] If operator-facing CLI or config changed, [docs/reference/](../docs/reference/cli.md) / guides under [docs/](../docs/README.md) were updated
- [ ] If a Known gap was resolved, it was removed from the guide (not left as history)
