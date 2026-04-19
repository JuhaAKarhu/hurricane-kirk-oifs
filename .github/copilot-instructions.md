---
name: hurricane-kirk-workspace-instructions
description: Workspace-level instructions for the Hurricane Kirk analysis project. Applies to all agent operations in this repository.
---

# Hurricane Kirk Analysis — Workspace Instructions

## Data File Handling

**SKIP data file evaluation** during initial exploration, context-gathering, or setup phases:
- Do NOT attempt to load, read, or inspect data files in `/data/` directory (IBTrACS NetCDF files)
- Do NOT load entire GRIB output files from OIFS runs
- Do NOT materialize large multi-dimensional arrays for inspection unless explicitly requested

**Rationale**: 
- Data files are large (IBTrACS: ~100+ MB, GRIB outputs: GBs)
- Evaluation causes performance degradation and quota/quota-warning scenarios
- Analysis scripts handle data loading; metadata/structure info is available from README, notebooks, and script documentation

**Exception**: 
- When user explicitly asks to "load," "check," or "analyze" specific data values
- When debugging data processing code that operates on these files

## Preferred Workflow

1. **Explore via code/metadata**: Read scripts, notebooks, and README instead of raw data
2. **Use script outputs**: Consult CSV summaries, PNG plots, and NetCDF track files (already reduced)
3. **User-initiated loading**: If data inspection is needed, ask confirmation before loading large files

## Project Conventions

- **Persistence**: All user prompts and responses logged in `project_prompts.md` and `project_prompts_and_responses.md`
- **Commits**: Always include these log files in version control commits
- **Terminal Environment**: Use `source .venv/bin/activate` before running Python scripts in this workspace
