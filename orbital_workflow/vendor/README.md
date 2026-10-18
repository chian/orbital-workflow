# Numerical template source

`nano_rarefaction.py` is a byte-for-byte snapshot of
`nano-graphrag/question_pipeline/utilities/rarefaction.py` at repository revision
`60a167f9eeda0c9ea2ca294724174948947baf3f`.

SHA-256: `02af19652d69f368ee8875d3b27cad0bb2bbc8d1f8274344b72a4437092cdd35`.
The original MIT license is preserved as `LICENSE.nano-graphrag`.

The active scalar-score adapter is `orbital_workflow/score_yield.py`. It reuses
this module's numerical fitting/uncertainty code and numeric band type. It does
not bind the snapshot's identity-incidence credit controller. All adaptations
and the working quasi-likelihood's statistical limitations are explicit in the
adapter's documentation and every serialized yield estimate's provenance.
