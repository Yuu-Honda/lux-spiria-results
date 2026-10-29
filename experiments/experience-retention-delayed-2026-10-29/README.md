# Completed delayed external-record study — saved-action replay

This bundle replays the saved actions from the actual delayed collection on 2026-10-29. It does not generate or regenerate AI choices, repeat the original research collection, or perform a new delayed experiment. Python 3 and its standard library are sufficient.

```sh
python3 -B replay.py --out /tmp/experience-retention-delayed-replay
```

Choose a new absolute output directory outside this bundle. An existing output directory is refused. The replay verifies every manifest-listed file and both pinned execution modules before importing them, reads only each assigned source, reproduces only the requested saved inspections, and executes each saved action once. It compares execution status, validation status, artifact SHA-256, exact error type/message, and inspection bytes/costs with the original records. A successful command exits 0 and writes `replay_verification.json` in the new output directory. `--bundle` can explicitly select this bundle.

The uppercase `MANIFEST.json` lists every bundled file except itself with its SHA-256 and byte length. `replay_plan.json` uses the unchanged generic schema 1 and records all 12 assignments in their actual fixed collection order. Each entry has the same 11 fields. Policies and actions are exact raw actor-output JSON bytes; observations and artifacts are exact original file bytes. The three source maps, three public numeric originals, three wrappers, frozen delayed tasks/gold, frozen memory, and pinned execution modules are exact copies. The wrappers contain precisely `{"schema_version":"artifact-container.v2","payload":<parsed original>}`. The originals and wrappers are reused public numerical exports; this study adds no private dialogue.

## Actual timing and scope

The same external experience record was frozen at `2026-10-27T16:12:30.470580Z`. Initial delayed authoring was authorized from `2026-10-29T01:16:40.951919Z` to `2026-10-29T01:19:01.413325Z`, 119050.481339–119190.942745 elapsed seconds (about 33.070–33.109 hours) after the memory freeze. This is an actual delay of more than 33 hours, satisfying the minimum of 24 hours; it is not an exactly 24-hour collection.

Initial/final authoring authorization times are recorded checks before the corresponding authoring, not known provider sampling starts or completion timestamps. Original native deterministic execution timestamps are separate: execution began at `2026-10-29T01:26:33.279883Z` and finished at `2026-10-29T01:26:34.595198Z` after all final actions were frozen. `collection_metadata.json` preserves these native `execution.json` times and the earlier transport execution authorization guard as separate labeled fields. A new replay has its own new execution timestamps.

Twelve fresh contexts each received one assigned item; the experience arm reread the same externally stored record (SHA-256 `5c94f608ff5a6c7e85f311be8cdf45fa210f7da943fa8b832cf419fe8b64af8f`, 5,627 canonical characters). The six items per arm comprise three new delayed objectives, each repeated once per original/wrapped source format. They differ from training and immediate objectives; they are not six independent objectives. No repairs or outcome-based retries were allowed. Fixed paired dispatch order is not provider/time counterbalancing. Provider/model/configuration, token use, compute and latency metadata are unavailable (`null`).

## Observed delayed result

Both arms accepted 6/6 artifacts: 3/3 on original format and 3/3 on wrapped format. Both requested 6/6 optional structural inspections, reading 477,221 bytes and receiving 168,282 canonical projection characters per arm. Both had zero execution errors, invalid actions, abstentions and budget violations. Paired outcomes were six both-correct, zero corrected, zero regressed, zero both-wrong. This delayed sample shows zero measured inspection reduction from the record (6 versus 6); it shows no delayed inspection benefit. Optional inspection cost is separate from the engine's source reads during execution and is not total I/O.

The earlier 17 synthetic preparation checks are engineering checks, separate from these 12 actual delayed collections. Any replay guard tests are also engineering checks, not AI trials or research observations. Successful deterministic replay verifies the saved actions and their artifacts; it does not establish that a new AI would make the same choices.

The intervention is availability of the whole external experience record. It does not isolate a review from its history. Fresh contexts reread that record on new objectives after elapsed real time. This supports a narrow test of external persistence and portability; it does not establish time-only causality, continuous psychological retention, biological memory, learned model weights, a native ChatGPT/full LRE or SHIORI mechanism, general AGI, consciousness, brain behavior, timing gains, or equal compute. Source-format wrappers are an engineered intervention. There are only three unique delayed objectives and known public numerical sources.

This bundle includes no actor context identifiers, receipts, private host paths, private orchestration/state, or new model outputs. Public source provenance is in `input/SOURCE_PROVENANCE.json`; full frozen tasks and gold are in `input/DELAYED_TASKS.json` and `input/DELAYED_GOLD.json`.

## Pinned code

- `action_loop.py`: `61495538507742ab5c3d55721a4115bf9fb24542b605525c63edc6b8f4cb7297`
- `experience_io.py`: `e66ca22700b19a6bae4340561bb5183473b605b8a07bb6e61f0c1bcb4ab78543`
- Unchanged generic `replay.py`: `94d9d3b531056cf23f45be08381ffa024e3dea632f09f30dbea6f5df993fa8f5`
