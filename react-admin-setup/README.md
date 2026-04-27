# react-admin baseline (optional)

This directory exists so anyone wanting to reproduce the **react-admin Posters Galore** demo on `:8000` — the original UI the Reflex port in `../reflex-admin/` mirrors — can do so against the same pinned dataset the benchmark uses.

The benchmark itself does **not** require react-admin. It targets the Reflex port at `:3001`/`:8001`. Use this only if you want to compare ports side-by-side, or to visually validate the Reflex implementation against the original.

## What this patches

`react-admin/examples/data-generator/src/index.ts` upstream calls a chain of `generate*()` functions that produce **fresh random data** on every load. For a benchmark we need **deterministic** data — the agent's task references `Gary Smith (id 421)`, `order #98`, `reviews 0/49/292/293`, all of which only exist in our pinned `seed.json`.

The patch replaces the random-data path with a single `import seedData from './seed.json'` and returns it. The `seed.json` you copy in (step 3 below) is the same file the Reflex port reads — both ports back the same dataset.

## Files

- `data-generator.patch` — unified diff against `examples/data-generator/src/index.ts`. Apply with `git apply`.
- `index.ts.original` — upstream `index.ts` for reference (the patch's `before`).
- `index.ts.patched` — what `index.ts` looks like after applying the patch (the patch's `after`).

## Reproduction steps

Run from the parent directory of this repo (so `agent-benchmark/` is a sibling of the freshly-cloned `react-admin/`):

```bash
# 1. Clone upstream react-admin
git clone https://github.com/marmelab/react-admin.git
cd react-admin

# 2. Drop the pinned seed into the data-generator package
cp ../agent-benchmark/seed.json examples/data-generator/src/seed.json

# 3. Apply the patch
git apply ../agent-benchmark/react-admin-setup/data-generator.patch

# 4. Build and run the demo
make install
make build
make run-demo        # serves on http://localhost:8000
```

The demo is now backed by the same dataset as the Reflex app at `:3001`. Gary Smith should appear at customer id `421` with 8 orders.

## Notes

- The patch imports `seed.json` directly via TypeScript's JSON module support; react-admin's `tsconfig.json` already enables `resolveJsonModule`, so no tsconfig changes are needed.
- `seed.json` is ~1.1 MB and contains 900 customers, 600 orders, 324 reviews. Copying it into `examples/data-generator/src/` adds ~1 MB to the working tree but does not affect the published `data-generator-retail` npm package (the package is built from upstream sources, not our patched copy).
- Regenerating the seed (e.g. via `node -e "require('data-generator-retail').default()"` from the repo root) will produce **different IDs** and break `expected_outcome.json`. Don't regenerate unless you also update the expected outcome.
