# Long Video Remix — AI Video Editing Skill for Claude Code & Codex

[中文](README.md) | **English**

**Public methods edition · v1.5.1-public-methodology-clean.** The archive provides reusable editing and visual production methods, templates and validators.

Direct 2 uses current project evidence for visual calibration. New styles require representative same-source A/B. Start with the [Visual Reference Router](references/visual-reference-router.md).

**AI video editing Agent Skill for long video → shorts, highlights, and remix edits.** Turn long-form footage into a searchable, traceable video structure; use two human-in-the-loop Director passes to decide *what to tell* and *how to tell it*; then use Visual Methods, Blender motion composition, FFmpeg rendering, and playback QA to turn the confirmed plan into reproducible production.

`Claude Code · Codex · AI video editing · Long video to shorts · Video highlights · Blender · FFmpeg · Human-in-the-loop · Bilingual`

**Why it is different from one-click AI editors:** it does not ask one model to black-box an entire long video and jump straight to a finished cut. Broad builds a low-cost searchable video index; Detail revisits only the regions that matter; Direct 1 and Direct 2 keep creative decisions human-controlled; Execute turns confirmed decisions into real visual production, timelines, renders, and final playback QA.

**Visual production.** Direct 2 uses the Style System and Visual Router to choose among M01–M14 methods and F01–F09 fallbacks. Validate the confirmed design with an editable Blender composition, continuous Dynamic Demo, and Executable Proof before FFmpeg assembly and final QA. See [visual production](references/visual-production.md).

| Common problem | How Long Video Remix handles it |
|---|---|
| **Every new edit requires rewatching the same long footage** | Broad Structure creates a searchable video index, Content Map, and source-time tracebacks |
| **Creative ideas get mixed with unverified evidence** | Direct 1 chooses the narrative direction, Detail verifies targeted regions, and Direct 2 locks the execution plan |
| **Detail / ASR becomes expensive and slow** | STOP after minimum sufficient evidence; prefer subtitles + waveform / signals and use targeted listening / ASR only for material ambiguity |
| **The mockup looks great but the real render drifts** | Confirmed Mockup → Implementation Lock; the V7 design must map to concrete elements and parameters, and Proof/Execute may only reproduce that lock |
| **Decisions drift across models or sessions** | source refs, boundaries, the D2 snapshot, authorization, and render manifest preserve machine-checkable continuity |

**Core outputs:** `Content Map` · structured observations · Detail evidence · real keyframes · Direct 2 execution plan · implementation lock · executable visual proof · verified edit ranges · render manifest · QA / audit records

Built for **MCNs, directors, content editors, creators, and AI video-workflow developers** who repeatedly reuse long-form footage and need creative control without repeatedly re-reading the same multimodal source.

The goal is to reduce repeated interpretation of source media, not to promise zero-cost automatic editing. Frame extraction, targeted ASR, focused rewatching, and GPU rendering still require resources depending on the footage, model, and toolchain.

Use only media you have the right to use.

See [current validation](QA.md) · [Install / update](INSTALL.en.md).

**Cross-model / cross-machine stage delivery:** every major block must regenerate a project-level `handoff.md` before forward stage advance. The handoff carries Scope Lock, gate state, next action, actual artifact manifest + SHA-256, project state digest, and source rebinding metadata. Detail still carries its dedicated `execution-handoff.md`. This is an exit-delivery invariant, not a new approval gate.

## AI Video Editing Use Cases

Long Video Remix is designed for workflows that combine **long-form media understanding, human creative direction, and executable visual production**:

- **Long video to shorts / short-form video editing** — turn long shows, events, courses, or livestreams into short videos;
- **Video highlights / highlight extraction** — interviews, events, reactions, narrative payoffs, and high-value moments;
- **Drama / variety-show remix editing** — narrative recuts, relationship-focused edits, and cross-scene thematic montage;
- **Livestream clipping** — searchable structure, candidate discovery, and traceable clips from long streams;
- **AI-assisted montage editing** — humans / Directors own the narrative while AI handles structure, verification, execution, and QA;
- **Blender motion composition** — editable 2D motion treatment, continuous demos, and executable proof for selected clips;
- **FFmpeg video editing / rendering** — return confirmed visual, audio, and text layers to the full film and audit the export;
- **Searchable video analysis** — reuse the same structured layer for retrieval, research, and content-performance analysis.

## Quick start

For a first local installation, choose the command for your tool. For an existing installation directory, see [Installation and updates](INSTALL.en.md).

Extract the ZIP and install the complete folder as described in [Install and upgrade](INSTALL.en.md).

1. Install the complete folder, copy `assets/project-template.json` to create a separate project, and register sources and available models / video tools.
2. Complete Broad's formal observation layer and Content Map. If you only need structured analysis, deliver at this point; later editing can reuse the results.
3. A human / Director defines the narrative spine. Detail verifies the selected regions and delivers real keyframes and a standalone handoff. Direct 2 then confirms the Execution Package (plan + production reference) and planned ranges; after returning to the actual execution environment, Execute Step 0 verifies selected boundaries before machine authorization is prepared / confirmed against the final ranges.
4. Run static validation and compilation. The rendering adapter checks authorization before consuming the manifest:

```sh
python3 scripts/validate_project.py PROJECT
python3 scripts/compile_render_manifest.py PROJECT
python3 scripts/check_render_authorization.py PROJECT PROJECT/render-manifest.json
```

Existing FFmpeg / MCP renderers continue to handle ordinary editing, clean-video, and audio mixing. The package also includes a local Blender composition path and an FFmpeg assembly step: follow [visual production](references/visual-production.md) to create editable compositions, continuous Dynamic Demos, Executable Proof, and actual review records. Evidence, authorization, manifest compilation, and export auditing still use the existing contracts; external renderers are mapped through the [MCP adapter contract](references/mcp-adapter.md).

Prefer `scripts/extract_frames.py` for local identity-mapped sources; for MCP / proxies, follow the [MCP adapter](references/mcp-adapter.md), retaining measured times and source bindings. The script's `signals` mode marks visual-change and sound segments; `strip` returns frame-by-frame edit-point strips. See [Detail evidence](references/detail-evidence.md) for evidence and question closure.

New projects use V0–V7 for Direct 2 visual work. For installation, see [INSTALL.en.md](INSTALL.en.md).

## Common prompt examples

Replace the placeholders with your sources, narrative direction, or working files, and choose the example that fits your current task.

### 1. No topic yet: start with Broad Structure

**What to ask:**

> Please run Broad Structure on 〔source video(s)〕 across the full source duration and build traceable structured records. Deliver observations for each analyzed sample frame, scene and action indexes, questions and unverified items, a source-order overview, and a Content Map. State the completed coverage and gaps. Stop at the Broad stage for this request.

**What you get:** A Broad source package with the observation tables, overview, Content Map, and coverage records. Each record retains its source and time location.

### 2. Broad is complete: what stories could this material tell?

**What to ask:**

> Based on 〔Broad source package〕, propose a small number of clearly distinct creative directions for me to choose from. For each direction, explain the core idea, narrative spine, corresponding source regions, current evidence, and questions that Detail needs to verify.

**What you get:** Candidate directions and a draft narrative direction for Direct 1. A human or an independent AI Director can propose the directions; discussion and confirmation make them the basis for targeted review.

### 3. The narrative direction is confirmed: which regions need detailed review?

**What to ask:**

> The confirmed narrative direction is 〔direction〕, and the expression that must be preserved is 〔key point〕. Use 〔Broad source package〕 to locate the intervals that need Detail Structure. For each interval, list the source video, time range, reason for selection, necessary surrounding context, and questions to verify. Deliver the detailed-review task list first.

**What you get:** An interval list ready for detailed review, explaining why each interval needs review and what to verify. Exact edit points are left for verification in Detail.

### 4. The intervals are selected: complete Detail and prepare the handoff

**What to ask:**

> Follow 〔confirmed narrative direction〕 and 〔detailed-review task list〕 for Detail Structure. Start from existing subtitles plus waveform / signals, and use local listening / ASR only when exact wording, speaker identity, or a subtitle conflict can change the narrative decision. Do not wait for full-interval ASR. Deliver minimum-sufficient evidence, selection-ready conservative edit boundaries (which may remain partial before final calibration), real keyframes, and a self-contained handoff.

**What you get:** A Detail evidence package with intervals, deep observations, only the necessary speaker checks, selection-ready boundaries, real source keyframes, and a handoff. Unselected candidates do not need frame-exact audio finishing first.

### 5. Detail is complete: run Direct 2 and visual confirmation

**What to ask:**

> Read 〔Detail handoff〕 and the real keyframes, then produce Direct 2's final narrative and execution plan. For visual design, run Visual Reference v2.3.6 V0→V7: V0/V1 define inputs and measurable problems; V2 records how project evidence calibrates the direction; V3 forms candidates with an Art Direction thesis; V4 produces a small mockup set; V5 performs evidence-bound review and stops for my choice. Record that same real choice in V6—do not add a second approval—then use V7 to lock parameters and reference traces. Bridge V7 into the Implementation Lock. If this environment has the same renderer / layout tool that final Execute will use, rebuild the selected result as an Executable Proof with that toolchain and record actual_tool, entrypoint, fonts / assets, and key parameters in execution-reference. If this environment cannot produce the proof, keep the status at awaiting_proof and hand off the open item; do not substitute a tool unavailable to downstream Execute.

**What you get:** A confirmed Execution Plan, the V0–V7 visual-design record, every V6-confirmed mockup, and the V7→Implementation Lock mapping; when the toolchain is available, also an executable proof and reproducible entrypoint.

### 6. Execution Package is confirmed: render and QA

**What to ask:**

> Execute 〔Execution Package〕 without reselecting the narrative, source material, or visual style. Start with Execute Step 0: reopen only the Direct 2 selected ranges + handles and verify final video/audio in/out, sentence tails, meaningful pauses, reactions, and any J/L-cuts; use ASR only for small windows when needed. For every clip, output a planned-range → verified-range → delta/reason comparison. If any calibration exceeds `d2_selection_snapshot`, stop for confirmation instead of widening the selection yourself. Only after all selected boundaries are supported and remain within the snapshot should you prepare / confirm authorization, compile the timeline / render manifest, render, and run QA.

**What you get:** An executable timeline / render manifest, rendered media when the environment supports it, technical audit results, and actual playback QA records.

## Workflow

| Stage | Outputs and decisions |
|---|---|
| Broad Structure → Structured Observation Layer → Content Map | Global observation tables and scene / action / question indexes, preserving coverage and gaps |
| Direct 1 · Narrative Direction | A human / Director determines the narrative spine, candidate regions, and questions to verify |
| Detail Structure + Edit Boundary | Stops at minimum-sufficient evidence; subtitles / signals first; candidates may carry partial conservative boundaries; returns to Direct 1 if evidence is insufficient |
| Direct 2 · Execution Package | Locks selected clips, planned ranges / boundary refs, and allowed calibration; mockup → proof closes the Visual Gate |
| Execute → Render / QA | Step 0 verifies only selected ranges and promotes boundaries to supported; then authorize, render, and QA |

**Canonical stage names:** this release uses only `Broad Structure → Direct 1 → Detail Structure → Direct 2 → Execute`. Board, Deep, Directed Deep, and Detailed Structure are legacy aliases in historical records, not extra stages.

## How rich structure reliably reaches execution

A fixed information baseline preserves facts, derived interpretations, and unknowns. Source-time tags let every judgment be traced back to the original footage, while incremental saves and recovery reduce repeated scanning. Execution integrity binds adopted evidence, boundaries, reviews, and independent source-audio tracks to current source versions, and checks actual ranges and order against Direct 2.

Drafts that are not ready may only be compiled into non-renderable manifests by explicitly using `--planning`. Audio continuity checks protect dialogue and audio tails. J/L-cuts or creative truncation require specific confirmed grounds. Results continue to distinguish technical success from final listening and viewing approval.

For engineering fields, see the [Execution integrity contract](references/execution-integrity.md).

<details>
<summary><strong>Full method, Structure forms, Direct responsibilities, and engineering notes</strong></summary>

## Why Structure is worth doing on its own

Video, images, subtitles / original audio, people, actions, scenes, and context are costly multimodal information. Structure compresses them into searchable, sortable, traceable tables and text, such as `frame-observations.csv`, scene / overview records, and `content-map.md`. People, Directors, or other Skills can consume this compact data first, rather than reloading the original videos, nine-frame grids, and large image collections every time.

This produces a straightforward change:

| Before | After Structure |
|---|---|
| Analyze each video again, one by one | Turn multiple videos into a unified structured data layer |
| Reopen the video to inspect a time point | Directly locate the people, actions, dialogue, background, and content description at that timecode |
| Repeatedly read the same multimodal material for different tasks | Reuse the same structured results for editing, content research, performance review, and retrieval |
| Spend substantial context on watching everything again | Concentrate costly multimodal reading on the regions that need deeper analysis |

## Why Execute is also central

Structure makes source material understandable and reusable. Producing a video still requires turning a confirmed creative plan into a timeline that **preserves evidence and protected ranges, can be rendered, and can be checked**.

Detail Structure establishes verified units, necessary context, and `context_ranges` / `protected_ranges`, then supplies edit boundaries sufficient for Direct 2 selection; unselected candidates may remain partial. Execute **does not redo narrative selection**. Step 0 first promotes the actually selected boundaries to supported, then it is responsible for:

- reopening only Direct 2 selected ranges + handles for final A/V boundary verification, with targeted ASR only when needed;
- compiling the confirmed order and verified cuts into assembly and output timelines;
- applying hard cuts / xfade, audio tracks, text tracks, and chapter cards;
- producing `render-manifest.json` and rendering through the authorized entrypoint;
- after export, performing full decoding, frame-count / duration checks, near-silence scans, join comparisons, Reference Compliance, and final QA.

This repository therefore does not stop at structured analysis and leave you to work out the edit yourself. **Structure and Execute provide stable capabilities at both ends. Direct provides two creative decision points that require human participation: first confirm the narrative spine, then confirm the final execution plan.**

## A concrete example: from analyzing videos to analyzing content

Suppose you have 500 published short videos, along with playback curves, viewing duration, drop-off, or engagement data.

Previously, you might only learn:

> Retention rises at 12 seconds in video A; viewers begin leaving at 8 seconds in video B; video C has a higher completion rate.

What you really want to know is: **what viewers actually saw at that time point.**

After Structure, each analyzed time point can be mapped to structured content: people, actions, expressions / gaze, spatial relationships, dialogue, on-screen text, scene background, and narrative function. Audience behavior data can then be linked directly to content nodes:

| Time point | Structured content | Content type | Audience behavior |
|---|---|---|---|
| 00:08 | Two people argue; one turns and leaves | Conflict / action change | Retention rises |
| 00:12 | A close-up reaction with no dialogue | Character reaction | Replays increase |
| 00:19 | A long stretch of explanatory dialogue | Exposition | Drop-off increases |
| 00:27 | Information planted earlier pays off | Narrative payoff | Retention rises again |

The analysis can then move beyond which video performs well to ask:

- Which kinds of images are more likely to hold attention?
- Which character actions often correspond to replays?
- Before viewers leave, is there usually long dialogue, a static image, or a decline in information density?
- Does a structure such as conflict → reaction → payoff perform consistently across videos?
- Can we retrieve every segment with character silence + a close-up reaction and compare their performance?

**Structure's value is turning video from a multimodal object that is difficult to compute over and combine into a data layer that can be searched, filtered, joined, compared, and used for further creation.**

The same structured results support editing, content review, audience behavior analysis, comparisons across videos, research, retrieval, and other AI workflows.

## Suitable uses

This method suits video work where source material is long and needs repeated interpretation and reuse: drama / variety shows / interviews / documentaries / courses / event recordings, as well as performance reviews of published content.

It is especially useful when:

- there is too much material to understand reliably through a single summary;
- the same videos will be reused for editing, research, retrieval, or analysis;
- creative direction needs human participation instead of a single black-box generation;
- only a small number of candidate segments justify dense multimodal observation;
- content judgments ultimately need to become stable timelines, transitions, audio tracks, and QA.

## Why two Structure passes

Scanning an entire long video at frame-level detail in one pass is expensive and can waste computation before creative direction is established. This workflow uses two Structure passes with different goals:

- **First pass, Broad Structure: prioritize coverage.** Review all source material at a lower sampling density and compress the results into a reusable structured working layer;
- **Second pass, Detail Structure: prioritize completeness.** Once the script direction is confirmed, return only to selected regions to add dense visual observation, original audio, surrounding context, and counterevidence.

Costly multimodal observation is therefore concentrated in a small number of valuable regions, while creative discussion, retrieval, and analysis across videos can work from already structured data wherever possible.

## Structure is a reusable working layer

This structured data layer does not replace original evidence. It lets subsequent work proceed without starting again from the original video. People and other models can quickly browse, filter, sort, search, and cite it.

It addresses three main problems:

- **Reduce repeated multimodal reading**: later Direct stages do not need to reload original videos, nine-frame grids, or large image collections into context for every creative discussion;
- **Reduce context load during creative work**: people, Directors, or other Skills can combine and assess `frame-observations.csv`, scene / overview records, and `content-map.md` directly;
- **Concentrate costly computation on selected regions**: only passages involved in the confirmed script return to the original footage for Detail Structure, with dense reading of visuals, original audio, and surrounding context.

Original evidence is retained. All structured records preserve trace-back paths such as `frame_id`, `scene_id`, timecodes, and evidence refs, so work can return to the source material whenever needed.

## What Structure can do

Broad Structure can begin before a topic is defined. Typical outputs include:

- source material and version registration;
- visual sampling and subtitle / transcript coverage across the full duration;
- **Frame Observation Index**: one row per analyzed sampled frame, preserving frame ID / time / frame-end time in ms, visual facts, actions / states, emotional cues, space / background, motif tags, burned-in subtitles, **original-audio highlights and listening-verification status**, content description, changes from the previous frame, **topic judgment, confidence / evidence basis**, interpretations, and unknowns;
- **Action Node Candidates**: local windows with a default sampling density of 4fps around candidate changes in actions, gaze, positions, or object handoffs, preserving candidate start/end, the minimum viable unit, lip / speech cues, and relationship shifts;
- **Structure Q&A**: structured questions that affect understanding, answers, evidence, unverified items, and the next verification steps;
- scene-level event structure;
- traceable evidence for dialogue, people, locations, and actions;
- a source-order overview;
- a Content Map across scenes;
- navigation for relationship changes, recurring clues, key objects, and silent interactions;
- coverage and unknowns, distinguishing sampled regions from regions verified through continuous audiovisual review.

Structure aims to turn a difficult-to-browse long video into a **source-material space that people and models can search again, combine, and trace back**, rather than simply summarizing its plot.

Broad Structure's formal delivery is therefore neither a nine-frame grid plus a summary nor a Content Map alone. It is a **textual, structured, searchable, traceable working data package**:

1. **Raw evidence**: sampled individual frames, nine-frame grids, subtitles / ASR, and original source locations;
2. **Structured Observation Layer (core delivery)**: `frames.jsonl` + human-readable `frame-observations.csv`, `action-node-candidates.csv`, and `structure-questions.csv`, plus scene / segment observations and `overview.md`;
3. **Creative navigation layer**: `content-map.md`, emotional / relationship cues, and usable boundaries built on the formal records above, allowing the first Director to determine Narrative Direction without reloading the original video.

Frame-by-frame here means **each analyzed / sampled frame**. It does not claim semantic analysis of every frame in a 25/30fps video.

With `deliverable=content_map`, work can formally end at this stage without proceeding to editing.

### Structure's minimum information baseline

Structure output must not collapse into a few summary sentences plus a Content Map. The basic observation layer is the shared foundation for later creative work, analysis, and Execute:

- every analyzed sampled frame must retain a structured record;
- `visual_facts`, actions / states, `motif_tags`, burned-in subtitles / visible text, `change_from_previous`, `content_description`, and `unknowns` must be explicit; use `none` / `unknown` / `not_applicable` even when there is no content;
- action-change candidates must enter a separate action-node table with a local 4fps window or an explicit exception reason;
- questions that affect understanding must enter the Q&A table, preserving evidence and unverified items;
- the overview, Content Map, final copy, or editing suggestions must build on these basic records and cannot replace them.

This constraint ensures Structure becomes a reusable data layer, rather than leaving only a summary that cannot be examined in detail after each task.

## Why Direct happens twice

Direct is external by default and is usually best carried out in an **independent research / directing workspace**. It does not mix topic selection, evidence verification, and the final editing plan into one step; it appears on either side of the second Structure pass.

### Direct 1: Narrative Direction — “What are we telling?”

The first Director consumes Broad Structure's formal textual data: sampled-frame / segment observations, action nodes, Q&A, scene / overview, Content Map, emotional / relationship cues, usable source boundaries, and any necessary external research. Its task is to select:

- the core premise / viewing relationship;
- the Narrative Spine;
- candidate regions / scenes;
- questions for Detail Structure to answer;
- confirmed human judgments and items that must not change.

This step **does not require precise edit points and must not present structured clues as verified facts prematurely**. Use `assets/narrative-direction-template.md` or connect an existing research / directing document directly.

### Direct 2: Execution Package — “How do these materials tell the story?”

After Detail Structure, the Director receives the complete evidence package for a second time: deep observations, original-audio / burned-in-subtitle verification, speaker adjudications, context / counterevidence, verified units, protected ranges, and evidence gaps. Only then is the final execution package formed. Its Editorial Execution Plan includes:

- which verified units are finally selected / excluded;
- their order and each segment's narrative function;
- dialogue / actions / reactions that must be retained in full;
- audio, text, transitions, pacing, and duration allocation;
- replaceable ranges and core expression that must not change.

Also deliver `execution-reference.md`: specific text styles / positions / display duration, visual treatment, audio / transitions, resources, and QA criteria. Usually one or two samples suffice to lock the style across the video; individual references are not required for every shot / subtitle. Detail's handoff already carries these output requirements, so switching models does not depend on the installed environment. See the [Complete delivery contract](references/execution-package.md). Use `assets/execution-plan-template.md` and `assets/execution-reference-template.md`. `assets/editorial-plan-template.md` remains as a combined template for older projects. By default, Execute only implements the plan confirmed by this second Director. **Final source-material selection belongs to Direct 2, not Execute.** If core evidence remains `pending / contradicted`, or either Direct stage is unconfirmed, the timeline cannot be marked `ready_for_render`.

## Why Detail Structure is a separate stage

The first Content Map should not scan every region at frame-level detail for a particular topic. That would be costly and would make Structure commit to a topic prematurely.

Once the first Direct provides Narrative Direction, the system knows where to increase information density. The second pass first establishes the **minimum complete context needed to resolve the current target questions**, then makes selection judgments; it does not require final transcripts or frame-level cut points for every candidate. Typical actions include:

- increase sampling from an overview at roughly ten-second intervals to one or two frames per second or continuous playback; key changes in actions / gaze / positions continue to use local windows at the default 4fps density;
- first create a **Detail Interval Card**: explain why the region requires detailed review, preceding context, current background, what follows, target questions, and its connection to the topic;
- create a **Deep Observation Index** for selected core regions, recording complete visual descriptions: people, positions / orientation, action chains, key visual changes, observable emotional cues / cautious emotional interpretations, expressions / gaze, distances between people, key objects, motif tags, shot size / composition;
- add a **content description**: what actually happens in the short segment, rather than just copying keywords or dialogue;
- add **scene and narrative background**: location / time / environment, the preceding event, and how the current moment came about;
- return from subtitle keywords only to the **audio window needed to resolve the target question**; use subtitles + waveform / signals for localization, and local listening / ASR only for decisive wording, speaker / addressee, overlap, or subtitle conflicts. Distinguish burned-in subtitles / ASR / actual original audio, and use **Speaker Adjudication** when the ambiguity matters;
- expand beyond a single scene to fifteen to thirty seconds before and after it, or to the complete event when necessary, recording before_state / after_state;
- separate facts, interpretations, and unknowns; preserve `question_refs` / unverified items, and check counterevidence, gaps, incorrect causality, and spatiotemporal relationships against Narrative Direction;
- only then refine sufficiently understood core regions into units, context_ranges, protected_ranges, and executable editing judgments.

If evidence conflicts with Narrative Direction, the tool reports the problem and returns to Direct 1 for adjustment. If the evidence supports it, the complete Detail Structure evidence package goes back to the Director to form the second Direct's Execution Package (Editorial Execution Plan + production reference), then proceeds to Execute.

## What Execute can do

At the start of Execute, creative direction is confirmed and relevant material has undergone a second targeted deep pass. Subsequent work includes:

- forming an executable edit plan;
- building an assembly timeline and an output timeline;
- handling hard cuts / xfade, audio tracks, text tracks, and chapter cards;
- using `protected_ranges` to prevent removal of essential meaning and actions;
- quantizing source events to the target fps using cumulative duration; the validator and compiler share the same output-coordinate calculation, avoiding drift from rounding each segment independently;
- including `source.time_mapping` in precise cache identity; mapping changes invalidate the relevant video / audio / final caches;
- compiling `render-manifest.json`;
- caching video, audio, and text outputs in separate layers;
- fully decoding exports and checking frame counts and presentation duration;
- scanning near-silence;
- automatically generating comparison images for every join;
- distinguishing technical checks, playback review, and final video approval.

The repository currently provides timeline compilation and export-audit scripts but **does not mandate one renderer**. You can pass `render-manifest.json` to FFmpeg, a video MCP, an editing-software adapter, or your own rendering workflow.

## Main files

```text
long-video-remix/
├── README.md / README.en.md
├── INSTALL.md / INSTALL.en.md
├── LICENSE
├── SHA256SUMS
├── PROJECT_INSTRUCTIONS.txt
├── CHAT_PROJECT_REFERENCE.md
├── SKILL.md
├── agents/
│   └── openai.yaml
├── assets/
│   ├── capability-map-template.json
│   ├── composition-plan-template.json
│   ├── delivery-spec-template.json
│   ├── visual-methods-template.json
│   ├── execution-plan-template.md
│   ├── execution-reference-template.md
│   ├── execution-handoff-template.md
│   ├── project-template.json
│   ├── timeline-template.json
│   └── …other Structure / Detail templates
├── references/
│   ├── workflow.md
│   ├── workflow-control.md
│   ├── visual-production.md
│   ├── style-system.md
│   ├── visual-methods/
│   │   ├── index.md
│   │   ├── method-library.md
│   │   ├── fallback-recipes.md
│   │   ├── application.md
│   │   ├── resources.md
│   │   └── research-extension.md
│   ├── detail-evidence.md
│   ├── data-contracts.md
│   ├── execution-integrity.md
│   ├── execution-package.md
│   ├── montage-rules.md
│   ├── render-engineering.md
│   ├── qa-handoff.md
│   ├── regression-checklist.md
│   ├── structure-regression-matrix.md
│   ├── mcp-adapter.md
├── scripts/
│   ├── workflow_control.py
│   ├── visual_pipeline.py
│   ├── blender_composite_worker.py
│   ├── render_blender_composition.py
│   ├── finish_ffmpeg.py
│   ├── versioning.py
│   ├── extract_frames.py
│   ├── validate_project.py
│   ├── detail_gates.py
│   ├── compile_render_manifest.py
│   ├── timeline_math.py
│   ├── execution_integrity.py
│   ├── prepare_execution_authorization.py
│   ├── check_render_authorization.py
│   └── audit_render.py
├── examples/synthetic-ready/
├── examples/synthetic-ready/
├── tests/
│   └── …other Detail / Execute / audio / checksum regression tests
├── visual-reference/
└── QA.md
```

## Minimal usage

### Structure only

1. Copy `assets/project-template.json` to `project.json` in the project directory;
2. Register sources and tools that are actually available;
3. Complete Broad Structure and retain both `frames.jsonl` and human-readable `frame-observations.csv` (copy `assets/frame-observation-template.csv` if needed); action-change candidates go into `action-node-candidates.csv` (default local 4fps windows), and structured questions / answers / unverified items go into `structure-questions.csv`;
4. Build scene records / `overview.md` / `content-map.md` from sampled-frame observations; refer to `assets/content-map-template.md`;
5. Set `project.deliverable` to `content_map` to deliver at this stage.

### Full Remix

1. Complete Broad Structure first, delivering the formal Structured Observation Layer + Content Map;
2. A human / Director uses this textual structured data and any necessary external research to form Narrative Direction (Narrative Spine + candidate regions + verification questions);
3. Bring Narrative Direction back into the project, perform Detail Structure on selected regions, and create `deep-observations.csv` to complete visuals, content, background, before/after states, original-audio evidence, counterevidence, and protected ranges for core regions;
4. Deliver real keyframes, evidence, and a standalone handoff (including complete downstream output requirements), then return them to the Director to form the Execution Package;
5. Execute starts with Step 0: reopen only D2-selected ranges + handles, verify final A/V boundaries, and promote adopted boundaries to `supported`; then compile the edit plan / timeline from the confirmed plan + production reference and produce with the frozen styles;
6. After Step 0, save current evidence bindings and prepare / confirm machine authorization against the final ranges according to the [Execution integrity contract](references/execution-integrity.md), then run:

```text
python3 scripts/validate_project.py PROJECT
python3 scripts/compile_render_manifest.py PROJECT
python3 scripts/check_render_authorization.py PROJECT PROJECT/render-manifest.json
```

7. After producing the video with an actual renderer, run:

```text
python3 scripts/audit_render.py output.mp4 PROJECT/render-manifest.json --outdir audit-dir --contacts
```

## Boundaries

- Frame sampling supports discovery; it is not continuous viewing;
- Subtitles / ASR support retrieval; they are not verification by listening to original audio;
- Broad Structure's formal forms are textual structured data. The Content Map builds on them and cannot replace them;
- Direct 1's Narrative Direction expresses directing intent; it is not proof from the source material;
- Detail Structure grounds Narrative Direction in original source evidence;
- Direct 2 forms a complete Execution Package from verified evidence and keyframes; Execute does not skip this step by default and decide the final narrative or style on its own;
- Tools may suggest that a node lacks sufficient material or propose alternative segments, but do not rewrite confirmed core expression on their own by default;
- A successful rendering log does not mean the finished video has passed acceptance.

## Current status

This repository is closer to an **AI-native long-video analysis + remix execution framework** than a one-click short-video generator.

It fits between content understanding and practical editing engineering: make long source material understandable first, then reliably realize human creative decisions.

## License

The [MIT license](LICENSE) covers project code and accompanying documentation that the rights holder has licensed. Retain the copyright and license notice. Third-party material used in a project is subject to its own permissions.

</details>
