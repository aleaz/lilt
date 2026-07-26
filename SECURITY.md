# Security Policy

## Supported versions

Security fixes target the current Release Candidate line and the tip of `main`
when it tracks that line.

| Line | Supported |
|------|-----------|
| `v1.0.0-rc.2` / package `1.0.0rc2` | Yes |
| `main` (while tracking the RC line) | Yes |
| `v1.0.0-rc.1` / package `1.0.0rc1` | No (superseded by rc.2) |
| Older untagged 0.1.x tips | No (superseded by RC) |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Prefer **GitHub private vulnerability reporting** on this repository (Security tab),
or email **alejandroazario@gmail.com** with:

- A description of the issue and its impact
- Steps to reproduce (PoC if available)
- Affected version / commit if known (`lilt --version`)

You should receive an acknowledgment within a few days. We will coordinate a fix
and disclosure timeline with you before any public discussion.

For non-security bugs, use GitHub Issues on this repository.
