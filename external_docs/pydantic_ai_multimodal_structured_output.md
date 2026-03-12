# PydanticAI Multimodal Structured Output

Repo-local notes for the pattern used by `get_room_detail_details_from_photo`.

## Binary image input

PydanticAI accepts multimodal image input by passing `BinaryContent` values inside the `Agent.run(...)` user content list.

Pattern:

```python
from pydantic_ai import Agent, BinaryContent

result = await agent.run(
    [
        "Analyze these room photos.",
        BinaryContent(data=image_bytes, media_type="image/png"),
    ]
)
```

## Structured output

For providers that support native structured output, use `NativeOutput(MyModel)`.

Pattern:

```python
from pydantic_ai import Agent
from pydantic_ai.output import NativeOutput

agent = Agent(
    model=my_model,
    output_type=NativeOutput(MyModel),
)
```

## Fallback

If native structured output is not supported for the selected model/provider profile, the same extractor can fall back to `PromptedOutput(MyModel)`.

This is the pattern used in:

- `src/ikea_agent/tools/image_analysis/room_detail_tool.py`
