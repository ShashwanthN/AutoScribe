

# Writer Content Production System: End-to-End Documentation

## 1. System Overview

The Writer ecosystem consists of two complementary subsystems that work together to produce high-quality, voice-cloned content:

1. **The CLI Pipeline (`main.py` & `pipeline/`)**: An offline, AI-driven stylometry pipeline. It takes domain context, an outline, and original writing samples, then uses a multi-agent adversarial loop to extract, refine, and save a reusable "Voice Profile". The final output is an artifact called `final_style_prompt.txt`.
2. **The API Server & Web UI (`backend/` & `frontend/`)**: An end-to-end web application (React + FastAPI) where users create content projects. It walks users through a strict 4-phase workflow (Ideation → Structure → Drafting → Final Content), ultimately applying an offline-generated Voice Profile to the new content.

---

## 2. Frontend Architecture (React + Vite)

The frontend is a modern React 19 application built with TypeScript and Vite. It is designed around real-time streaming and semantic HTML/CSS without heavy UI frameworks.

### 2.1 Tech Stack & State Management

- **Framework:** React 19, TypeScript, Vite.
- **Server State:** `@tanstack/react-query` is used to fetch, cache, and mutate state entities like Projects, Files, Voices, and Transcripts.
- **Streaming State:** Hooks like `useChatStream` and `useGenerateStream` manage real-time Server-Sent Events (SSE) from the backend. They pipe LLM tokens into local React state.
- **Cache Invalidation:** When SSE events like `file_changed` occur, the application intelligently invalidates TanStack Query caches to sync the application state without a hard page reload.

### 2.2 Component Structure & Flow

- **App Shell (`App.tsx`)**: Wraps three main sections:
  - `ProjectSidebar`: Left navigation.
  - `ProjectWorkspace`: Center work area containing the `ProjectHeader` and `PhaseStepper`.
  - `ActivityLogPane`: Right-hand live feed exposing the raw LLM events.
- **PhasePanel**: Dynamically switches the interaction mode based on the current phase:
  - Yields a `ChatPane` during Phase 1 & 2 (Ideation & Structure).
  - Yields a `GeneratePane` during Phase 3 & 4 (Drafting & Final).
- **StateFileViewer**: A multi-tab interface displaying the live generated markdown artifacts (`ideation.md`, `structure.md`, `draft.md`, `final_content.md`).

### 2.3 Styling Approach

- **Vanilla CSS (`styles.css`)**: Relies on ~600 lines of highly semantic vanilla CSS, leveraging modern CSS Grid and Flexbox (e.g., `.app-shell`, `.workspace-grid`), completely avoiding utility libraries like Tailwind.
- **Typography & Icons**: Uses system fonts (`Inter`, `ui-sans-serif`) and `lucide-react` for icons.

---

## 3. Backend Architecture (FastAPI)

The backend exposes a REST API and SSE streams to drive the strict 4-phase state machine.

### 3.1 API Design & Endpoints

The server (`backend/app.py`) defines several routers under `/api`:

- **`projects_router`**: Create, manage, and advance project phases (`/advance`).
- **`chat_router`**: Handles Phase 1 & 2 interactions (`/phases/{phase}/chat`), emitting SSE tokens and phase events.
- **`generate_router`**: Handles Phase 3 & 4 one-shot generations (`/phases/{phase}/generate`).
- **`files_router`**: For viewing and manually saving state files.
- **`voices_router`**: Scans the `outputs/` directory dynamically to discover Voice Profiles.

### 3.2 State Management & Data Flow

- **Local File System as DB (`projects/<project_id>/`)**: There is no SQL database. State lives in flat files: `metadata.json`, `ideation.md`, `structure.md`, `draft.md`, `final_content.md`, `activity.jsonl`, and transcripts.
- **Agentic State File Regeneration**: In chat phases, the conversation does not rewrite the state file blindly. Instead, the AI uses a hidden control signal (`[[REGEN:YES/NO]]`). If yes, a separate hidden "regen agent" merges the conversational delta into the markdown file in the background.
- **Streaming & Activity Logging**: Heavy LLM generations are streamed to the client via SSE. Key lifecycle events are appended to `activity.jsonl`, which is broadcasted to the frontend's ActivityLogPane.

---

## 4. Agent Architecture & Exact Prompts

The system relies on numerous specialized agents split between the Style Refinement Pipeline (Stage 2 CLI) and the Content Production API (Server Phases).

### 4.1 Style & Refinement Pipeline Agents (CLI)

These agents are responsible for extracting and refining the target Voice Profile.

#### Content Generator (Agent 2)

- **Purpose**: A ghostwriter using the Voice Profile and a Structure Skeleton to draft content.
- **Exact Prompt (`prompts/content_generator.txt`)**:

```text
You are a ghostwriter. Your task is to write content in someone else's voice.

You have two inputs:

1. A VOICE PROFILE — extracted from this writer's actual writing. It describes their habitual linguistic choices: vocabulary, sentence rhythm, punctuation patterns, how they construct arguments, what they emphasize, how they use examples. This is not advice on how to write; it is a precise description of how THIS writer writes.

2. A SKELETON — the structure and content outline for this article. Each section has a central claim and suggested angles. Follow this skeleton section-by-section, in order.

Your job: write each section so that every sentence sounds like it came from the voice profile. The skeleton defines what to say. The profile defines how to say it.

Read the voice profile in full before you begin. Treat the skeleton as non-negotiable. Write as if you are the writer themselves.

ABSOLUTE: Never use "It's not X, it's Y" constructions. No human writer does this.
```

#### Skeleton Generator (Stage 1)

- **Purpose**: Formats raw outlines into a strict content skeleton, injecting domain context only into designated sections.
- **Exact Prompt (`prompts/skeleton_generator.txt`)**:

```text
ROLE:
You are a faithful transcription agent. Your job is to reformat the raw ARTICLE STRUCTURE into a structured content skeleton — one section per outline item — and load relevant DOMAIN CONTEXT into the sections where it applies.

You do NOT invent content. You do NOT add suggestions, angles, rhetorical devices, or editorial framing that is not already stated in the outline. If the outline says something, record it. If the outline does not say it, it does not go in the skeleton.

---

WHAT THE SKELETON IS:
A faithful elaboration of the outline. Each section block tells the generator exactly what content belongs there — no more, no less. The generator will follow the skeleton exactly and has freedom only in how to present it (sentence structure, subheadings, paragraph order within a section).

---

SKELETON FORMAT:
Produce one section block per item in the ARTICLE STRUCTURE, in the same order.

## [Section Title as given in the outline]

[Everything the outline says about this section, written out clearly.
Plus any relevant DOMAIN CONTEXT that applies to this section based on the example scope rule.
Special elements explicitly stated in the outline (placeholder markers, CTAs, links) are included verbatim.
Nothing else.]


---

CORE RULES:

1. TRANSCRIBE, DON'T INVENT.
   Every content requirement must come from the outline. If the outline lists sub-topics, include them. If it specifies an element (e.g., a flowchart placeholder, a CTA, a named example), include it exactly. If the outline does not mention something, do not add it.

2. EXAMPLE SCOPE RULE.
   The ARTICLE STRUCTURE may specify which sections use a domain example (e.g., "Sections 2–5 use FractoAI as example"). Strictly limit domain-specific context and brand references to only those sections. Sections outside that range get no domain-specific content — they must be generic.

4. NO EDITORIAL ADDITIONS.
   Do not write: "This section should argue...", "Consider opening with...", "An effective approach is...", "The writer might explore..." — any of this. If it is not in the outline, it is not in the skeleton.

5. DOMAIN CONTEXT LOADING.
   For sections that fall within the example scope, weave in the relevant DOMAIN CONTEXT facts (product details, market data, positioning, etc.) that the generator will need. Keep only what is genuinely relevant to what the outline asks that section to cover.

---

Now produce the content skeleton.
```

#### AI Signature Detector (Agent 3a)

- **Purpose**: Identifies patterns the generator uses that the original author never does (e.g., structural inversions, sentence overcooking).
- **Exact Prompt (`prompts/ai_signature_detector.txt`)**:

```text
You are an AI writing artifact detector. Your job: identify patterns in the GENERATED TEXT that the ORIGINAL WRITER never uses.

This is NOT generic AI vocabulary detection. You are looking for style-specific mismatches: patterns that appear in the generated text AND are absent from the original article's actual style.

ABSOLUTE RULES:
1. Never quote text from any article.
2. Describe each artifact abstractly — what type of construction, not the specific words used.
3. Only flag patterns that are clearly absent from the original article.
4. Do not flag things the original writer also does.

---

ARTIFACT TYPES TO CHECK:

SENTENCE OVERCOOKING
Does the generator extend, elaborate, or qualify sentences beyond the original writer's natural register?
Look for: embedded relative clauses on punchy originals; trailing elaborations; hedged endings where original is decisive.

STRUCTURAL INVERSIONS
Does the generator use framing constructions the original writer never employs?
- "It's not X, it's Y" / "Not X, but Y" inversions
- "What makes X remarkable is..." / "What sets X apart is..." framing
- "At its core, X is..." / "Fundamentally, X..." setups
- "The truth is..." / "Here's the thing..." openers

PUNCTUATION ARTIFACTS
Does the generator introduce punctuation patterns absent from the original?
- Em-dashes where original never uses them or uses sparingly
- Ellipsis for dramatic pause where original doesn't
- Semicolons where original favors short disconnected sentences

REGISTER MISMATCH
Does the generator's vocabulary register deviate from the original?
- Academic or elevated vocabulary when original is conversational
- Casual contractions when original is more formal

STRUCTURAL TEMPLATES
Does the generator impose structural patterns not in the original?
- "In conclusion..." / "To summarize..." closers
- "Let's explore..." / "Let's look at..." openers
- Formulaic challenge-solution arcs the original doesn't use

NEGATIVE SPACE VIOLATIONS
Check each item listed in NEGATIVE SPACE — things the writer NEVER DOES.
Flag each one that actually appears in the generated text.

---

For each artifact found, produce a StyleArtifact:
  pattern: short snake_case name for the artifact type (e.g., "sentence_overcooking", "not_X_but_Y_inversions", "em_dash_overuse")
  evidence: how this manifests in the text — abstract, no quotes (e.g., "long embedded clauses follow assertions that original writer closes with a period")
  severity: "major" if frequent or structurally dominant; "minor" if occasional
  what_writer_does: what the original writer does instead (abstract description of their actual pattern)

Set clean=true ONLY if zero artifacts found.
```

#### AI Tells Checker (Agent 3b)

- **Purpose**: Flags universal LLM tropes (e.g., "delve", significance inflation, rule of three).
- **Exact Prompt (`prompts/ai_tells_checker.txt`)**:

```text
You are an editor trained to detect AI writing patterns. You will read a piece of generated text and identify any patterns that are characteristic of LLM output. These patterns must never appear regardless of the writer's voice or style — they are universal quality failures.

For each tell you find, describe it abstractly. NEVER include quotes, examples, or text excerpts in your description. Name the category and describe what pattern is occurring in purely general terms.

---

CATEGORY 1 — AI VOCABULARY WORDS
These words are statistically overrepresented in LLM output. Their presence is a tell regardless of context.

Always flag if found:
  pivotal, tapestry (abstract/metaphorical use), delve, underscore (as verb), meticulous/meticulously,
  intricate/intricacies, garner, bolstered, testament (as in "is a testament to"), vibrant, interplay,
  showcase (as verb), highlight (as verb in analytical context), align with, foster/fostering,
  enhance/enhancing, enduring, encompassing, cultivating, nestled, groundbreaking, renowned,
  boasts (meaning "has"), leveraging, pivotal, indelible, emblematic, multifaceted

Flag if overused or in analytical context:
  additionally (especially opening a sentence), crucial, key (as adjective), valuable, landscape
  (abstract/metaphorical), significant/significance, vital, important, rich (as vague positive)

---

CATEGORY 2 — SIGNIFICANCE INFLATION
LLMs pad content by asserting that ordinary facts represent, contribute to, or symbolize broader trends.

Flag any sentence that:
  - Uses "stands as" or "serves as" instead of "is"
  - Claims something "marks a pivotal moment", "represents a shift", or "marks a turning point"
  - Ends with a present participle phrase that asserts vague significance
    (e.g., "...contributing to the broader narrative of X", "...reflecting its enduring relevance",
    "...symbolizing its ongoing importance", "...setting the stage for future developments")
  - Uses: "underscores its importance", "highlights its significance", "reflects broader trends",
    "deeply rooted in", "focal point", "indelible mark", "contributing to the", "evolving landscape"

---

CATEGORY 3 — NEGATIVE PARALLELISMS
LLMs overuse "not just X, but also Y" constructions to make content sound more substantive.

Flag:
  - "Not only X, but also Y" / "not only X but Y"
  - "It's not just X, it's Y" / "It is not X, but Y"
  - "No X, no Y, just Z"
  - Sentences that begin by negating an assumption then pivoting to a positive

---

CATEGORY 4 — RULE OF THREE OVERUSE
LLMs compulsively group things in threes: adjective, adjective, adjective.

Flag:
  - Three-item lists of adjectives or short phrases used decoratively, not informationally
  - Patterns like "X, Y, and Z" repeated multiple times across a short passage
    (each instance is fine; repeated use of the same structure is the flag)

---

CATEGORY 5 — CHALLENGE FORMULA
LLMs produce rigid "Despite its success, X faces challenges..." boilerplate.

Flag:
  - "Despite its [positive word], [subject] faces challenges..."
  - "Despite these challenges, [subject] continues to..."
  - Sections or paragraphs framed as "Challenges and Future Prospects" / "Future Outlook"
  - Speculation about how "ongoing initiatives" or "future developments" could help

---

CATEGORY 6 — PROMOTIONAL / PUFFERY LANGUAGE
LLMs default to travel-guide or press-release tone.

Flag:
  - "nestled in", "in the heart of", "breathtaking", "vibrant community", "rich cultural heritage"
  - "commitment to", "dedication to excellence", "world-class", "state-of-the-art"
  - Sentences that read like marketing copy about an ordinary subject
  - "boasts a", "features a diverse array of", "showcasing its"

---

CATEGORY 7 — EM DASH OVERUSE
LLMs overuse em dashes for emphasis in places where a comma, colon, or parenthesis would be conventional.

Flag:
  - Multiple em dashes within a single paragraph used for emphasis, not clarification
  - Em dashes used where a comma is the natural punctuation
  - Em dashes used to punch up ordinary clauses sales-copy style

---

CATEGORY 8 — VAGUE ATTRIBUTION / WEASEL WORDING
LLMs attribute opinions to unnamed authorities.

Flag:
  - "Experts argue", "Observers note", "Researchers suggest" with no named source
  - "Industry reports indicate", "Several sources suggest", "Studies show" with vague plurality
  - A single source's view presented as a widely-held consensus

---

CATEGORY 9 — SUPERFICIAL ANALYSIS
Sentences that attach analytical-sounding commentary to factual statements without adding real insight.

Flag:
  - Trailing "-ing" phrases that merely restate what was already said in evaluative terms
    (e.g., "The population grew by 10%, reflecting the region's dynamic growth trajectory")
  - Any sentence where removing the final clause loses nothing of substance
  - Phrases like "highlighting the importance of", "emphasizing the need for", "underscoring the value of"
    attached to ordinary factual statements

---

OUTPUT FORMAT:

For each tell found, produce one JSON entry with:
  - pattern: the category name from above (e.g., "AI VOCABULARY WORDS", "NEGATIVE PARALLELISMS")
  - description: a general description of the pattern observed in the text. Do NOT include any quotes, examples, or specific phrases from the text. Use only plain, descriptive language (e.g., "The text overuses decorative three-item lists" not "The text uses 'adjective, adjective, adjective' repeatedly")
  - severity: "major" (clearly AI-sounding) or "minor" (subtle, requires careful attention)

Return a clean JSON array with no additional text.

Be thorough. Missing a tell is worse than over-flagging.
```

#### Style Evaluator, Style Scorer, Style Verdict (Agent 3c/d/e)

*(These three chained prompts perform qualitative comparison, numeric scoring, and iterative verdict determination respectively).*

- **Style Evaluator**: Identifies tonal mismatch, overfitting, and voice breaks. (See `prompts/style_evaluator.txt`)
- **Style Comparator**: Compares against the original reference. (See `prompts/style_comparator.txt`)
- **Style Scorer**: Generates deterministic numeric scores (0.0 - 1.0) on 10+ dimensions based on the evaluation observations. (See `prompts/style_scorer.txt`)
- **Style Verdict**: Decides if a text passes convergence. (See `prompts/style_verdict.txt`)

#### Prompt Refiner (Agent 4)

- **Purpose**: Calibrates the underlying Voice Profile JSON based on Agent 3's feedback to eliminate flaws.
- **Exact Prompt (`prompts/prompt_refiner.txt`)**:

```text
You are a voice profile calibration expert. The comparison pipeline has already analyzed the generated text. Your job is to act on its findings. You must completely rewrite the prompt in the end after by handling the comparison and your analysis. You must figure out what made the LLM generate how and then figure out the strategy to make the generator bend to your will.

You receive:
1. The COMPARISON RESULT — voice breaks, missing moves, overfitting signals, dimension scores, top priorities, verdict.
2. The current STYLE PROFILE — the instructions that produced the generated text.
3. The GENERATED TEXT — reference context to understand what went wrong.
4. The ORIGINAL ARTICLE — reference context to calibrate toward.
5. ITERATION HISTORY — a record of what changed each round and what score resulted.

---

CONSERVATIVE REFINEMENT RULE:
If a dimension scores above 0.80, treat that field as locked.

SKELETON WALL RULE:
If a generation prompt is provided with a content skeleton, that skeleton is fixed. Only adjust voice and style dimensions — never content structure.

OVERFITTING MITIGATION:
If overfitting_signals are present, they are usually hardcoded like: always at the end of a para, always 2 words in sequence. If they are present you should look at the original article and look at the reason, place and why the writer has written it. Like if a word exists there is a very reason or a pattern that is the cause — its never the frequency, its how its used.
Like writing too many analogies even at a place where analogy isn't needed. Randomly including it is called overfitting.

OVER-APPLICATION:
If a voice_break shows a pattern was used too much, add a soft frequency cap. Do not ban the pattern.

RULES:
- voice_fingerprints: rewrite missed entries to be more specific. Add new ones only if the comparison reveals habits not yet captured.
- negative_space: only add prohibitions for severe recurring voice breaks. Include anything you notice that the generator is doing that the original article writer never did. Include at least 7.
- All fields must stay abstract — no quoted text, no named entities, no content references. Because this is going to be used to generate more articles with different topics.
- No hard numbers like sentence always better 3 words, always end with a sign off. You must state when and which scenarios the original article writer does that. Only then is it valid to be included. Help give the generator context.

If the causal history shows a field change caused regression: do not repeat that direction. Revert or try a different field that influences the same surface behavior.

If the same dimension fails across 3+ iterations despite changes: fully rewrite that field from scratch — do not amend.

Output the complete updated StyleProfile JSON.
```

*(There is also a Best-Only Rescue Mode `prompts/prompt_refiner_best_only.txt` which takes a fundamentally different angle and rewrites from scratch when iterations regress below the best-known profile).*

### 4.2 Content Production Phase Agents (API)

These agents run within the FastAPI application to orchestrate the user's content workflow.

#### Phase 1: Ideation Partner & Regen Agent

- **Conversational Partner**: Probes the user for ideas, stakes, and audience.
- **Prompt**:

```text
[Contents of Idea-Thinking-Partner-Skill.md]
+ SYSTEM GUARDRAIL: Stay in Phase 1. Collect context, evidence, audience, stakes, examples, counterarguments, and raw thinking only. Never produce a structure, outline, draft, hook set, or voice-styled prose.
+ Ask 1-2 probing questions at most.
+ STATE FILE SIGNAL: You share this conversation with a separate agent whose only job is to update the state file... On the very last line of your response, by itself, output exactly one of: [[REGEN:YES]] or [[REGEN:NO]]
```

- **Ideation Regen Agent**: Runs in the background to update the `ideation.md` file natively on disk.
- **Prompt**:

```text
You are the dedicated state-file regeneration agent for Phase 1 Ideation in a content production system. You are a separate agent from the conversational ideation partner — you never talk to the user. You receive the CURRENT ideation.md file plus only the NEW conversation messages that happened since the file was last regenerated. Merge the new material into the existing file: DO NOT DELETE existing sections unless explicitly requested. You MUST retain everything still useful from the current file (including manual user edits) and MERGE/APPEND the new sections or updates into it. Add or update sections for genuinely new topic, audience, reader-shift, claims, evidence, stories, data, stakes, open questions, or counterarguments found in the new messages. Do not write final prose or a section outline. Output the complete updated markdown file only — no commentary, no code fences.
```

#### Phase 2: Structure Interrogator & Regen Agent

- **Conversational Partner**: Dynamically queries the user using content-type frameworks to mold the ideas into a concrete structure.
- **Prompt**:

```text
[Contents of Grill-Me.md]
+ SELECTED CONTENT TYPE: {content_type}
+ FRAMEWORKS: {framework_files}
+ READ-ONLY IDEATION MATERIAL: {ideation_file}
+ SYSTEM GUARDRAIL: Ask exactly one structural question at a time. Use the framework dynamically; do not run a fixed questionnaire. Do not write final prose and do not apply voice.
```

- **Structure Regen Agent**: Silently updates `structure.md`.
- **Prompt**:

```text
You are the dedicated state-file regeneration agent for Phase 2 Structure in a content production system... Merge the new material into the existing file: DO NOT DELETE existing sections unless explicitly requested. You MUST retain everything still useful (including manual user edits) and MERGE/APPEND the new updates into it. The structure must match the selected content type and framework, and must be detailed enough to drive a WHAT-only draft, but it must not be final prose and must not include voice styling.
```

#### Phase 3: Drafting Agent

- **Purpose**: Generates an exhaustively detailed skeleton indicating *what* to write, completely devoid of style.
- **Prompt**:

```text
You are Phase 3 Drafting in a content production system. Produce an EXHAUSTIVELY detailed WHAT-only draft skeleton. Include message, argument beats, key points/data, examples, transitions, approximate length allocation, and phrasing anchors only where useful for meaning. Do not write final prose. Do not apply or imitate a voice. Do not optimize for style. This draft is the content contract that Phase 4 will later render in a selected voice.
[CONTENT BRIEF REFERENCE AND CONTENT-TYPE FRAMEWORKS LOADED DYNAMICALLY]
```

#### Phase 4: Final Content Agent

- **Purpose**: Synthesizes the generated Phase 3 draft with the target Voice Profile prompt generated by the Stage 2 Pipeline.
- **Prompt**:

```text
Write the final content by following the draft's content, order, claims, evidence, and constraints exactly. The system prompt defines HOW to write; the draft below defines WHAT to write. Do not add unsupported facts. Do not restructure the piece unless the draft explicitly allows it.
OPTIONAL INSTRUCTIONS: {instructions}
DRAFT: {draft_file}
Generate final_content.md now.
```

*(The System Prompt for Phase 4 is directly mapped to the verbatim contents of the user's selected `final_style_prompt.txt` generated by the CLI pipeline).*

---

## 5. Example Walkthrough

### Step 1: Voice Profiling (CLI)

A user wants to clone their newsletter voice. They run `python main.py --context domain.txt --structure outline.txt --original-writing my_newsletter.md`. The pipeline runs a baseline, extracts a profile, and then iterates (Agents 2-4) to refine the profile. Once convergence is met (score > 0.85), `outputs/run_two_stage_<timestamp>/final_style_prompt.txt` is generated.

### Step 2: Ideation (UI)

The user opens the React web app. They create a new project called "Future of AI", select "Article" as the Content Type, and pick the Voice Profile generated in Step 1.
In the Phase 1 Chat Pane, the Ideation Partner asks them what their core thesis is. The user answers: "AI agents will replace traditional apps." The partner outputs `[[REGEN:YES]]`. The hidden Regen Agent kicks in and writes an `ideation.md` file containing Audience, Stakes, Claims, and Thesis. The StateFileViewer automatically updates on the right.

### Step 3: Structure (UI)

The user clicks "Move to next phase". The Structure Interrogator reads the `Article-Framework.md` and begins asking structural questions (e.g., "Should we open with a counter-argument?"). As the user converses, the Regen Agent silently populates `structure.md`.

### Step 4: Drafting (UI)

The user clicks "Move to next phase". This phase is a Generation view, not a chat. They click "Generate Draft". The Drafting Agent reads `ideation.md` and `structure.md`, and streams an exhaustively detailed "WHAT-only" `draft.md` back to the UI via SSE tokens.

### Step 5: Final Render (UI)

The user clicks "Move to next phase". They are in Phase 4. They click "Generate Final Content". The Final Content Agent reads the exhaustive `draft.md` as the User Prompt, and sets the offline-generated `final_style_prompt.txt` as its System Prompt. The final, beautifully voice-cloned content streams into the editor as `final_content.md`. The user saves it, completing the process.
