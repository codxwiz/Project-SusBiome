# Artifact Policy

Source code, configuration, tests, templates, and the canonical district registry
belong in version control. Provider downloads, generated datasets, logs, trained
models, release manifests, and credentials do not.

Production model artifacts are created under `models/releases/<release-id>` and
promoted into `models/*_model.joblib` through `scripts.ml.registry.ModelRegistry`.
The `models/registry.json` pointer and all generated model files must be stored in
the deployment artifact store or mounted volume, not committed to Git.

The only tracked file under `data/` is `data/raw/locations.csv`. Historical data
must be reproducible through the documented collectors and pipeline commands.
