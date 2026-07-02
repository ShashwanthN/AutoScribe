




# Writter — Agent Interaction Flow

## Overview


Writter learns a writer's voice from sample writing, then reproduces that voice on any new topic using a two-stage pipeline. Stage 1 generates a structured content skeleton from a domain context and outline. Stage 2 runs an iterative voice-matching loop that refines a style profile until the generated text matches the author's voice.

---

## Usage

```bash
python main.py \
  --context context.txt \
  --original-writing sample.md \
  --structure outline.txt \
  --topic "Your Product will Fail! It's not your Fault"
```

### All Flags


| Flag                      | Required | Default                    | Description                                                            |
| --------------------------- | ---------- | ---------------------------- | ------------------------------------------------------------------------ |
| `--context FILE`          | ✅       | —                         | Domain context document (background knowledge for skeleton generation) |
| `--structure FILE`        | ✅       | —                         | Article structure / outline file                                       |
| `--original-writing FILE` | ✅       | —                         | Sample article in the target voice. Repeatable for multiple samples    |
| `--topic TEXT`            | —       | First line of`--structure` | Topic for the generated article                                        |
| `--output-dir DIR`        | —       | `outputs`                  | Directory to write run artifacts                                       |
| `--max-iterations N`      | —       | `6`                        | Max Stage 2 refinement iterations                                      |
| `--threshold F`           | —       | `0.85`                     | Score at which the loop considers itself converged                     |
| `--word-count N`          | —       | —                         | Approximate target word count (±15%)                                  |
| `--run-all`               | —       | `false`                    | Run all iterations regardless of convergence                           |
| `--detailed-log`          | —       | `false`                    | Write full LLM input/output to`detailed_log.txt` in the run directory  |
| `--verbose / -v`          | —       | `false`                    | Verbose output                                                         |

---

## Full Pipeline

```
original_writing[] (never written to disk)
context.txt
structure.txt
      │
      ▼
┌─────────────────────────────────────────────────┐
│  STAGE 1: Content Skeleton Generation           │
│                                                 │
│  SkeletonGenerator                              │
│  Input:  topic                                  │
│          context                                │
│          structure                              │
│          original_writing (pacing/structure     │
│                            patterns only)       │
│  Output: skeleton (markdown)   ─────────────────┼──► skeleton.md
└─────────────────────────────────────────────────┘
      │  skeleton
      ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 2: Voice-Aware Article Generation                        │
│                                                                 │
│  Agent 0 — Baseline Generator                                   │
│  Generates a neutral article on the topic with no style         │
│  guidance. Used purely for adversarial stylometry.              │
│                                   │                             │
│                                   ▼                             │
│  Agent 1 — StyleExtractor                                       │
│  Input:  original_writing (concatenated) ◄── FIREWALL           │
│          baseline (for anti-pattern extraction)                 │
│  Output: StyleProfile                                           │
│  Populates negative_space with patterns the model does          │
│  by default that the original writer never does.                │
│                                   │                             │
│                                   ▼                             │
│  ┌────────────────────────────────────────────────────────┐     │
│  │               BEST-ONLY REFINEMENT LOOP                │     │
│  │                                                        │     │
│  │  Agent 2 — ContentGenerator                            │     │
│  │  Input:  topic, StyleProfile, structure, skeleton      │     │
│  │          prev_tells, prev_comparison, iter_history     │     │
│  │  Output: generated_text                                │     │
│  │                     │                                  │     │
│  │                     ▼                                  │     │
│  │  Agent 3 — StyleComparator ◄── original_writing        │     │
│  │            ↑ LAST AGENT TO SEE REFERENCE TEXT          │     │
│  │  Input:  reference_text, generated_text                │     │
│  │          StyleProfile, skeleton, best_generated_text   │     │
│  │  Output: ComparisonResult                              │     │
│  │          (score, voice_breaks, top_priorities,         │     │
│  │           ai_tells, ai_signature, overfitting)         │     │
│  │                     │                                  │     │
│  │       score > best? │ score ≤ best?                    │     │
│  │            ▼        │      ▼                           │     │
│  │       update best   │  RESCUE ATTEMPT                  │     │
│  │                     │  Agent 4 (alternative_mode=True) │     │
│  │                     │  → Agent 2 (rescue profile)      │     │
│  │                     │  → Agent 3 (rescue score)        │     │
│  │                     │  If rescue > best: accept        │     │
│  │                     │  Else: keep current best         │     │
│  │                     │                                  │     │
│  │            ──────────────────────                      │     │
│  │                     │                                  │     │
│  │         converged / plateau / max_iters?               │     │
│  │                YES → EXIT                              │     │
│  │                NO  ▼                                   │     │
│  │  Agent 4 — PromptRefinerBestOnly                       │     │
│  │  Input:  best_profile, ComparisonResult                │     │
│  │          generated_text, iteration_history             │     │
│  │          current_profile_changes                       │     │
│  │  Refines from BEST profile (not regressed state)       │     │
│  │  Output: refined StyleProfile                          │     │
│  │                     │                                  │     │
│  │                     └──── loop back to Agent 2 ────────│     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
outputs/run_two_stage_<timestamp>/
```

---

## Agent Details

### Agent 0 — Baseline Generator

Generates a neutral article with no style guidance using the same structure. This gives Agent 1 a model-default baseline to compare against the original writing, revealing what the model does naturally that the target author never does. Those model-default patterns are added to `negative_space` in the StyleProfile, forcefully suppressing them in all subsequent generation.

---

### Agent 1 — StyleExtractor

Extracts a structured `StyleProfile` from the concatenated original writing samples.

When given a `generated_baseline`, it compares the baseline against the original writing to identify anti-patterns — behaviors that are LLM defaults but absent in the author's voice. These populate `negative_space` as specific prohibitions.

**Firewall:** This is the last time `original_writing` content is used in an extraction context. After this point, the profile alone carries the voice.

---

### Agent 2 — ContentGenerator

Writes the article following the skeleton structure section-by-section, in the author's voice as described by the `StyleProfile`.

**Skeleton is a hard constraint.** The skeleton defines WHAT to write; the profile defines HOW. The generator receives both as explicit instruction layers.

**Inputs on iterations 2+:** previous voice breaks (`prev_comparison`), AI-tell warnings (`prev_tells`), and score history (`iteration_history`) — so the generator actively avoids repeating past mistakes.

---

### Agent 3 — StyleComparator

A 3-stage internal pipeline that scores how closely the generated text matches the reference voice:


| Stage | Agent                 | What it does                                                                |
| ------- | ----------------------- | ----------------------------------------------------------------------------- |
| 1a    | `StyleEvaluator`      | Pure qualitative dimension observations — no scores yet                    |
| 1b    | `AISignatureDetector` | Profile-aware model artifact detection                                      |
| 1c    | `AITellsChecker`      | Universal LLM writing-pattern detection                                     |
| 2     | `StyleScorer`         | Converts observations → numeric dimension scores                           |
| 3     | `StyleVerdict`        | Computes relative verdict, top priorities, holistic assessment, convergence |

**Overall score** is computed deterministically in code as a weighted average of 13 dimensions (not by the LLM), eliminating variance in the convergence metric.

**Dimensions and weights:**


| Dimension             | Weight |
| ----------------------- | -------- |
| `word_choice`         | 10%    |
| `sentence_rhythm`     | 10%    |
| `voice_fingerprints`  | 10%    |
| `structure_adherence` | 10%    |
| `ai_tells`            | 10%    |
| `sentence_openers`    | 8%     |
| `sentence_endings`    | 8%     |
| `punctuation`         | 8%     |
| `emphasis_moves`      | 8%     |
| `tonal_register`      | 8%     |
| `overfitting`         | 6%     |
| `hedging`             | 2%     |
| `argument_structure`  | 2%     |

**Information firewall:** `original_writing` is never passed to Agents 4. The comparator's structured `ComparisonResult` carries all relevant findings forward.

---

### Agent 4 — PromptRefinerBestOnly

Refines the `StyleProfile` based on the comparator's findings. Always starts from the **best-scoring profile** seen so far — never from a regressed state.

**Normal mode** (each iteration): causal chain reasoning. Receives the full iteration history including what specific fields changed each round, what the style prompt looked like, and what the outcome was. Locks fields scoring above 0.80.

**Alternative mode** (rescue attempts): takes a fundamentally different angle on priority fields. No incremental refinement — complete rewrite of failing dimensions.

**Consecutive failure rule:** if the same dimension fails 3+ iterations despite changes, the field is rewritten from scratch rather than amended.

---

## Best-Only Rescue Logic

When an iteration scores ≤ the current best:

```
regression detected
      │
      ▼
Agent 4 (alternative_mode=True) — refine from best_profile
      │
      ▼
Agent 2 — generate with rescue profile
      │
      ▼
Agent 3 — score rescue content
      │
rescue_score > best_score?
   YES → rescue accepted → becomes new best + accepted profile for this slot
   NO  → rescue discarded → next iteration starts from best_profile anyway
```

Either way the iteration counter advances. The next iteration always starts fresh from the best-known profile.

---

## Convergence Logic


| Condition                                                    | Action                  |
| -------------------------------------------------------------- | ------------------------- |
| `score ≥ threshold` (default 0.85)                          | Exit — converged       |
| Score plateau across 3 consecutive iterations (< 0.01 delta) | Exit — plateau warning |
| `iteration == max_iterations`                                | Exit — max reached     |

The best-scoring iteration's profile and content are always saved regardless of exit reason.

---

## Output Artifacts

```
outputs/run_two_stage_<timestamp>/
├── baseline.txt                    ← Agent 0 neutral generation (for reference)
├── skeleton.md                     ← Stage 1 skeleton (working copy)
├── final_skeleton.md               ← Stage 1 skeleton (final copy)
├── stage1_prompt.txt               ← Portable: regenerate the skeleton in any AI chat
├── stage2_prompt.txt               ← Portable: regenerate the article in any AI chat
├── iter_01_content.txt             ← Generated article, iteration 1
├── iter_01_profile.json            ← StyleProfile used in iteration 1
├── iter_01_style_prompt.txt        ← Full generation prompt sent to Agent 2
├── iter_01_rescue_content.txt      ← (if rescue triggered) rescue attempt content
├── iter_02_content.txt
├── iter_02_profile.json
├── iter_02_style_prompt.txt
├── ...
├── final_style_profile.json        ← Best-scoring StyleProfile (machine-readable)
├── final_style_prompt.txt          ← Best-scoring full generation prompt
├── final_content.txt               ← Best-scoring generated article
├── run_summary.json                ← Score per iteration, exit reason, timing, config
└── detailed_log.txt                ← (if --detailed-log) full LLM input/output log
```

### Portable Prompts

**`stage1_prompt.txt`** — paste into any AI chat to regenerate the content skeleton from scratch given the same topic, context, and structure.

**`stage2_prompt.txt`** — paste into any AI chat to generate a full article in one shot. Contains the content skeleton and the full voice profile. No pipeline required.

---

## Information Firewall

The central architectural constraint: **`original_writing` never reaches Agent 4**.

```
original_writing ──────────────────────────────────────────────┐
                                                                │
                  Agent 4 ◄── ComparisonResult                  │
                  Agent 4 never sees reference text             │
                                                                │
topic, structure ──► Agent 2 ──► generated_text ──► Agent 3 ◄──┘
                                                        │
                                                 ComparisonResult
                                                        │
                                          ≥ threshold → done
                                          < threshold → Agent 4 → loop
```

Agent 3 sees both texts and produces abstract observations (scores, voice breaks, missing moves, overfitting signals). Agent 4 receives only those observations — it updates abstract style rules, not content instructions. The resulting profile is portable to any topic.
