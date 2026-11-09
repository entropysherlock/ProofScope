"""Per-tool adapters. Each exposes `prepare(case, workdir) -> dict` (inputs written, command to run) and
`parse(case, run, workdir) -> dict` (native verdict preserved, outcomes per track). Adapters may only
add imports/wrap declarations; they never edit a declaration's binders, types or body."""
