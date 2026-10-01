# 002 — Public release

**Status:** done · **Completed:** 9 September 2026
**Retroactive spec.**

## Problem
The project should be public — as a portfolio piece and so others can use and
report on it — but its development history belongs to a real wedding.

## Requirements
1. Must publish the code with **no** names, speeches, recordings, transcripts or
   identifying metadata from the event, in any file or any commit.
2. Must preserve the full history privately.
3. Must make the public repo the one where development continues.
4. Should present the event as an anonymised case study.
5. Should make bug reports useful and safe.

## Acceptance — met
- [x] Public repo `live-captions`: one commit, one author, scanned clean, clones
      and passes every test from scratch.
- [x] Private `wedding-captions-archive`: all history, marked never-public.
- [x] Case study, CONTRIBUTING, issue templates in place.

## Decisions
| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| History | Fresh `git init` from the clean tree | `git-filter-repo` rewrite | Commit messages named people; a fresh history cannot leak what it never had |
| Where work continues | Public repo; private is an archive | Develop privately, publish snapshots | Snapshots drift; HEAD was already clean |
| Bug reports | Templates ask for interface, channel map, gate line | Free-form | Every audio bug turns on those three |
| Rule for contributors | Never attach a transcript or recording | — | They contain everything said at someone's event |

## Lessons
The two leaks that nearly happened — the old `.git` renamed into the tree, and a
tracked Notion export never listed in `.gitignore` — were both caught by staging
and scanning *before* adding a remote. Keep doing that for every release.
