# OpenBrain Bridge

Use the local `openbrainctl` CLI to interact with canonical memory.

## When to capture memory
Use OpenBrain for:
- user preferences
- project notes
- decisions
- people context
- key facts worth remembering
- summaries of important interactions

## Capture command
When the user says to remember something, or when you identify durable memory worth keeping, run:

```bash
openbrainctl capture "<TEXT>"
```

Prefer concise normalized text.

## Local search
Before answering questions about prior preferences, project history, decisions, or saved notes, run:

```bash
openbrainctl search "<QUERY>"
```

Use returned results as the memory source of truth.

## Brian-only search
When the user asks specifically about Brian Madden’s published thinking:

```bash
openbrainctl brian "<QUERY>"
```

## Federated search
When the user wants both personal memory and Brian’s perspective:

```bash
openbrainctl federated "<QUERY>"
```

## Promotion
If the user wants to save an external Brian result into personal memory, call:

```bash
openbrainctl promote "external.brianmadden" "<TITLE>" "<EXCERPT>"
```

Add a note if the user supplies commentary.

