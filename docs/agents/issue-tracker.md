# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues on **23xxCh/ox-robot**.
Use the `gh` CLI for all operations. Pass `-R 23xxCh/ox-robot` unless you are
already inside a clone whose `origin` is that repo.

## Conventions

- **Create an issue**: `gh issue create -R 23xxCh/ox-robot --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> -R 23xxCh/ox-robot --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list -R 23xxCh/ox-robot --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> -R 23xxCh/ox-robot --body "..."`
- **Apply / remove labels**: `gh issue edit <number> -R 23xxCh/ox-robot --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> -R 23xxCh/ox-robot --comment "..."`

This workspace is not yet a git clone of `ox-robot`. Until `origin` points at that repo, always pass `-R 23xxCh/ox-robot`. After the first push, `gh` can infer the repo from `git remote -v`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue on `23xxCh/ox-robot`.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> -R 23xxCh/ox-robot --comments`.
