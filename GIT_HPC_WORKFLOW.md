# Git Workflow for hurricane_kirk on HPC

## Problem
- **Git is NOT in PATH by default** on this HPC system
- Git is installed via spack but requires module loading
- Python terminal subprocess doesn't inherit modules

## Solution (Use This for Next Session)

### Quick Command (Copy-Paste Ready)
```bash
cd /users/jfkarhu/Numlab/hurricane_kirk
source .project_setup.sh
git status
```

If that works, proceed with commit:
```bash
git add project_prompts.md project_prompts_and_responses.md docs/session_archive/COMPLETION_SUMMARY_*.md README.md scripts/run_cps_analysis.py notebooks/05_multi_run_comparison.ipynb
git commit -m "Session Apr 13: unified colors, robust IBTrACS, -3K experiments, CPS annotations"
git push
```

### What `.project_setup.sh` Does
- Automatically loads `git/2.40.0` module
- One-line setup: `source .project_setup.sh`
- Located in project root

### Verify It Works
```bash
source .project_setup.sh
which git  # Should show: /appl/spack/v020/install-tree/gcc-8.5.0/git-2.40.0-gjj45b/bin/git
git --version  # Should show: git version 2.40.0
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `bash: git: command not found` | Run `source .project_setup.sh` first |
| Git still not found | Try `module load git` manually |
| Using Python terminal | Switch to bash terminal |
| Module not available | Contact HPC support (spack-maintained) |

## Files Modified for This Setup
- **`.project_setup.sh`** – Auto-load script (already created)
- **`README.md`** – Updated "At Session End" with git instructions
- **`docs/session_archive/COMPLETION_SUMMARY_2026-04-13.md`** – Detailed git workflow guide

## Context
- HPC: Mahti (CSC)
- Module system: Lmod + spack
- Git installed: spack v020 (gcc-8.5.0)
- Git version: 2.40.0
- Module state: Sticky (remains loaded across sessions)

---

**Last verified**: 2026-04-13 20:30 UTC
**Verified by**: GitHub Copilot agent
**Status**: ✅ WORKING
