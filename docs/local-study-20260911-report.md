# Local run and matched training study — 11 September 2026

A running log of every change made while reproducing DOOMFLY on a local Mac and
running a matched training/frozen-control study. **Each change gets a Method and
a Results entry, appended in order.** Times are local (UTC+8).

No result here is evidence of biological learning. It is one reconstructed brain,
one Doom seed and an unvalidated plasticity hypothesis (v6 previously failed its
visual, conditioning and survival gates). Changed weights and longer survival do
not establish learning.

**Host:** Apple M4, 10 cores, 32 GB RAM, macOS 26 (Darwin 25.6). Python 3.11.14,
numpy 1.24.4, vizdoom 1.3.0, numba 0.61.2, Node 25.9.0.

---

## 1. Environment, data and graph reproduction (11:17–11:25)

### Method
- Created `.venv-neural` with Python 3.11 and installed the pinned
  `requirements-neural.txt` + `doom/requirements.txt` with the build constraints.
- Downloaded the three MaleCNS v1.0 files listed in `doom/datasets.json` and
  checked each SHA-256 against `data-provenance/malecns_v1/source.lock.json`.
- Built the native kernel (`python -m doom.build_kernel`), then ran
  `python -m doom.connectome malecns_v1`, `python -m doom.prepare` and
  `python -m doom.audit_data`.
- Ran the Python test suites and the viewer's checks (`npm ci`, `tsc`,
  `node tests/run-broadcast-tests.mjs`, `npm run build`).

### Results
- All three source files matched their locked checksums (edges file 1,051,241,946 bytes).
- Import reproduced the published graph exactly: 166,700 neurons, 25,582,938
  directed edges, 124,177,617 contacts, 3,335 mapped / 42 unmapped R1–R6, 3,718
  uncertain-sign neurons. Import took 19 s and about 2 GB peak memory.
- The independent data audit passed. `graph_sha256` was identical to the
  committed audit, so the local runtime graph is byte-identical to the audited one.
- `outputs/doom/malecns_v1/manifest.json` was **not** reproduced exactly by the
  committed `prepare.py`: the same 14 readouts in a different order and older
  `motor_interface` wording. The committed file was restored. The decoder
  aggregates by cell type and side, so order does not change controls, but
  checkpointed controller rates are stored by position.
- Tests: 93 Python tests passed, 2 skipped (native observer not yet built);
  the kernel matched the Brian2 reference. Viewer: typecheck passed, 23/23 tests
  passed, production build succeeded. `npm` reported 11 dependency
  vulnerabilities (8 high).
- Rebuilding the kernels rewrote the tracked `*.dylib.json` build records with
  this machine's binary hashes (source hashes unchanged).

## 2. First live run: v6 with learning (11:24, run `e5464e70`)

### Method
`bash doom/run_broadcast.sh --model experimental-v6 --learning --port 8766` with
audit and checkpoints in a temporary directory; viewer via `npm run dev`
(`DOOM_STREAM_ORIGIN=http://localhost:8766`). The launcher sets
`OPENBLAS_NUM_THREADS=1`; the README's direct command does not.

### Results
- Ran at 0.23× real time: about 122 ms compute per 28.6 ms game tic, 7.4 tics
  and 7.4 published frames per wall second, one CPU core, about 760 MB RSS.
- The viewer proxy served immutable one-second segments labelled `training`;
  the browser parser accepted 67 live frames across 9 segments.
- After 25 damage events, 1,968 of 4,184 KC→MBON11 edges had changed.
- The first six completed rounds lasted 158–201 tics with zero kills.

## 3. Native 3D observer build (11:26–11:29)

### Method
Installed `cmake` (Homebrew; Boost and SDL2 already present) and ran
`deploy/doomfly/native-observer/build.sh`: pinned ViZDoom 1.3.0 archive,
`observer.patch`, Release build.

### Results
- Archive checksum verified, patch applied cleanly, engine built without errors.
- `tests/test_doom_native_observer.py`: 8/8 passed, including 3 seeds × 500 tics
  of byte-identical RGB/game/object state and the weapon-bob regression.

## 4. Restart with observer and checkpoint resume (11:30, run `89c6da59`)

### Method
Stopped the run with SIGTERM (final checkpoint), restarted with `--resume`.

### Results
- Stopped in about 2 s with a checkpoint. The new run recorded
  `continuation_of: e5464e70`; brain time, weights and damage counts carried
  over; the interrupted round was censored.
- Camera renders: 5 ms direct, 17 ms through the viewer. A 45 s soak gave 367
  successful renders, 9 rate-limited (the designed 24/s cap), 0 failures.
- With the mirror running (and the soak load), throughput fell from 7.4 to 6.8
  game tics per second (speed 0.196×).
- By 11:53 this training-only pilot had 236 s of brain time, 317 damage events,
  2,042 changed edges (mean efficacy 0.89). Its last 12 rounds lasted 182–276
  tics, 8 with a kill. Without a control this could not be interpreted.

## 5. Matched training / frozen-control study launched (11:54)

### Method
- Stopped the pilot (checkpoint kept) and moved it to
  `outputs/doom/local-pilot-20260911/`, excluded from the comparison.
- Wrote the protocol to `outputs/doom/local-study-20260911/study.json` **before
  launch**: primary outcome = survival tics per completed round, compared
  between arms in blocks of 50 completed rounds.
- Launched two detached processes, both from fresh neural state, seed 41027,
  `combat_survival`, fixed BCI, native observer mirror, 300 s checkpoints:
  - **training** (port 8766, run `e79e47a8`): `--model experimental-v6 --learning`
  - **control** (port 8767, run `681ca998`): `--model experimental-v6` —
    identical damage-triggered PPL101 stimulation, weights frozen.
- `caffeinate -i -w <pid>` prevents idle sleep. Summary script:
  `outputs/doom/local-study-20260911/compare.py` (reads the gzip audit archives).

### Results
- Both arms reported the expected phases (`training`, `frozen-control`).
  Control: 0 changed edges. Training: 1,963 changed after 14 s of brain time.
- Each arm ran at about 0.205× — running two did not halve speed.

## 6. One-hour check (12:55)

### Method
`compare.py` over all completed rounds.

### Results

| | Training | Control |
|---|---|---|
| Completed rounds | 95 | 97 |
| Survival mean / median (tics) | 200.0 / 194 | 197.7 / 192 |
| Kills per round | 0.46 | 0.45 |
| Block 1 (rounds 1–50) mean / median | 204.0 / 194 | 198.3 / 194 |

Rounds 51–95: Mann-Whitney p = 0.64. No difference. Both arms had slowed to
about 0.15× real time (no thermal throttling recorded).

## 7. Two-hour check (14:08)

### Method
`compare.py`; then a tail check of rounds 101+ (share of long rounds, mean with
the top 10% removed).

### Results

| Block (50 rounds) | Training mean / median | Control mean / median | Kills/round T / C |
|---|---|---|---|
| 1 | 204.0 / 194 | 198.3 / 194 | 0.48 / 0.32 |
| 2 | 195.9 / 195 | 199.6 / 190 | 0.46 / 0.62 |
| 3 | 229.7 / 209 | 205.6 / 199 | 0.74 / 0.50 |
| 4 (training 47 rounds) | 213.8 / 202 | 195.7 / 189 | 0.62 / 0.50 |

- Rounds 51–197: Mann-Whitney p = 0.062 (descriptive; repeated looks inflate
  false positives).
- Rounds 101+: training median 207 vs 196 tics; rounds over 300 tics 9 vs 1;
  mean without the top 10% 206.6 vs 192.1.
- Training weights: 2,097 changed, mean efficacy 0.868.

## 8. Movement check (14:10)

### Method
`outputs/doom/local-study-20260911/movement.py` reads every audited tic of every
completed round. **Exploratory:** the split at round 100 was chosen after the
two-hour check showed the arms diverging there; it was not in `study.json`.
For each arm, early (rounds 1–100) and late (rounds 101+), pooled over tics:
damage rate, kills per firing tic, applied turn/forward/fire, readout spikes,
MBON11/PPL101/KC activity, and behaviour in the 35 tics after a nonfatal hit
versus calm tics (no hit in the previous 35 tics, no stimulation active).
Output saved alongside as `movement-<timestamp>.txt`.

### Results

| Metric | Training early | Training late | Control early | Control late |
|---|---|---|---|---|
| Rounds | 100 | 124 | 100 | 136 |
| Survival (mean tics) | 200.0 | 230.3 | 199.0 | 215.6 |
| Damage per game second | 17.5 | 15.2 | 17.6 | 16.2 |
| Kills per round | 0.47 | 0.73 | 0.47 | 0.60 |
| Kills per 100 firing tics | 2.49 | 1.62 | 3.15 | 2.11 |
| \|turn\| (deg/tic) | 1.01 | 1.03 | 1.03 | 1.01 |
| Forward (mean) | 1.42 | 3.08 | 1.14 | 2.05 |
| Moving fraction | 0.52 | 0.80 | 0.44 | 0.65 |
| Firing fraction | 0.094 | 0.194 | 0.075 | 0.132 |
| DNpe017 Hz (move + fire neuron) | 3.56 | 7.71 | 2.84 | 5.13 |
| MBON11 Hz (sum of 2 cells) | 12.1 | 2.3 | 54.3 | 53.9 |
| PPL101 Hz (sum of 2 cells) | 280 | 342 | 265 | 314 |
| Forward: after hit / calm | 1.51 / 1.24 | 3.14 / 3.01 | 1.14 / 1.12 | 2.13 / 1.92 |
| Firing: after hit / calm | 0.100 / 0.082 | 0.199 / 0.187 | 0.076 / 0.072 | 0.137 / 0.123 |

Late-period per-round comparisons (Mann-Whitney, descriptive): forward
p = 3×10⁻¹¹, firing p = 3×10⁻¹¹, MBON11 p = 5×10⁻⁴⁴, damage rate p = 0.11,
\|turn\| p = 0.10.

### Interpretation
- **The difference is a general behaviour shift, not a hit-specific response.**
  Training moves forward and fires more in calm periods by about as much as right
  after hits (forward +1.09 calm vs +1.00 after hits; firing +0.064 vs +0.062).
  Turning is unchanged.
- **Longer survival fits taking fewer hits while moving more** (15.2 vs 16.2
  damage per game second), not better aim: training fires more but has fewer
  kills per firing tic (1.62 vs 2.11).
- **Neural correlate:** training's MBON11 output has almost stopped firing
  (2.3 vs 54 Hz), and DNpe017, which the fixed decoder maps to both forward
  movement and firing, is higher (7.7 vs 5.1 Hz). The circuit path from MBON11 to
  DNpe017 was not tested here; this is a correlation.
- **Both arms drift over time** (more DNpe017, movement and firing late than
  early, including the frozen control), so part of the change is ongoing network
  state, not plasticity. Training drifts further.
- This is consistent with a non-associative side effect of depressing KC→MBON11,
  not with learning to avoid damage.

## 9. Repository changes (13:00–14:00)

### Method and results
- `.gitignore`: ignored `tools/vizdoom-*.tar.gz`, `tools/vizdoom-observer/`,
  `outputs/doom/native-spectator-v1/engine/` and `outputs/doom/local-*/`.
- A `First run` commit (`6c65cd4`) on `main` had added 2,041 files: the ViZDoom
  source/build tree, archive, compiled engine and `vizdoom.pk3`, and study run
  records. Commit `4734aeb` removed them from the index only (files kept on disk)
  and added the ignore rules. They remain in the fork's history at `6c65cd4`,
  including a few generated build files containing a local home path.
- `AGENTS.md` (commit `b370250`): rule against AI attribution trailers in commits.
- Two commit messages were rewritten and force-pushed with lease to the fork's
  `main` to remove AI attribution trailers; file contents were unchanged.

## 10. Restart safety restored and status check (14:35–14:39)

### Method
- `main` carried the original author's kernel build records, which did not match
  this Mac's compiled kernels, so a restart would have been refused. The six
  `*.dylib.json` records were restored from local commit `dc21139`, which holds
  this Mac's records, without recompiling. They are kept as uncommitted local
  changes because they are machine-specific.
- Verified by importing `doom.native` (the runtime integrity check) and comparing
  the v6 memory kernel's record with its binary.
- Ran `compare.py` without changing either arm.

### Results
- The runtime integrity check passed and the v6 memory kernel record matched, so
  either arm can now be restarted with `--resume`. Neither arm was restarted.
- After 2 h 45 min: training 231 completed rounds (1,448 s brain time), control
  245 rounds (1,468 s); both about 0.15× real time.

| Block (50 rounds) | Training mean / median | Control mean / median | Kills/round T / C |
|---|---|---|---|
| 4 (now complete) | 221.1 / 202 | 195.7 / 189 | 0.66 / 0.50 |

- All completed rounds: training mean 218.5 / median 201 tics, control
  209.2 / 196. Rounds 51–231: Mann-Whitney p = 0.066 (descriptive).
- Training weights: 2,099 changed, mean efficacy 0.874.

## Open issues

- The six kernel build records are machine-specific local changes; do not commit
  them. Rerun `python -m doom.build_kernel` after any compiler or source change.
- `manifest.json` is not reproducible from the committed `prepare.py` (see 1).
- The viewer shows "offline" if a single game tic takes longer than 5 s of wall time.
- 11 npm dependency vulnerabilities remain unaddressed.

## Current status and next steps (14:39)

- Both arms are running unchanged since 11:54 and are restart-safe.
- Next: keep both arms unchanged for several more hours and judge later
  pre-registered blocks; treat the movement result as the leading explanation
  unless a hit-specific difference appears; replicate with a second seed pair.
