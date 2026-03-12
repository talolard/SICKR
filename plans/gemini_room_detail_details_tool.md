# Plan: `get_room_detail_details_from_photo`

## Goal
Add a new image-analysis tool, `get_room_detail_details_from_photo`, that accepts one or more user-provided room images and performs one direct Gemini multimodal call to:

1. Verify whether each image appears to show an indoor room.
2. Detect when the provided images are certainly from different rooms.
3. Extract notable objects of interest across the image set.
4. Infer the most likely room type with an explicit confidence signal.
5. Return a fully typed, JSON-serializable Pydantic result for agent and UI use.

This is a backend tool call, not an agent-to-agent handoff and not a multi-step tool chain.

## Current Repo Constraints
- `src/ikea_agent/tools/image_analysis/` already contains typed tool models and wrappers, but those are fal-backed image-analysis tools.
- The image-analysis agent already has access to uploaded attachments via `ctx.deps.state.attachments`.
- There is not currently a canonical runtime `RoomType` literal in `src/`.
- `AnalysisRepository.record_analysis(...)` assumes a single `input_asset_id`, while this tool is intentionally multi-image.
- User-visible tools require a frontend renderer registration in CopilotKit.

## Proposed Scope
- Add a Gemini-backed room-detail tool under `src/ikea_agent/tools/image_analysis/`.
- Keep the tool agent-facing and attachment-driven, like the existing image-analysis tools.
- Use one Gemini `generate_content` call with:
  - one text instruction block
  - N uploaded room images
  - structured JSON output constrained by a Pydantic schema
- Return image-set-level conclusions plus per-image details.
- Register the tool on the image-analysis agent.
- Add a dedicated UI renderer rather than falling back to raw JSON.

## API Shape

### Tool Name
`get_room_detail_details_from_photo`

Keep the name stable once introduced. It is awkwardly repetitive, but that is preferable to renaming it later after UI/tool contracts depend on it.

### Input Model
```python
class RoomDetailDetailsFromPhotoRequest(BaseModel):
    images: list[AttachmentRefPayload] = Field(min_length=1, max_length=12)
```

Behavior:
- If the request is omitted, the tool should default to all uploaded image attachments from `ctx.deps.state.attachments`.
- Reject empty attachment lists.
- Reject non-image attachments.
- Keep the max image count modest so the prompt and token cost stay bounded.

The initial version should stay intentionally simple and avoid speculative knobs.

## Shared Room Type Literal
Introduce a shared runtime literal in `src/ikea_agent/shared/types.py` and reuse it from the tool models.

```python
RoomType = Literal[
    "bathroom",
    "bedroom",
    "dining_room",
    "entryway",
    "hallway",
    "home_office",
    "kitchen",
    "laundry_room",
    "living_room",
    "nursery",
    "outdoor",
    "studio",
    "utility_room",
    "other",
    "unknown",
]
```

Notes:
- `unknown` is for insufficient evidence.
- `other` is for identifiable rooms that do not fit the current union cleanly.
- If another canonical room taxonomy is discovered during implementation, use it instead, but only if it already exists in active runtime code.

## Output Model

### Supporting Types
```python
RoomEvidenceConfidence = Literal["high", "medium", "low"]

CrossImageRoomRelationship = Literal[
    "same_room_likely",
    "different_rooms_confirmed",
    "uncertain",
]
```

```python
class RoomDetailObjectsOfInterest(BaseModel):
    major_furniture: list[str] = Field(default_factory=list)
    fixtures: list[str] = Field(default_factory=list)
    lifestyle_indicators: list[str] = Field(default_factory=list)
    other_items: list[str] = Field(default_factory=list)
```

```python
class RoomPhotoImageAssessment(BaseModel):
    image_index: int
    appears_to_show_room: bool | None
    room_type: RoomType = "unknown"
    confidence: RoomEvidenceConfidence = "low"
    notes: list[str] = Field(default_factory=list)
```

### Top-Level Result
```python
class RoomDetailDetailsFromPhotoResult(BaseModel):
    caption: str
    room_type: RoomType = "unknown"
    confidence: RoomEvidenceConfidence = "low"
    all_images_appear_to_show_rooms: bool | None = None
    non_room_image_indices: list[int] = Field(default_factory=list)
    cross_image_room_relationship: CrossImageRoomRelationship = "uncertain"
    objects_of_interest: RoomDetailObjectsOfInterest = Field(
        default_factory=RoomDetailObjectsOfInterest
    )
    image_assessments: list[RoomPhotoImageAssessment] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
```

Why this shape:
- The tool needs a single room-type answer for downstream agent reasoning.
- Per-image assessments preserve ambiguity instead of forcing a brittle global conclusion.
- `different_rooms_confirmed` is stricter than “looks different”; the prompt should only emit it when Gemini is confident.
- Grouped string lists are easier for the model to fill reliably than per-object metadata.
- Grouped lists are easier for downstream UI to render and easier for agents to reason over.
- `notes` keeps room for model observations that do not fit the other buckets.

Indexing convention:
- `image_index` is zero-based and refers to the order of `request.images`.

## Prompt Contract
Use one prompt with clear instructions and conservative certainty language.

Prompt intent:
- The user provided a set of images for interior-design help.
- Decide whether each image appears to depict an indoor room.
- Determine whether the images are clearly from different rooms.
- If uncertain whether they are the same room, return `uncertain`.
- Only return `different_rooms_confirmed` when the images clearly depict different rooms.
- Populate `objects_of_interest` using short noun phrases.
- Put items into grouped lists:
  - `major_furniture`
  - `fixtures`
  - `lifestyle_indicators`
  - `other_items`
- Infer the most likely room type from the allowed `RoomType` values.
- Prefer `unknown` over guessing.
- Keep notes short and concrete.

Prompt examples for object extraction:
- `major_furniture` examples:
  - `sofa`
  - `sectional couch`
  - `bed`
  - `bunk bed`
  - `crib`
  - `dining table`
  - `desk`
  - `bookshelf`
  - `wardrobe`
  - `dresser`
  - `nightstand`
  - `coffee table`
  - `tv stand`
  - `kitchen island`
  - `bar stools`
- `fixtures` examples:
  - `toilet`
  - `sink`
  - `bathtub`
  - `shower`
  - `vanity`
  - `stove`
  - `oven`
  - `refrigerator`
  - `dishwasher`
  - `countertop`
  - `upper cabinets`
  - `fireplace`
  - `radiator`
  - `ceiling fan`
  - `washing machine`
  - `dryer`
- `lifestyle_indicators` examples:
  - `dog`
  - `cat`
  - `litter box`
  - `diapers`
  - `stroller`
  - `school backpack`
  - `Legos`
  - `toys`
  - `gaming chair`
  - `monitor setup`
  - `laundry basket`
  - `guitar`
  - `bike helmet`
  - `pet bed`
  - `baby gate`
- `other_items` examples:
  - `rug`
  - `curtains`
  - `wall art`
  - `mirror`
  - `plant`
  - `storage bins`
  - `boxes`
  - `vacuum`
  - `clutter`
  - `shoe rack`

The prompt should explicitly prohibit overclaiming:
- Do not assume all images show the same room.
- Do not force a room type when evidence is weak.
- Do not hallucinate unseen objects.
- Use short concrete labels, not long descriptions.
- Do not duplicate the same object across multiple lists.

## PydanticAI Call Design
Implement this through the repo's standard `pydantic-ai` Google model path, not by instantiating `google.genai.Client` directly.

Recommended implementation shape:
```python
extractor = Agent[None, RoomDetailDetailsFromPhotoResult](
    model=build_google_or_test_model(...),
    output_type=NativeOutput(RoomDetailDetailsFromPhotoResult),
)

result = await extractor.run(
    [
        instruction_text,
        *[
            BinaryContent(data=stored.path.read_bytes(), media_type=image.mime_type)
            for image in request.images
        ],
    ]
)
```

Implementation notes:
- Reuse the existing app Gemini API key settings and model-construction path rather than introducing a second Gemini client stack.
- Keep this as one internal model call, not an agent-to-agent handoff.
- Load attachments from `AttachmentStore` and send them through `pydantic-ai` image input support.
- Start with `NativeOutput(RoomDetailDetailsFromPhotoResult)` because this tool does not need function tools.
- If the selected Gemini model proves unreliable with native structured output, fall back to `PromptedOutput(RoomDetailDetailsFromPhotoResult)` in the same internal extractor wrapper.
- Wrap malformed output or model errors in a tool-local error type with actionable messages.

Suggested helper shape:
- `build_room_detail_details_extractor(...) -> Agent[None, RoomDetailDetailsFromPhotoResult]`
- keep it local to the image-analysis tool package unless another feature needs the same extractor.

## Model Selection
Add a dedicated settings entry for this tool rather than hard-coding the main conversational model.

Suggested setting:
```python
gemini_image_analysis_model: str = Field(default="gemini-2.5-flash")
```

Reasoning:
- This tool is a bounded extraction/classification task, not open-ended prose generation.
- The default image-analysis model should be cheap and fast enough to call during normal chat use.
- Keeping a dedicated setting lets us upgrade or separate cost/performance later.

## Backend Integration

### New/Updated Modules
- `src/ikea_agent/tools/image_analysis/models.py`
  - add request/result models and shared supporting types
- `src/ikea_agent/tools/image_analysis/tool.py`
  - add service wrapper and public async helper
  - add the internal `pydantic-ai` extractor construction/helper
- `src/ikea_agent/tools/image_analysis/__init__.py`
  - export the new models and tool entrypoint
- `src/ikea_agent/chat/agents/image_analysis/toolset.py`
  - register the new tool
- `src/ikea_agent/persistence/models.py`
  - add normalized multi-image analysis input table
- `src/ikea_agent/persistence/analysis_repository.py`
  - persist and query the normalized input-asset rows
- migration files under the repo's existing migration path
  - add/drop the new normalized table as needed during local development
- `src/ikea_agent/shared/types.py`
  - add shared `RoomType`
- `src/ikea_agent/config.py`
  - add `gemini_image_analysis_model`

### Toolset Behavior
Register:
- `Tool(get_room_detail_details_from_photo, name="get_room_detail_details_from_photo")`

Tool wrapper behavior:
- If request is omitted:
  - use all uploaded images from state
  - error if none are available
- Persist one analysis row via `AnalysisRepository`
- Log concise operational facts:
  - image count
  - resolved room type
  - cross-image relationship

## Persistence Strategy
The current `analysis_runs` table stores only one `input_asset_id`.

For this tool, add a normalized join table now rather than packing the image list into JSON only.

Suggested table:
- `analysis_input_assets`

Suggested columns:
- `analysis_input_asset_id`
- `analysis_id`
- `asset_id`
- `ordinal`

Suggested invariants:
- foreign key from `analysis_id` to `analysis_runs.analysis_id`
- foreign key from `asset_id` to `assets.asset_id`
- unique constraint on `(analysis_id, ordinal)`
- unique constraint on `(analysis_id, asset_id)` if we want to prevent duplicate image references in one analysis run

Initial implementation:
- keep `analysis_runs.input_asset_id` for backward compatibility with existing code paths
- persist the first image as `analysis_runs.input_asset_id`
- persist every input image in `analysis_input_assets` with stable ordinal order
- persist the structured request in `request_json`
- persist the structured result in `result_json`
- persist no normalized detection rows for this tool

Reasoning:
- normalized input assets are safer than relying on JSON blobs for relational integrity
- preserving image order matters for `image_index` semantics in the output
- local-development stage is the right time to make schema changes while the data is disposable
- this avoids designing downstream analytics and debug tooling around a temporary shortcut

Repository behavior:
- extend `AnalysisRepository.record_analysis(...)` or add a specialized helper so one analysis run can persist multiple input assets atomically
- fail the whole write if any referenced asset is missing instead of partially persisting the analysis
- keep the request JSON as a full-fidelity payload, but treat the normalized rows as the source of truth for linked input assets

## Frontend Rendering Contract
Add a dedicated renderer under `ui/src/components/tooling/`.

Suggested component:
- `RoomDetailDetailsFromPhotoToolRenderer.tsx`

Renderer responsibilities:
- Show inferred room type and confidence
- Show cross-image relationship
- Show non-room image warnings when present
- Show grouped object lists for furniture, fixtures, lifestyle indicators, and other items
- Show per-image notes in compact form
- Remain idempotent across replays using the existing CopilotKit tool rendering model

Register in:
- `ui/src/components/copilotkit/CopilotToolRenderers.tsx`

If the renderer receives invalid payloads, fall back to `DefaultToolCallRenderer`.

## Testing Plan

### Python
- `tests/tools/test_image_analysis_models.py`
  - validate request min/max image rules
  - validate result serialization order and defaults
- `tests/tools/test_image_analysis_tool.py`
  - stub the internal `pydantic-ai` extractor call
  - verify attachments are loaded from the store
  - verify omitted request uses all uploaded images
  - verify malformed structured output raises a clean error
- `tests/persistence/...`
  - verify normalized `analysis_input_assets` rows are written in request order
  - verify the write is atomic when one referenced asset is missing
- `tests/chat/agents/...`
  - verify tool registration on image-analysis agent

### UI
- renderer unit test for:
  - success state
  - empty objects state
  - invalid payload fallback

### Behavioral Gate
Before calling the implementation ready:
- run `make tidy`
- run `make ui-test-e2e-real-ui-smoke`

## Risks
- Gemini structured output may still occasionally fail schema validation; the wrapper must fail cleanly and may need `PromptedOutput` fallback.
- Schema churn is acceptable here, but repository and migration code must stay aligned during local iteration.
- Room-type classification can be overconfident if the prompt is not conservative enough.
- Very large image batches can increase latency and cost sharply.

## Open Questions
- Whether the repeated tool name should be shortened before implementation. If we keep it, keep it forever.
- Whether `outdoor` belongs in the room-type union or should be represented only through `appears_to_show_room=False`.
- Whether later versions should include per-object confidence scores.

## Definition of Done
- The image-analysis agent can call `get_room_detail_details_from_photo` against uploaded images.
- The backend performs one Gemini multimodal call for the full image set.
- The tool returns the typed structured result above.
- The tool is persisted, logged, and rendered in the UI.
- Tests cover model validation, wrapper behavior, and renderer behavior.
