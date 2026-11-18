# Kalanos audit — lerobot/utokyo_xarm_pick_and_place

- Report: https://hub.kalanos.ai/d/@kalanos/hf/lerobot/utokyo_xarm_pick_and_place
- Source dataset: https://huggingface.co/datasets/lerobot/utokyo_xarm_pick_and_place
- Engine: kalanos-0.9.2+ga422365
- Assessed: 2026-10-31T00:39:20Z
- Scope: vision-imitation-v1

Recorded assessment checks · Review required · pass 101/102 · blocked 0 · review 1 · unknown 0

Sufficiency: unknown

Assessment: Review required. Sources with review/block findings: 1. Affected episodes (review + blocked): 1. Assessment gaps: 2.

## Summary

- Kalanos score: 89.9 / 100 (evaluated checks only; not a readiness score)
- Technical readiness: Not established (unknown, not zero)
- Evaluated / expected episodes: 102 / 102 (inventory complete)
- Recorded duration: 12.3 min
- Episode rows: 7,490
- Recorded decisions: 101 pass · 1 review · 0 blocked · 0 unknown
- Report-only findings: 378 across 102 / 102 episodes. They do not change eligibility.

## Insights

- Principal findings, by distinct episodes affected (issue and channel counts overlap; do not sum):
  1. Blur vs. same-camera baseline: 1 episode, 1 source flagged — hand camera (1)
- Task context: Pick up a white plate, and then place it on the red plate.

## Dataset quality indicators

- Robot & action: 2 of 6 fields declared (declared, not verified). Robot model: Unknown; Action shape: 7-channel action_vector; Action space and convention: Unknown; Units: Unknown; Control frequency: Unknown; Camera views: 3 video streams
- Data integrity: Not established (1 of 4 required checks measured); timestamps out of order in 0 of 102 episodes measured
- Diversity: no near-duplicates among 5,151 numeric-trajectory pairs across 102 episodes at 2% distance; trajectory variation 0.920. Numeric trajectories only; not visual or behavioral diversity.
- Size after filtering: 101 passing episodes, 12.2 min
- Task coverage: 1 unique instruction. Scene and outcome labels are unknown unless annotated.

## Findings & Coverage Gaps

- **Hand image** (observation.images.hand_image) — Review required, 1 episode. vision.blur vs camera in 1 episode.
- **Capture timing** — Assessment gap (outside the required scope; not a passed check). 0 computed / 714 eligible stream_episode; 714 unavailable.
- **Signal meaning** — Assessment gap. 918 computed / 1734 eligible channel_episode; 816 unavailable.

8 further source(s) carry report-only observations that do not change eligibility.

## What was measured

25 of 45 checks ran; the counts of those are under Measurements.

- integrity.dead_taxel_pct: did not run (unavailable 306, not applicable 408)
- integrity.hysteresis: did not run (unavailable 306, not applicable 408)
- integrity.snr_db: did not run (unavailable 1,529, not applicable 205)
- motion.action_chatter: did not run (unavailable 306, not applicable 408)
- motion.energy_proxy: did not run (unavailable 102)
- timing.drop_rate: did not run (unavailable 714)
- timing.dt_jitter_ms: did not run (unavailable 714)
- timing.effective_hz: did not run (unavailable 714)
- vision.camera_sync_skew_ms: did not run (unavailable 102)

## Dataset context

- Actions, objects and roles, scenes, relation, goal and task type: not included in this summary.

## Recording details

- Robot: Unknown (declared by the source; not verified)
- Format: lerobot_v3
- License: APACHE-2.0 (declared)
- Cameras: observation.images.hand_image (102 episodes); observation.images.image (102 episodes); observation.images.image2 (102 episodes)
- Actions: 7-channel action_vector (motor_0, motor_1, motor_2, motor_3, motor_4, motor_5, motor_6)
- Not recorded by this report: action units, dtype, control semantics, declared sampling rate, camera resolution and placement.

Declarations describe structure, not observed actions, device identity, model compatibility or task success.

## Instructions

- “Pick up a white plate, and then place it on the red plate.” — 102 episodes

Instructions are intended tasks as the dataset stores them, not observed actions or outcomes.

## Episode selection

- Listed episodes: 102. All are selected by default; the report page narrows the selection by instruction, action, object and scene.
- Unknown episodes are not demonstrated failures; zero recorded passes is not a measured failure rate.

## Audit details

- Run state: complete
- Errors recorded during the audit: none
- Binding conflicts: none

## Sources & component evidence

Not recorded in this report.

## Assessment coverage

Computed, unavailable and out-of-scope evidence are different states. Each line uses its own denominator.

Capabilities (computed / eligible):
- acquisition_timing: outside the required scope (102 not required); not a passed check
- behavioral_diversity: outside the required scope (102 not required); not a passed check
- numeric: 102 / 102 episode computed
- video_quality: 102 / 102 episode computed

Evidence dimensions:
- behavioral_diversity: outside the required scope (102 not required); not a passed check
- capture_origin_evidence: 0 / 714 stream_episode computed; 714 unavailable
- semantic_mapping: 918 / 1,734 channel_episode computed; 816 unavailable
- visual_quality: 306 / 306 camera_stream_episode computed

## Measurements

Counts are recorded severity results, not episode counts or raw measurement values. Severity is distinct from the consequence that decides review or blocking.

- annotation.task_instruction_missing (episode, flag): 102 report_only; computed in 102 of 102 episodes
- integrity.flatline_pct (channel, %): 456 good · 360 warning · 713 report_only; computed in 102 of 102 episodes
- integrity.missing_pct (channel, %): 1,734 good; computed in 102 of 102 episodes
- vision.exposure_shift_pct (stream, %): 288 good · 18 warning; computed in 102 of 102 episodes
- vision.sharpness_score (stream, fraction): 306 good; computed in 102 of 102 episodes
- … 4 more not listed here.

## Report details

- Input report: lerobot/utokyo_xarm_pick_and_place
- Schema: 8.0.0
- Source report SHA-256: Not recorded
- Engine run: 98c4d0d5bfce4962a8a2c5a4e3855c9a
- Engine version: 0.9.2
- Engine revision: Not recorded
- Source identity uri: hf://datasets/lerobot/utokyo_xarm_pick_and_place@da56c23e1b6d32c101c300b85dc54288b53ea63c
- Source identity protocol: hf
- Source identity repo id: lerobot/utokyo_xarm_pick_and_place
- Source identity revision: da56c23e1b6d32c101c300b85dc54288b53ea63c
- Source identity size bytes: 57156343
- Source identity file count: 10
- requirements id: vision-imitation-v1
- policy id: default-decisions-v1
- binding id: resolved-bindings
- tier: full
- Readiness formula id: pass-quality-over-known-inventory-v1
- Readiness reasons: 58
- Readiness passing quality: 89.86731767951191

## Limitations

This summary preserves recorded engine decisions. It does not execute diagnostics or certify task success, hardware health or training suitability. Unknown or unavailable evidence is not zero and not a pass.
