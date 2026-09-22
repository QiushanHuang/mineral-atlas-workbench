# 32-class standard and September 2026 corrections

[Read the full 32-class table](point-groups-32.md).

The offline catalogue is maintained in [`atlas/point-groups-32.json`](../atlas/point-groups-32.json). It lists all 32 non-magnetic crystallographic point groups, crystal systems, textbook shorthand, Schoenflies notation, operation orders, actual mirror counts and alternative settings. Sources are recorded in the catalogue.

| Reference model | Faces | System | International symbol | Textbook shorthand |
|---|---:|---|---|---|
|439 tourmaline|16|Trigonal|3m|L³ 3P|
|451|6|Trigonal|−3m|L³ 3L² 3PC|
|611|20|Hexagonal|6mm|L⁶ 6P|
|6512|20|Hexagonal|6/mmm|L⁶ 6L² 7PC|
|671|5|Hexagonal|−6m2|Lᵢ⁶ 3L² 3P|
|675|8|Hexagonal|−6m2|Lᵢ⁶ 3L² 3P|

For −6m2, the third power of the sixfold rotoinversion produces the horizontal mirror. The shorthand therefore lists three additional vertical mirrors; the actual mirror count is four. An ordinary-element inventory is L³ 3L² 4P. The previous mixed notation Lᵢ⁶ 3L² 4P was corrected. No analogous shorthand error was found in the other four reference models.

## Repeatable checks

1. Check the point-group type, crystal system and canonical textbook notation against the 32-class catalogue.
2. Validate the complete operation set in the declared basis, then geometry, faces, indices and shared edges. A missing operation list must not pass silently.
3. Run `python scripts/audit_reference_groups.py` to independently enumerate vertex-preserving orthogonal operations for the fifteen reference examples. Results are saved in `reference-point-group-audit.json`.
4. Generate reports and the offline gallery from the same catalogue. Its contents participate in the build/cache fingerprint and are included in result bundles.
5. Run Python tests, JavaScript checks and release-package validation before publishing.

The physical specimen point group and physical Miller indices are not established by these checks. 439 tip labels, 451 opposite-face labels, 611 face 15 and 6512 end-label handedness retain their supplied uncertainty. Private photographs or textbook scans are not newly published by this update. The previously authorized 451 dataset is unchanged.

The local case-study review also corrected historical model-count wording and a stale 18-view summary to 29 views. These are local dataset statistics, not a new claim that the public gallery contains those private photos. The public reference gallery remains photo-free; the separate 451 example has its own authorized assets and annotations.

611 was updated on 2026-09-22 after the user confirmed the lower-end proportion correction. Its unequal end slopes and sizes remove the horizontal mirror and inversion; [the correction note](611-correction.md) supersedes the earlier symmetric-shape conclusion.
