# OPENCLAW_RETROFIT.md
## Retrofit checklist for reconnecting OpenBrain after an OpenClaw upgrade

This document explains how to reconnect and validate the **OpenBrain Gateway** after upgrading **OpenClaw**.

The goal is to keep OpenBrain **external**, **upgrade-safe**, and easy to reattach without changing the canonical memory store.

---

# 1. Architecture reminder

OpenBrain is intentionally **not embedded inside OpenClaw core**.

## System roles

- **OpenClaw**
  - Telegram/chat interface
  - assistant runtime
  - tool execution
  - session handling

- **OpenBrain Gateway**
  - canonical local memory service
  - local memory capture/search
  - Brian Madden external knowledge connector
  - federated retrieval
  - promotion of external insights into local memory

- **Postgres + pgvector**
  - structured long-term canonical memory

- **Markdown archive**
  - human-readable memory archive

This separation means OpenClaw can be upgraded independently, then reconnected to the same OpenBrain service.

---

# 2. What must survive an OpenClaw upgrade

These components are outside OpenClaw and should remain unchanged:

- `/opt/openbrain/`
- Postgres database
- OpenBrain archive under `/opt/openbrain/archive/`
- Brian mirror repo under `/opt/openbrain/external/brianmadden-ai`
- `openbrainctl` symlink in `/usr/local/bin/openbrainctl`
- systemd service: `openbrain-gateway`

Do **not** delete or rebuild these just because OpenClaw was upgraded.

---

# 3. Where the OpenBrain skill lives

The OpenClaw skill bridge is stored in the workspace skill path:

```bash
~/.openclaw/workspace/skills/openbrain-bridge/SKILL.md
```

## Expected structure

```bash
~/.openclaw/workspace/skills/openbrain-bridge/
└── SKILL.md
```

## If the skill is missing after upgrade

Recreate it with:

```bash
mkdir -p ~/.openclaw/workspace/skills/openbrain-bridge
cp /opt/openbrain/openclaw/SKILL.md ~/.openclaw/workspace/skills/openbrain-bridge/SKILL.md
```

Then verify:

```bash
ls -R ~/.openclaw/workspace/skills/openbrain-bridge
```

Expected:

```bash
SKILL.md
```

---

# 4. Which OpenClaw config/settings matter

The most important setting is that OpenClaw must have access to a tool surface that can run:

```bash
openbrainctl
```

This means `exec` (or equivalent local command execution) must still be available.

## Important OpenClaw release behavior
Recent OpenClaw releases may default new installs to a **messaging-focused tool profile**.

That can remove access to `exec` unless you explicitly enable a broader profile.

## Minimum required setting

Use a profile that includes command execution, such as:

```bash
openclaw config set tools.profile coding
```

Then validate:

```bash
openclaw config validate
```

If a future OpenClaw release changes profile names or tool grouping, confirm that local command execution is still available.

---

# 5. OpenBrain service paths that matter

## Main service root
```bash
/opt/openbrain
```

## Environment file
```bash
/opt/openbrain/.env
```

## CLI entrypoint
```bash
/usr/local/bin/openbrainctl
```

## Gateway systemd service
```bash
openbrain-gateway
```

## Archive path
```bash
/opt/openbrain/archive
```

## Brian mirrored repo
```bash
/opt/openbrain/external/brianmadden-ai
```

---

# 6. What to validate immediately after an OpenClaw upgrade

After every OpenClaw upgrade, check these in order.

---

## Step A — Confirm OpenBrain is still running

```bash
sudo systemctl status openbrain-gateway --no-pager
```

Expected:
- service is active/running

If needed:

```bash
sudo systemctl restart openbrain-gateway
```

Then verify health:

```bash
curl http://127.0.0.1:8094/health
```

Expected:

```json
{"ok":true,"service":"openbrain-gateway"}
```

---

## Step B — Confirm `openbrainctl` is still callable

```bash
which openbrainctl
openbrainctl --help
```

Expected:
- `which` returns `/usr/local/bin/openbrainctl`
- help text prints successfully

If not, restore the symlink:

```bash
sudo ln -sf /opt/openbrain/.venv/bin/openbrainctl /usr/local/bin/openbrainctl
```

Then re-test:

```bash
which openbrainctl
openbrainctl --help
```

---

## Step C — Confirm OpenClaw config is still valid

```bash
openclaw config validate
```

If validation fails, fix the config before testing anything else.

---

## Step D — Confirm the OpenBrain skill still exists

```bash
ls ~/.openclaw/workspace/skills/openbrain-bridge/SKILL.md
```

If it is missing:

```bash
mkdir -p ~/.openclaw/workspace/skills/openbrain-bridge
cp /opt/openbrain/openclaw/SKILL.md ~/.openclaw/workspace/skills/openbrain-bridge/SKILL.md
```

---

## Step E — Confirm OpenClaw still has a profile that can execute commands

Reapply if needed:

```bash
openclaw config set tools.profile coding
openclaw config validate
```

Then restart OpenClaw using your normal runtime method.

If using a user service:

```bash
systemctl --user restart openclaw-gateway
```

---

# 7. Post-upgrade functional tests

Run these in order.

---

## Test 1 — Local canonical memory retrieval

### Direct CLI test
```bash
openbrainctl search "What architecture did Peter choose for this system?"
```

Expected:
- returns local memory results from canonical memory

### OpenClaw chat test
Ask OpenClaw:

> What architecture did I choose for this system?

Expected:
- OpenClaw uses local memory and answers correctly

---

## Test 2 — Local capture still works

### Direct CLI capture
```bash
openbrainctl capture "Post-upgrade validation succeeded and OpenClaw was successfully reconnected to OpenBrain."
```

Then search for it:

```bash
openbrainctl search "post-upgrade validation"
```

Expected:
- the new memory is returned

### OpenClaw capture test
Tell OpenClaw:

> Remember that the post-upgrade OpenBrain reconnection succeeded.

Then ask:

> What do you remember about the upgrade validation?

Expected:
- OpenClaw should be able to retrieve the saved fact

---

## Test 3 — Brian-only retrieval

### Direct CLI
```bash
openbrainctl brian "AI and the future of knowledge work"
```

Expected:
- returns Brian Madden results from the mirrored repo and/or connector

### OpenClaw chat
Ask:

> What does Brian Madden say about knowledge work and AI?

Expected:
- Brian results are used
- answer is clearly based on Brian’s published material

---

## Test 4 — Federated retrieval

### Direct CLI
```bash
openbrainctl federated "Compare my architecture with Brian Madden's perspective"
```

Expected:
- output contains:
  - local results
  - Brian results
  - combined results

### OpenClaw chat
Ask:

> Compare my current system design with Brian Madden’s approach.

Expected:
- OpenClaw can synthesize local + Brian information

---

## Test 5 — Source status

```bash
curl http://127.0.0.1:8094/sources/status
```

Expected:
- local source OK
- Brian repo available
- Brian MCP state reported clearly

This helps distinguish between:
- OpenBrain service failure
- Brian source failure
- OpenClaw integration failure

---

# 8. If the Brian mirrored repo is stale after upgrade

Refresh it:

```bash
/opt/openbrain/scripts/update-brian-repo.sh
```

If that script is missing or not executable:

```bash
chmod +x /opt/openbrain/scripts/update-brian-repo.sh
/opt/openbrain/scripts/update-brian-repo.sh
```

Then retest:

```bash
openbrainctl brian "AI and the future of knowledge work"
```

---

# 9. If `openbrainctl` works but OpenClaw does not use it

This usually means one of:

1. the OpenBrain skill is missing
2. the active tool profile no longer exposes local command execution
3. OpenClaw’s instructions no longer strongly encourage memory search/capture behavior
4. the runtime was restarted without reloading the workspace/skill state

## Recovery steps

### A. Reinstall the skill
```bash
mkdir -p ~/.openclaw/workspace/skills/openbrain-bridge
cp /opt/openbrain/openclaw/SKILL.md ~/.openclaw/workspace/skills/openbrain-bridge/SKILL.md
```

### B. Reapply tool profile
```bash
openclaw config set tools.profile coding
openclaw config validate
```

### C. Restart OpenClaw
```bash
systemctl --user restart openclaw-gateway
```

### D. Re-test in chat
Ask OpenClaw explicitly:

> Use the OpenBrain Bridge skill to search for my selected architecture.

If needed, make it even more explicit:

> Run `openbrainctl search "selected architecture"` and summarize the result.

---

# 10. If OpenClaw upgrades change tool behavior

The design assumption is:

- OpenBrain remains external
- the only fragile boundary is the bridge from OpenClaw to `openbrainctl`

If a future OpenClaw version changes:
- tool profiles
- command execution
- skill loading behavior
- plugin/bridge policies

then the likely retrofit is **only**:
- restore skill
- restore exec-capable tool profile
- validate `openbrainctl`
- rerun functional tests

It should **not** require:
- changing the OpenBrain database
- changing archive files
- changing Brian repo mirror
- migrating canonical memory

---

# 11. Suggested post-upgrade command checklist

Use this exact sequence after future upgrades:

```bash
sudo systemctl status openbrain-gateway --no-pager
curl http://127.0.0.1:8094/health
which openbrainctl
openbrainctl --help
openclaw config validate
ls ~/.openclaw/workspace/skills/openbrain-bridge/SKILL.md
openclaw config set tools.profile coding
openclaw config validate
systemctl --user restart openclaw-gateway
openbrainctl search "What architecture did Peter choose for this system?"
openbrainctl brian "AI and the future of knowledge work"
openbrainctl federated "Compare my architecture with Brian Madden's perspective"
curl http://127.0.0.1:8094/sources/status
```

If all of those pass, the retrofit is complete.

---

# 12. Quick recovery commands

## Restore skill
```bash
mkdir -p ~/.openclaw/workspace/skills/openbrain-bridge
cp /opt/openbrain/openclaw/SKILL.md ~/.openclaw/workspace/skills/openbrain-bridge/SKILL.md
```

## Restore CLI symlink
```bash
sudo ln -sf /opt/openbrain/.venv/bin/openbrainctl /usr/local/bin/openbrainctl
```

## Restart OpenBrain
```bash
sudo systemctl restart openbrain-gateway
```

## Restart OpenClaw
```bash
systemctl --user restart openclaw-gateway
```

## Refresh Brian mirror
```bash
/opt/openbrain/scripts/update-brian-repo.sh
```

---

# 13. Success criteria

The retrofit is successful if:

- OpenBrain service is healthy
- `openbrainctl` is callable
- OpenBrain skill exists in the OpenClaw workspace
- OpenClaw can capture memory
- OpenClaw can search local canonical memory
- OpenClaw can query Brian results
- OpenClaw can perform federated retrieval
- no canonical memory migration was required

---

# 14. Final principle

If OpenClaw changes, **repair the bridge, not the brain**.

That is the whole point of this architecture.

