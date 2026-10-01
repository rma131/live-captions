# Specs

Every change to this project starts as a spec, lives in this directory, and is
versioned with the code it describes. Switch branches and the specs switch with
them. A fresh session — human or Claude — should be able to read this file and
know exactly what exists, what is being built, and why.

The shape follows GitHub's Spec Kit (constitution → spec → plan → tasks) without
its tooling. This project stays small; so does its process.

## The pieces

| File | Answers | Changes when |
|---|---|---|
| [`../CLAUDE.md`](../CLAUDE.md) | **The constitution.** What must always be true | Rarely, and only by an explicit amendment noted in the spec that caused it |
| `NNN-name/spec.md` | **What** and **why.** Problem, users, requirements, acceptance, decisions | The intent changes |
| `NNN-name/plan.md` | **How.** Approach, files touched, risks, verification | The approach changes |
| `NNN-name/tasks.md` | **Where we are.** Checklist, ticked as commits land | Every working increment |

Small specs may skip `plan.md` and `tasks.md`. Retroactive specs (the ones for
work done before this process existed) record outcome and decisions only.

## Lifecycle

`proposed` → `draft` → `accepted` → `in progress` → `done`
                                         ↘ `rejected` / `superseded by NNN`

- **proposed** — an idea worth writing down. One paragraph is enough.
- **draft** — being specified; open questions listed.
- **accepted** — the spec is agreed; work may start.
- **done** — acceptance criteria met and verified. The spec stays as the record.
- A rejected spec is kept, with the reason. Knowing why something was *not* built
  is half of what keeps a design coherent.

## Conventions

- **Numbering** is sequential and never reused: `003-conference-mode`.
- **Branches** carry the number: `003-conference-mode`, `003-lid-spike`.
- **Commits** cite it: `[003] Route single feed through continuous LID`.
- **Plan mode** drafts land in `.plans/` (gitignored, set in
  `.claude/settings.json`). An approved plan is *promoted* into
  `specs/NNN-*/plan.md` by hand, after a privacy read. Drafts never reach this
  repo directly.
- **Decisions** are recorded in the spec that made them: what was chosen, what
  was rejected, why. Never only in a commit message or a chat.

## Public and private

This repository is public. Specs here describe the **product**: behaviour,
architecture, trade-offs. They never contain client names under negotiation,
pricing, budgets, real people from an event, or anything from a transcript.

Business material — proposals, pricing, client specifics — lives in a separate
private repository and uses the **same spec numbers**, so `003` here and `003`
there are the two halves of one piece of work.

## Index

| # | Spec | Status | Branch |
|---|---|---|---|
| 000 | [Wedding live captions](000-wedding/spec.md) | done | — |
| 001 | [Linux migration and hardware](001-linux-migration/spec.md) | done | — |
| 002 | [Public release](002-public-release/spec.md) | done | — |
| 003 | [Conference mode](003-conference-mode/spec.md) | draft | — |
| 004 | [Phones as microphones](004-phone-mics/spec.md) | proposed | — |
| 005 | [Local model evaluation](005-local-model-eval/spec.md) | proposed | — |
