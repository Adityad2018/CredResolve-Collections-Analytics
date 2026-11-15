# GitHub publication handoff

**GitHub account:** [Adityad2018](https://github.com/Adityad2018)  
**Suggested repository:** `CredResolve-Collections-Analytics`  
**Repository URL:** Pending creation/publication. This document does not imply that a remote repository has already been created or that files have been pushed.

## Before publishing

1. Sign in to GitHub as `Adityad2018` and create an empty repository named `CredResolve-Collections-Analytics`.
2. Do not initialize it with a README, license, or `.gitignore` because this package already contains those files.
3. Review the data-sharing permission. The assignment ZIP includes source extracts, but the repository `.gitignore` excludes `data/raw/` and local database files from Git by default. Do not override this without explicit authorization from the data owner.
4. Inspect `git status --short` and confirm that no credentials, `.env` files, customer data, local databases, or large generated artifacts are staged.

## Publish from macOS Terminal

Run from the extracted project root (`credresolve_review`):

```bash
git init
git branch -M main
git add .
git status --short
# Review the staged file list before committing.
git commit -m "Initial CredResolve collections analytics submission"
git remote add origin https://github.com/Adityad2018/CredResolve-Collections-Analytics.git
git push -u origin main
```

After the push succeeds, the repository URL is:

`https://github.com/Adityad2018/CredResolve-Collections-Analytics`

Only then replace the pending URL in the README/report with the verified repository URL. If GitHub says the remote already exists, inspect `git remote -v` before changing it. Never paste a personal access token into source files or the terminal command itself.
