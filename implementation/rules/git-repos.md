# Multi-Repo Topology — Push ALL on Session End

## The Repos

A scaffold typically spans multiple git repos with different visibility levels:

| Repo | Visibility | What Goes There |
|------|-----------|----------------|
| Primary (bots + scripts) | Private | Live code, configs, logs, rules, hooks |
| Knowledge vault (submodule) | Private | Vault notes, MOCs, session notes |
| Scaffold tools | Private | Standalone scaffold scripts (mirrored from primary) |
| Public research | PUBLIC | Sanitized methodology, measurements, papers |

## Push Order (every session end)

```bash
# 1. Knowledge vault (submodule — push first so parent ref is valid)
cd /path/to/knowledge && git add -A && git commit -m "session update" && git push

# 2. Primary repo (includes knowledge submodule ref)
cd /path/to/primary && git add -A && git commit -m "session update" && git push

# 3. Scaffold tools (copy updated scripts)
cd /path/to/scaffold-tools && cp /path/to/primary/scripts/{relevant_scripts}.py . && git add -A && git commit -m "sync from primary" && git push

# 4. Public research (periodic — sanitize first)
cd /path/to/public && git add -A && git commit -m "update" && git push
```

## Opsec Gate (public repo ONLY)
Before pushing to the public repo, grep for leaks:
```bash
grep -rnEi 'balance|\$[0-9]+|webhook|wallet|0x[0-9a-f]{8}|api.key|secret' /path/to/public/
```

Adapt the pattern list to your domain. The key categories to exclude:
- Account balances, position sizes, P&L numbers
- API keys, webhook URLs, wallet addresses
- Strategy parameters specific to your system
- Internal note titles and domain names

## Scaffold Tools Repo
This is a mirror of standalone scripts — the ones that work independently of the primary repo's config. Update it every session. It's easy to forget and lets the repos drift.
