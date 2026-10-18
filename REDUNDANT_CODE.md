# Duplicated logic: noted, not changed

Each item below does the same job in two places, so a fix in one place can be missed in the other. Fixing any of
them would mean merging the two copies into one shared function, not just deleting code. Kept here as a note only.
Nothing has been changed for these items.

(Items 1-9 from the first review, dead code, the `lane_c_copy_dir` fallback and the aliases, were removed on
18 Oct 2026.)

- **10. Southampton real-label scoring is written out twice**:
  [plan_risk.py:226-276](roadsense/models/plan_risk.py:226) (`run`, steps 2-4) and
  [refresh/score.py:100-141](roadsense/refresh/score.py:100) (`real_risk`, the `if home in cities:` block). Both do
  synthetic history, then `build_table`, predict, the yearly lambda, weather multipliers, the weekly rows, reasons and
  the column order. The only differences are where the model comes from (just fitted vs frozen) and `model_version`.
  Possible fix: one `score_home_city(model, cats, seg_all, labels, wx, potholes, syn, cfg)` in `plan_risk.py`, called
  from both places.

- **11. Building the weekly risk output is written out twice**:
  [risk.py:444-464](roadsense/models/risk.py:444) (`run`) and
  [refresh/score.py:65-84](roadsense/refresh/score.py:65) (`weekly_southampton`). Both do forward rows, predict,
  SHAP reasons for week 1, sort, `p30_trend`, the reason columns and the flags. Possible fix: one shared helper in
  `risk.py`.

- **12. The map projection is defined twice**: `LAT0`, `M_PER_DEG_LAT`, `M_PER_DEG_LON` and `to_xy` in
  [prevent/inputs.py:24-52](roadsense/prevent/inputs.py:24) and
  [synthetic/common.py:38-44](roadsense/synthetic/common.py:38). The comment says they are "same constants as
  lane B". The only difference is that the inputs.py `to_xy` casts to float. Possible fix: inputs.py imports the
  constants from `synthetic.common` and keeps its float cast.

- **13. Two "mean capture over years" helpers**:
  [real_risk.py:274](roadsense/models/real_risk.py:274) `_mean_capture` and
  [eval_ci.py:65](roadsense/models/eval_ci.py:65) `mean_capture`. Both call the same `_capture` core. Only the
  year grouping is duplicated, and they take different inputs (precomputed row groups vs a year column). Low value;
  fine to leave.
