# Backlog

Working notes on what comes after the template migration. Started
2026-10-24.

## Overview

| Step | What | Status | Depends on | Branch / PR |
|---|---|---|---|---|
| A | Finish the template migration | ✅ done | | #3 |
| B | Fix multi-element (composite) diagrams | ⬜ next | | `fix/multi-element-pourbaix` |
| C | Redesign as a Typer CLI | ⬜ | B | |
| C2 | Validate the input | ⬜ | C | |
| D | Bump pymatgen for the `show()` fix | ⏸ waiting for the next pymatgen release | | no PR needed |
| E | Update or remove `notes/` | ⬜ | | |

✅ done · ⬜ to do · ⏸ waiting. Update the table when a step starts or
ends. The sections below hold the details.

B and C are a single design job. Do the science fix (B) first, because
the data model it needs decides what the CLI (C) looks like.

---

## A. Finish the migration

Done in #3, merged on 2026-11-24. That PR adds the tests (7 tests,
95% coverage of `__main__.py`), the pathlib refactor and the ruff ALL
fixes. It also lists the behaviour changes, including the `MP_API_KEY`
rename as a breaking change.

---

## B. Fix multi-element (composite) Pourbaix diagrams

**Problem.** For more than one element, e.g. `['Fe', 'Ni']`:

- Entries are fetched and cached **per element** (`Fe.json`,
  `Ni.json`), each from its own `X-O-H` chemical system, and then
  combined with `extend()`.
- `PourbaixDiagram` does combine those into multi-entries (an Fe
  phase plus a Ni phase in the given ratio). So the result is more than
  an overlay, but it can only show **mixtures of single-metal species**.
- **Mixed-metal phases are never fetched**, e.g. NiFe₂O₄ and CuFe₂O₄
  (spinels) and any mixed-metal ions. Those are often the stable phases
  near neutral pH. So `FeNi.png` and `FeCu.png` are wrong, not just
  incomplete.
- **Composition and concentration are hard-coded:** equal fractions
  (`1 / n`) and 10⁻⁸ M for every ion.

**Fix direction.**

- Fetch the whole chemical system in **one** call:
  `mpr.get_pourbaix_entries(['Fe', 'Ni'])`. That queries Fe-Ni-O-H,
  mixed phases included, with one consistent set of energy corrections.
  - To verify: are single-element entries fetched separately exactly
    the same as the ones in a combined fetch? The GGA/GGA+U mixing
    scheme may depend on the chemical system. Compare `Fe.json` against
    the Fe entries from an Fe-Ni fetch.
- **Cache per chemical system**, not per element: key = sorted elements
  joined by `-` (`Fe-Ni.json`), the same convention MP uses. The order the
  user types (`Ni Fe` or `Fe Ni`) must give the same cache file and the
  same diagram.
- Decide what to do with the existing per-element files: keep them
  as-is for single elements (`Fe.json` is already the `Fe` system) and
  regenerate the PNGs that are wrong.
- **Make composition and concentration inputs** (see C), and record
  them in the PNG file name or title, so different diagrams don't
  overwrite each other.
- Possible extra: `PourbaixDiagram` slows down quickly as elements are
  added (the number of combinations grows fast). Consider capping at 2–3
  elements, or warning above that.

**Tests to add with the fix.** Same diagram whatever the element
order; the combined fetch is called once with all elements; the cache
key is the sorted system; the composition fractions sum to 1.

Branch suggestion: `fix/multi-element-pourbaix`. Since it changes the
cache layout, the commit may need a `!` and a `BREAKING CHANGE` note.

---

## C. Redesign as a CLI app

Today the program is configured by editing `compounds` in `main()`.
The template expects Typer, with `commands/` ready for subcommands.

Sketch, to be discussed:

```
pourbaix plot Fe Ni [--ratio 0.5,0.5] [--conc 1e-6] [--ph 0 14] [--v -3 3]
                    [--show/--no-show] [--out DIR] [--refresh]
pourbaix fetch Fe Ni          # fill the cache only
pourbaix cache list|clear
```

Design questions:

- Where do the data folders live? Today they're relative to the folder
  you run from. Options: a `--data-dir` option, an environment variable,
  or a user cache folder via `platformdirs`.
- `--refresh` re-fetches and overwrites a cached system.
- Should `--show` be the default, or only save the PNG? Saving only is
  friendlier for scripts and tests.
- API key: `MPRester()` already reads `MP_API_KEY` itself, so drop the
  `os.getenv`. Should `.env` still override real environment variables
  (`load_dotenv(override=True)`)? Probably not.
- Error messages for a missing API key, unknown element symbols, and
  network failures, instead of tracebacks.
- Split the code into modules: fetch/cache, diagram, plot, and the CLI.
  That makes each part testable on its own.

### Make `plot_pourbaix_diagram` fully object-oriented

Today it mixes two matplotlib styles. It calls `ax.set_xlabel` on an
explicit `Axes`, but `plt.xticks`, `plt.yticks`, `plt.tight_layout`
and `plt.savefig` work on pyplot's implicit "current" figure. That
only works because pymatgen's figure happens to be the most recently
created one.

Rewrite it to go through `ax` and `fig` only. Return the figure, and
let the caller decide whether to call `plt.show()`:

```python
ax = plotter.get_pourbaix_plot(...)
fig = ax.figure
ax.set_xlabel(ax.get_xlabel(), size=fontsize)
ax.set_ylabel(ax.get_ylabel(), size=fontsize)
ax.tick_params(labelsize=fontsize)
fig.tight_layout()
fig.savefig(path, dpi='figure', format='png')
return fig  # the caller decides on plt.show()
```

- The plot looks the same, because pymatgen still creates the figure
  (`pretty_plot(16)`) and we only take it from `ax.figure`. Passing our
  own `ax=` would change the figure size.
- pyplot is only needed to show the window, because opening one is
  pyplot's job.
- Tests can then check the returned figure without patching `plt.show`.
- This fits `--show/--no-show`: the CLI calls `plt.show()` only when
  asked.
- `plt.show()` moves out of `plot_pourbaix_diagram`, which changes the
  function's behaviour. That's why this belongs here, not in the
  migration PR.

---

## C2. Validate the input (with the CLI work)

Added 2026-11-23, Karel's idea while documenting `plot_pourbaix_diagram`:

- **Check that each element is a real chemical element** before calling
  the API (e.g. `pymatgen.core.Element.is_valid_symbol`, or catching the
  `ValueError` from `Element('Fee')`). Today a typo goes straight to the
  API.
- **Check that the API returned entries** for the system. An element
  without Pourbaix data probably gives an empty list or an unclear error
  from pymatgen. Give a clear message and a non-zero exit code instead,
  and don't write an empty cache file.
- **Validate composition and concentration** once they become inputs
  (see B and C): fractions > 0 that sum to 1, concentrations > 0.
- Tests: one per check, with a mocked `MPRester` returning `[]`.

---

## D. `PourbaixPlotter.show()` bug in pymatgen

**Bug** (pymatgen ≤ 2026.10.24):

```python
def show(self, *args, **kwargs) -> None:
    plt = self.get_pourbaix_plot(*args, **kwargs)  # returns an Axes
    plt.show()  # AttributeError
```

`matplotlib.pyplot` is imported only inside `if TYPE_CHECKING:`, so it
doesn't exist at runtime. The local name `plt` shadows it and is an
`Axes` object, which has no `.show()`. Reproduced locally with
2026.10.2:
`AttributeError: 'Axes' object has no attribute 'show'. Did you mean: 'imshow'?`

**Status: already fixed upstream, so no PR needed.** It was fixed in
materialsproject/pymatgen#4748 (merged 2026-10-24), which imports
`pyplot` inside `show()` and calls `plt.show()`. The merge came after the
v2026.10.24 release, so the fix ships in the **next** release.

**Our review of the upstream fix (2026-10-24): fine, no follow-up PR.**
The fix imports `pyplot` inside `show()` and calls `plt.show()`.

- **The import inside the function is unnecessary, but harmless.**
  pymatgen allows it on purpose (ruff `PLC0415` is ignored), but there's
  nothing to gain here: `pyplot` is already loaded through
  `pymatgen.util.plotting`. A top-level import would have been cleaner.
- **How the bug probably got in:** pymatgen runs ruff with `select =
  ["ALL"]`, including the `TC` rules. Because the local variable `plt`
  hid the module, ruff saw `plt` used only in annotations and moved the
  import under `TYPE_CHECKING`. The root cause is the variable name, not
  the import.
- **Returning `Axes` from `get_pourbaix_plot` is correct.** Accepting an
  `ax` and returning it is matplotlib's recommended object-oriented
  pattern, and `ax.figure` gives you the `Figure`. Returning a `Figure`
  instead would break every caller for no gain.
- A `show()` method always has to call `plt.show()`. Opening a window
  is pyplot's job; `Figure.show()` doesn't run the window's event loop.
- A follow-up PR that only moves the import would be a pure style
  change in freshly merged code. Not worth it.

To do:

- We don't call `plotter.show()`, so we aren't affected. We call
  `get_pourbaix_plot()` and then `plt.show()` ourselves.
- After the next pymatgen release, bump the version
  (`uv lock --upgrade-package pymatgen`). We'll keep using
  `get_pourbaix_plot()`, because we need the `Axes` for the font sizes
  and saving. The object-oriented cleanup of our own plotting code is
  under C.

---

## E. Small to-dos

- **The files in `notes/` are out of date** (added 2026-11-21).
  Update them, merge them into the README, or remove them.
