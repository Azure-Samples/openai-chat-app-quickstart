---
name: migrate-responses
description: Use this prompt to migrate a codebase from OpenAI Completions/Chat Completions API to the Responses API
model: Claude Opus 4.5 (copilot)
---

### Migration to OpenAI Responses API

You are migrating this repository from legacy OpenAI Completions/Chat Completions to the unified Responses API

#### Goals
- Enumerate all call sites using legacy endpoints/SDKs.
- Propose a per-language migration plan and sequencing.
- Apply safe, minimal edits to switch to Responses API.
- Update callers to consume the Responses output schema; no backcompat wrappers.
- Run tests/lints; fix trivial breakages introduced by the migration.
- Prepare small, reviewable change sets and provide a final summary with diffs (do not commit).

#### Guardrails
- Only modify files inside the git workspace. Never write outside.
- Do not preserve backward-compatibility shims; migrate code to the new API shape.
- Do not leave tombstone/transition comments or backup files.
- Preserve streaming semantics if previously used; otherwise use non-streaming.
- Ask for approval before running commands or network calls if approval mode.
- Do not run `git add`/`git commit`/`git push`; leave version control to the bootstrap script. Produce working-tree edits only.


#### Heuristics (detect and rewrite)
- Node: `createCompletion`, `OpenAIApi`, `ChatCompletion` → `OpenAI` + `client.responses.create(...)`.
- Python: `openai.Completion.create`, `openai.ChatCompletion.create` → `OpenAI()` + `client.responses.create(...)`.
- cURL/infra: `POST /v1/completions` → `POST /v1/responses`; map `prompt`→`input`, `max_tokens`→`max_output_tokens`.
- Tools: convert function-calling to `tools` with JSON Schema; use `tool_choice`; return tool results as a `tool` role turn in the next request.
- Multi-turn: maintain conversation history in the app; pass prior turns via `input` items.
- Formatting: replace Chat’s top-level `response_format` with `text.format` in Responses. Prefer a JSON Schema wrapper with `format.name` (e.g., `text: { format: { type: "json_schema", name: "Output", json_schema: { strict, schema } } }`). Remove the legacy field; avoid plain string formats.
- Content items: replace Chat `content[].type: "text"` with Responses `content[].type: "input_text"` for user/system turns; for assistant/tool outputs, prefer `content[].type: "output_text"`.
- Reasoning effort: **only migrate `reasoning` if it already exists in the original code**. Do not add `reasoning` to calls that didn't have it. If the original code used `reasoning`, preserve the existing effort level.

#### Acceptance
- All legacy Completions/ChatCompletion calls replaced with Responses equivalents.
- Imports/initialization updated; builds/tests pass or clear TODOs noted.
- Callers updated to consume Responses outputs (no legacy shapes retained).
- If migrating to gpt-5, ensure temperature is omitted or set to 1.
- Replace any top-level `response_format` usage with `text.format` and update parsing accordingly (e.g., `JSON.parse(res.output_text)`).
- Ensure the OpenAI SDK is upgraded to a version supporting Responses (e.g., Node `openai@latest`, Python `pip install -U openai`) and dependencies reinstalled.
- Project builds cleanly (e.g., `npm run build` / `pnpm build` / `yarn build`) when applicable.
- Always set `store: false`; do not rely on previous message IDs or server-stored context; keep conversation state in-app.
- Summary includes edited files, before/after counts of legacy calls, and next steps.

---

### Migration notes (Completions → Responses)

- **Why migrate**: Responses is the unified API for text, tools, and streaming; Completions/Chat Completions are legacy. With GPT‑5, Responses is required for best performance: GPT‑5 orchestrates tool calls as part of its internal reasoning and relies on Responses’ structured tool flow. Staying on Completions can degrade intelligence and cause repeated tool calls because legacy endpoints don’t preserve the model’s tool context.
- **HTTP**: switch `POST /v1/completions` → `POST /v1/responses`.
- **Fields**: `prompt` → `input`, `max_tokens` → `max_output_tokens`. `temperature` remains.
- **Formatting**: `response_format` from Chat Completions is not supported at the top level. Use `text.format` with a proper object. Prefer JSON Schema: `{ text: { format: { type: "json_schema", name, strict, schema } } }`. Avoid plain strings.
- **Content items**: Replace Chat `content[].type: "text"` with Responses `content[].type: "input_text"` for system/user turns. For assistant or tool outputs, prefer `content[].type: "output_text"`.
- **Images**: Replace Chat image parts with Responses `content[].type: "input_image"` plus `image_url` or image data.

---

### Azure OpenAI client migration (prerequisite)

If the codebase uses `AzureOpenAI` or `AsyncAzureOpenAI` constructors, migrate to the standard `OpenAI` / `AsyncOpenAI` constructors first. The Azure-specific constructors are deprecated in `openai>=1.108.1`.

#### Python migration

Before (deprecated):

```python
from openai import AsyncAzureOpenAI

client = AsyncAzureOpenAI(
    api_version=os.environ["AZURE_OPENAI_VERSION"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_ad_token_provider=token_provider,
)
```

After (current):

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=token_provider,
)
```

#### Key changes

| Before | After |
|--------|-------|
| `AzureOpenAI` | `OpenAI` |
| `AsyncAzureOpenAI` | `AsyncOpenAI` |
| `azure_endpoint` | `base_url` |
| `azure_ad_token_provider` | `api_key` |
| `api_version=...` | Remove entirely |

#### Cleanup checklist

- Remove `api_version` argument from client construction.
- Remove `AZURE_OPENAI_VERSION` / `AZURE_OPENAI_API_VERSION` environment variables from `.env`, app settings, and Bicep/infra files.
- Ensure `openai>=1.108.1` in `requirements.txt` or `pyproject.toml`.

#### Azure OpenAI endpoint path

Azure OpenAI uses `/openai/v1/responses` as the Responses API path (not `/v1/responses` like the OpenAI API). When using the SDK with `base_url`, ensure the endpoint includes the `/openai/v1` path prefix:

```python
client = AsyncOpenAI(
    base_url=f"{os.environ['AZURE_OPENAI_ENDPOINT']}/openai/v1",
    api_key=token_provider,
)
# The deployment name is passed as the model parameter
resp = client.responses.create(model="your-deployment-name", input="Hello")
```

For more details, see the [Azure OpenAI Responses API documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses).

---

### Responses API cheat‑sheet

- **Endpoint**: `POST /v1/responses`
- **Basic request**:

```json
{ "model": "gpt-5", "input": "Hello" }
```

- **Streaming**: add `"stream": true` and handle SSE events. See streaming guide.
- **Parameter mapping**:
  - **prompt → input** (string or array of items)
  - **max_tokens → max_output_tokens**
  - **response_format (chat) → text.format (responses)**.
    - Prefer JSON Schema for structured outputs. Required shape (top-level name/schema):
      - `{ text: { format: { type: "json_schema", name: "Output", strict: true, schema: { ... } } } }`
    - If using simple JSON, some SDKs may accept a helper (e.g., `zodResponseFormat`) that produces the correct schema wrapper. Avoid plain strings (e.g., `format: "json"`) which may 400.
  - **temperature**: unchanged
  - **stop, frequency_penalty, presence_penalty**: supported as relevant
  - **tools/function-calling**: use `tools` in Responses
  - **store**: set to `false` by default to avoid retaining response objects and reduce overhead
  - **seed**: not supported in Responses; remove if present

- **SDK idioms**:
  - Node:

```js
import OpenAI from "openai";
const client = new OpenAI();
const res = await client.responses.create({ model: "gpt-5", input: "Hello" });
console.log(res.output_text);
```

  - Python:

```python
from openai import OpenAI
client = OpenAI()
resp = client.responses.create(model="gpt-5", input="Hello")
print(resp.output_text)
```

- **Streaming (Node)**:

```js
const stream = await client.responses.create({ model: "gpt-5", input: "stream me", stream: true });
for await (const event of stream) {
  if (event.delta) process.stdout.write(event.delta);
}
```

- **Streaming event sequence**: When `stream: true`, the API emits events in this order:
  1. `response.created` – response object initialized
  2. `response.in_progress` – generation started
  3. `response.output_item.added` – output item created
  4. `response.content_part.added` – content part started
  5. `response.output_text.delta` – text chunks (multiple, each has `delta: string`)
  6. `response.output_text.done` – text generation finished
  7. `response.content_part.done` – content part finished
  8. `response.output_item.done` – output item finished
  9. `response.completed` – full response complete

  For basic text streaming, only handle `response.output_text.delta` (for text chunks) and `response.completed` (for finish). Other events can be ignored unless you need fine-grained progress tracking.

- **Streaming event types (Python SDK)**:
  - `ResponseTextDeltaEvent`: `type='response.output_text.delta'`, `delta: str`
  - `ResponseCompletedEvent`: `type='response.completed'`, `response: Response`

- **Mocking streaming responses (Python pytest)**:

```python
class MockResponseEvent:
    """Mock event for Responses API streaming."""
    def __init__(self, event_type: str, delta: str | None = None):
        self.type = event_type
        self.delta = delta

class AsyncResponsesIterator:
    """Async iterator for mocking Responses API streaming."""
    def __init__(self, answer: str):
        self.events = []
        for word in answer.split(" "):
            self.events.append(MockResponseEvent("response.output_text.delta", word))
        self.events.append(MockResponseEvent("response.completed"))
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index < len(self.events):
            event = self.events[self.index]
            self.index += 1
            return event
        raise StopAsyncIteration

# In fixture:
async def mock_create(*args, **kwargs):
    return AsyncResponsesIterator("Hello world!")

monkeypatch.setattr("openai.resources.responses.AsyncResponses.create", mock_create)
```

- **Image input (Node)**:

```js
const res = await client.responses.create({
  model: "gpt-5",
  input: [
    { role: "user", content: "What two teams are playing?" },
    { role: "user", content: [ { type: "input_image", image_url: "https://example.com/image.jpg" } ] }
  ]
});
console.log(res.output_text);
```

- **Quick cURL test**:

```bash
curl https://api.openai.com/v1/responses \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5",
    "input": [{ "role": "user", "content": [{ "type": "input_text", "text": "Return a JSON object with key answer" }] }],
    "text": { "format": { "type": "json_schema", "name": "Output", "strict": true, "schema": { "type": "object", "properties": { "answer": { "type": "string" } }, "required": ["answer"], "additionalProperties": false } } }
  }'
```

- **Tool use**:
  - Define functions in `tools` with JSON Schema params; let the model decide with `tool_choice: "auto"` or force a specific tool.
  - When the model asks to call a tool, execute it in your app and include the tool result in the next request as a `tool` role item within `input`.
  - Keep schemas minimal; validate inputs before execution.
  - Built‑in example (web search preview):

```js
const res = await client.responses.create({
  model: "gpt-5",
  tools: [{ type: "web_search_preview" }],
  input: "What was a positive news story from today?"
});
console.log(res.output_text);
```

- **Reasoning**: Only include `reasoning` if the original code already used it. Do not add `reasoning` to API calls that didn't have it—many models (e.g., gpt-4o-mini) don't support this parameter.

- **Multi‑turn**:
  - Manage conversation state in your app; pass prior turns explicitly via `input` items.
  - Use `type: "input_text"` for user/system turns, and `type: "output_text"` for assistant/tool outputs.
  - Always set `store: false`; do not rely on previous message IDs or server‑stored context.

```js
const input = [
  { role: "system", content: [{ type: "input_text", text: "You are helpful." }] },
  { role: "user", content: [{ type: "input_text", text: "Hi" }] },
  { role: "assistant", content: [{ type: "output_text", text: "Hello!" }] },
  { role: "user", content: [{ type: "input_text", text: "Tell me a joke" }] }
];
const res = await client.responses.create({ model: "gpt-5", input });
```

- **Structured output (JSON Schema)**:

```js
const schema = {
  type: "object",
  properties: { answer: { type: "string" } },
  required: ["answer"],
  additionalProperties: false
};
const res = await client.responses.create({
  model: "gpt-5",
  input,
  text: {
    format: { type: "json_schema", json_schema: { name: "Output", strict: true, schema } }
  }
});
const data = JSON.parse(res.output_text);
```

- **Data retention & state**:
  - Set `store: false` on all Responses requests.
  - Do not rely on previous message IDs or server‑stored context; keep state local and minimize logged metadata.

- **Gotchas**:
  - If you previously used Chat Completions for conversation state, manage your own state explicitly with Responses.
  - Prefer `max_output_tokens` over legacy `max_tokens`.
  - When migrating to `gpt-5`, ensure `temperature` is not specified or is set to `1`.
  - Replace Chat `content[].type: "text"` with Responses `content[].type: "input_text"` for user/system inputs.
  - For `text.format`, supply a proper object (e.g., `{ type: "json_schema", name, schema, strict }`), not a plain string.
  - The `seed` parameter is not supported in Responses; remove it from requests.

- **Auto-convert legacy `response_format` (example transformer)**:

```js
function upgradeResponseFormat(body) {
  if (!body || body.text?.format) return body;
  const rf = body.response_format;
  if (!rf) return body;
  let format;
  if (rf === "json") {
    format = { type: "json_schema", name: "Output", strict: true, schema: { type: "object" } };
  } else if (typeof rf === "object") {
    // Attempt to wrap arbitrary schema
    format = { type: "json_schema", name: rf.name || "Output", strict: rf.strict ?? true, schema: rf.schema || { type: "object" } };
  }
  const { response_format, ...rest } = body;
  return format ? { ...rest, text: { format } } : rest;
}
```

- **Troubleshooting 400s**:
  - `missing_required_parameter: text.format.name` → add `json_schema.name` (e.g., "Output").
  - `invalid_type: text.format` → ensure it is an object `{ type, json_schema }`, not a string.
  - `invalid input content type` → use `input_text`/`output_text` content types instead of Chat `text`.

---
### Python migration (Completions/Chat → Responses)

Before (legacy):

```python
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")
resp = openai.Completion.create(model="text-davinci-003", prompt="Hello")
print(resp["choices"][0]["text"])
```

After (Responses API):

```python
from openai import OpenAI
client = OpenAI()
resp = client.responses.create(model="gpt-5", input="Hello", store=False)
print(resp.output_text)
```

Mappings:
- prompt → input
- max_tokens → max_output_tokens
- temperature unchanged

Streaming: follow the library's streaming guide if previously used.



- **Reasoning**: Only migrate `reasoning` if it was already present in the original Chat Completions code. Do not add it to calls that didn't have it—many models don't support this parameter.

Example transformer (Node/TypeScript):

```ts
function toResponsesPayload(body: any): any {
  const out: any = { ...body };
  // Map response_format → text.format
  if (!out.text?.format && out.response_format) {
    const rf = out.response_format;
    if (rf === "json") {
      out.text = { format: { type: "json_schema", name: "Output", strict: true, schema: { type: "object" } } };
    } else if (typeof rf === "object") {
      out.text = { format: { type: "json_schema", name: rf.name ?? "Output", strict: rf.strict ?? true, schema: rf.schema ?? { type: "object" } } };
    }
    delete out.response_format;
  }
  // Ensure content types
  if (Array.isArray(out.input)) {
    out.input = out.input.map((turn: any) => ({
      ...turn,
      content: Array.isArray(turn.content)
        ? turn.content.map((c: any) => (c?.type === "text" ? { ...c, type: "input_text" } : c))
        : turn.content,
    }));
  }
  return out;
}
```
- **SDKs**: use the official OpenAI libraries; initialize `OpenAI` client and call `client.responses.create(...)`.
- **SDK versions**: upgrade to a version that supports Responses (Node `openai@latest`; Python `pip install -U openai`) and reinstall dependencies.
- **Azure OpenAI**: check [API version lifecycle](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/api-version-lifecycle?view=foundry-classic&tabs=python#api-evolution) for Responses API support; ensure your deployment uses a compatible `api-version`.
- **Streaming**: set `stream: true` and handle SSE events (see docs). Only enable if the original used streaming.
- **Tools**: move Chat Completions function-calling to `tools` with JSON Schema; use `tool_choice` as needed. Provide tool results back via a follow‑up call including a `tool` role item in `input`.
- **Multi‑turn**: manage conversation state in your app; pass prior turns explicitly using `input` items (system/user/assistant/tool). Do not assume server‑side memory by default.
- **Storage**: Default to `store: false` in all cases to reduce overhead and avoid server retention.
- **Data retention & state**:
  - Set `store: false` on all Responses requests.
  - Do not rely on previous message IDs or any server‑stored context; keep state client‑managed and minimize metadata.
- **Deprecations**: do not hardcode dates—link to the official deprecations page in user docs.

See also: `docs/language-recipes/*.md` for idiomatic code diffs.
