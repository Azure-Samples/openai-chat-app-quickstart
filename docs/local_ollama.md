# Running against a local LLM server

You may want to save costs by developing against a local LLM server, such as
[llamafile](https://github.com/Mozilla-Ocho/llamafile/). Note that a local LLM
will generally be slower and not as sophisticated.

Once you've got your local LLM running and serving an OpenAI-compatible endpoint, define `LOCAL_OPENAI_ENDPOINT` in your `.env` file.

For example, to point at a local llamafile server running on its default port:

```shell
LOCAL_OPENAI_ENDPOINT="http://localhost:8080/v1"
```

If you're running inside a dev container, use this local URL instead:

```shell
LOCAL_OPENAI_ENDPOINT="http://host.docker.internal:8080/v1"
```
