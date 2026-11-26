# Backlog

Working notes on what comes after the template migration. Started
2026-10-24.

## Overview

| Step | What | Status | Depends on | Branch / PR |
|---|---|---|---|---|
| A | Finish the template migration | ✅ done | | #3 |
| S | Dash spike: interactive Fe diagram, one session | ⬜ next | | throwaway, in `pbx-trial` |
| B | Fetch the whole chemical system (multi-element fix) | ⬜ | S | `fix/multi-element-pourbaix` |
| C | Redesign as an interactive app (Dash/Plotly), started from a CLI | ⬜ | S, B | |
| C2 | Validate the input | ⬜ | C | |
| D | Bump pymatgen for the `show()` fix | ⏸ waiting for the next pymatgen release | | no PR needed |
| E | Update or remove `notes/` | ⬜ | | |
| F | Find out why magnetite (Fe₃O₄) is no longer stable | ⬜ | | |

✅ done · ⬜ to do · ⏸ waiting. Update the table when a step starts or
ends. The sections below hold the details.

**Direction (2026-11-26):** an interactive app instead of a script that
saves PNGs. The spike (S) decides whether Dash/Plotly is the right tool
before B and C are rewritten around it. B and C are still one design
job, and B (the science) comes first.

**Decision (2026-11-26): no more file cache for entries.** Keep the
fetched entries in memory, per chemical system, while the app runs.
`pourbaix-entries/` and the save/load code go during C. The reasons:

- A file cache means owning a file format. Every library change becomes
  our problem: the emmet `EntryID` in #7 is one example.
- A file cache silently freezes an old database version. The 2024
  `Fe.json` still has magnetite, and current MP data doesn't (see F).
- A fetch takes about 1.5 s, which is fine once per app session.

---|---|---|---|---|
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

## S. Dash spike: is an interactive app the right direction?

One session, throwaway code in the scratch project `pbx-trial`, not in
this repo. The goal is to find out whether Dash/Plotly feels right and
is fast enough, before B and C are rewritten around it.

**Build:**

- **Fe only.** Fetch the entries once at start-up and keep them in
  memory.
- **Build `PourbaixDiagram`, then draw its stable domains as filled
  Plotly polygons.** Use `PourbaixDiagram.get_pourbaix_domains()` for
  the vertices, give each species its own colour, and put a label in
  each domain.
- **Add the water stability lines:** H₂ at E = −0.0591·pH, and O₂ at
  E = 1.229 − 0.0591·pH.
- **On hover, show the species, the pH and E.**
- **Add one logarithmic concentration slider** (10⁻¹⁰ to 1 M). It
  recalculates when you release it (`updatemode='mouseup'`), not on
  every move.

**Measure:**

- How long the diagram takes to recalculate after a slider change, for
  Fe and, as a stretch goal, for Fe-Ni.
- Whether the labels stay readable in thin domains, such as FeO(s)
  along the H₂ line.

**Success:** about 1 s or less for Fe, readable domains, and it's
fun to use. If it fails, decide whether static Plotly HTML (zoom and
hover, but no recalculation) is enough, or keep the matplotlib route.

**Out of scope:** tests, the CLI, packaging and polish.

**Tooling:** `plotly` is already installed (pymatgen uses it), and
`dash` only goes into `pbx-trial`.

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
- **Key the in-memory entries per chemical system**, not per element.
  The key is the sorted elements joined by `-` (`Fe-Ni`), the same
  convention MP uses. The order the user types (`Ni Fe` or `Fe Ni`) must
  give the same key and the same diagram. There's no file cache anymore
  (see the decision under Overview).
- **Make composition and concentration inputs** (see C).
- Possible extra: `PourbaixDiagram` slows down quickly as elements are
  added (the number of combinations grows fast). Consider capping at 2–3
  elements, or warning above that.

**Tests to add with the fix.** Same diagram whatever the element
order; the combined fetch is called once with all elements; the cache
key is the sorted system; the composition fractions sum to 1.

Branch suggestion: `fix/multi-element-pourbaix`.

---

## C. Redesign as an interactive app

`pourbaix Fe Ni` (Typer) starts a local Dash server and opens the
interactive diagram in the browser. The spike (S) decides the details.
Today the program is configured by editing `compounds` in `main()`.

### What to do better than MP's Pourbaix app

MP's app (next-gen.materialsproject.org/pourbaix) is also built with
Dash and Plotly, so the difference has to come from UX choices and
chemical sense, not from the technology. Compared on 2026-11-26 with Fe:

| MP's app | Do better |
|---|---|
| Two colours only: ions pink, solids cyan | A colour per species, or per oxidation state |
| Tiny labels, lost in thin domains (FeO(s), FeOH⁺, FeO₂²⁻) | Labels with a leader line when a domain is too narrow, and a legend |
| Concentration as a text field plus an "update" button, limited to 10⁻⁶–5 M | A live logarithmic slider down to 10⁻¹⁰ M (10⁻⁸ M is common in corrosion work) |
| Hover shows only the name and an mp-id | Hover shows pH, E, the stable species, and perhaps ΔG or the oxidation state |
| Fixed axes: pH −2 to 16, −4 to 4 V | Adjustable ranges and presets |
| Box zoom, double-click to reset (standard Plotly) | The same, plus clear reset and export buttons |
| No database version shown | Show the MP database version with the diagram |

### The earlier CLI sketch

This was written before the redesign. Keep what still fits after the
spike: there's no `fetch` or `cache` command without a file cache, and
`--show` becomes "open the app".

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

*Only relevant if a static matplotlib export stays. With Plotly, this
function is replaced.*

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

---

## F. Why is magnetite (Fe₃O₄) no longer stable?

Found 2026-11-26, in #7. With current Materials Project data, Fe₃O₄ is
not a stable domain in the Fe diagram. With the 2024 `Fe.json`, it is.
**MP's own app agrees with the current data:** at 10⁻⁶ M it shows
Fe(s), Fe₂O₃(s) and FeO(s), plus ions, and no Fe₃O₄. So it's the
database, not our code.

- 10 shared solids changed energy, by up to +1.6 eV. Most are Fe₃O₄
  polymorphs.
- Magnetite usually appears in an Fe Pourbaix diagram, so this could
  be a regression, or a deliberate change: a new calculation, the
  correction scheme (GGA/GGA+U/r2SCAN mixing), or the ion reference
  data.

To do:

- Record the database version (`MPRester().get_database_version()`).
- Check MP's release notes for changes to Fe oxides or the corrections.
- Compare with an experimental Fe Pourbaix diagram from the literature.
- If it still looks wrong, ask on the MP forum (matsci.org), with the
  evidence above.
