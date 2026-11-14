# ProofScope public website

The static public website is in `site/index.html`. It is a presentation layer for this repository's existing Lean-backed ProofScope project and does not replace the engine.

## Publishing

A GitHub Actions deployment workflow is configured in `.github/workflows/pages.yml`. GitHub Pages must be enabled in **Repository Settings → Pages → Build and deployment → Source: GitHub Actions**. After merging to `main`, the workflow will deploy to:

https://entropysherlock.github.io/ProofScope/

If Pages is not yet configured, an administrator must enable it. The workflow cannot bypass repository settings.

## Trust boundaries

The interactive comparison explainer is illustrative, running only in the visitor's browser. It does not invoke Lean, execute `ClaimDelta`, provide certification, or upload private inputs.

Actual research source and evidence are linked to the `v1.2-review` branch and archived GitHub Actions runs. Benchmark figures derive from the project's README; they are from an author-generated suite and do not establish general SOTA superiority.

The site is intentionally separate from `proofscope/`, `lean/`, `tests/`, and research workflows.
