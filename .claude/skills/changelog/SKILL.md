---
name: changelog
description: Update CHANGELOG.md at the SyRH repository root from the git history, one section per date, newest first; creates the file from the whole history if it does not exist yet. Use it before merging a branch into main, or whenever the user asks to update, write, create or catch up the changelog or "what changed".
---

# Changelog

Keep `CHANGELOG.md` at the repository root: one `##` heading per date, a few readable bullets
under each. It is run by hand before a branch is merged, so the changelog lands in `main` together
with the work it describes.

## Format

```markdown
# Changelog

All notable changes to SyRH, newest first. Each section is written from the git history before
the work is merged.

## 2026-11-17

- Frontend reorganised by feature: `features/` for business areas, `shared/` for common code.
<!-- commits: 962c423 -->

## 2026-11-16

- Login: session authentication API, login page, route guard and user menu (roadmap 0.2).
- Design system with light and dark themes, and the application shell (roadmap 0.3).
<!-- commits: a968d7c b75c0bb 1bfc962 98bf4e1 a80c8b4 -->
```

- **Dates** are the commits' author dates (`YYYY-MM-DD`), newest section first.
- **The `<!-- commits: ... -->` line** closes each section with the short hashes it covers. It
  does not show when the file is rendered; it is how later runs know which commits are already
  described, so a run never repeats or misses one. Keep it on every section, and never remove
  hashes from it.
- **English**, like the rest of the technical documentation (`specs/missions.md`, principle 10).
  Domain terms stay in French as the project uses them (agent, matricule, carrière, paie).

## Steps

### 1. Find what is missing

```bash
python3 .claude/skills/changelog/scripts/pending_commits.py
```

It prints, for each date, the commits not yet covered by any marker, with their message and the
files they touched. Merge commits and commits that only change `CHANGELOG.md` are already left
out. If it reports no commits, tell the user the changelog is up to date and stop.

When `CHANGELOG.md` does not exist, the report covers the whole history: that is the first run.

### 2. Write the bullets

For each date in the report, turn its commits into bullets for someone following the project, not
for someone reading `git log`:

- **One bullet per notable change**, in plain words: what now exists or works differently. A
  commit's subject is a starting point; its body and file list say what it really did. Look at
  `git show --stat <hash>` or the diff only when the message leaves you unsure.
- **Merge or drop small commits.** Several commits that build one feature become one bullet. A
  fix to something added the same day is part of that bullet, not a separate one. Pure
  housekeeping (formatting, typo, a stray whitespace) is dropped unless it is the only change.
- **Name the roadmap phase** when the work completes or advances one, as `(roadmap 0.2)`:
  commits that tick a box in `specs/roadmap.md` show it in their diff.
- **Keep bullets short**: one line where possible, two at most. No commit hashes in the text;
  they live in the marker.
- **Mention what a reader must act on**: a new setup step, a renamed command, a migration that
  needs care.

Every commit in the report goes into the marker of its date, including the ones you merged into
another bullet or dropped. A commit left out of every marker would come back on the next run.

### 3. Edit the file

- **No `CHANGELOG.md` yet**: create it with the title and introduction from the format above,
  then one section per date.
- **The date already has a section**: add the new bullets at the end of its list and append the
  new hashes to its marker. Rewording an existing bullet is fine when a new commit changes what
  it says (a feature finished, renamed or removed).
- **A new date**: insert its section in date order, newest first, below the introduction.

Leave every other section as it is.

### 4. Show and commit

Show the user the sections you added or changed. Then commit the file on the current branch, by
itself:

```
Update changelog
```

End the message with the attribution lines the session asks for, if any. On `main` itself, leave
the change uncommitted and say so, since work there is meant to arrive through a branch.

Do not merge, push or switch branch: the skill prepares the branch, and merging stays the user's
call.
