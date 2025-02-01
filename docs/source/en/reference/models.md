<!--Copyright 2024 The HuggingFace Team. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

⚠️ Note that this file is in Markdown but contain specific syntax for our doc-builder (similar to MDX) that may not be
rendered properly in your Markdown viewer.

-->
# Models

<Tip warning={true}>

Smolagents is an experimental API which is subject to change at any time. Results returned by the agents
can vary as the APIs or underlying models are prone to change.

</Tip>

To learn more about agents and tools make sure to read the [introductory guide](../index). This page
contains the API docs for the underlying classes.

## Models

You're free to create and use your own models to power your agent.

You could use any `model` callable for your agent, as long as:
1. It follows the [messages format](./chat_templating) (`List[Dict[str, str]]`) for its input `messages`, and it returns a `str`.
2. It stops generating outputs *before* the sequences passed in the argument `stop_sequences`

For defining your LLM, you can make a `custom_model` method which accepts a list of [messages](./chat_templating) and returns an object with a .content attribute containing the text. This callable also needs to accept a `stop_sequences` argument that indicates when to stop generating.

```python
from huggingface_hub import login, InferenceClient

login("<YOUR_HUGGINGFACEHUB_API_TOKEN>")

model_id = "meta-llama/Llama-3.3-70B-Instruct"

client = InferenceClient(model=model_id)

def custom_model(messages, stop_sequences=["Task"]):
    response = client.chat_completion(messages, stop=stop_sequences, max_tokens=1000)
    answer = response.choices[0].message
    return answer
```

Additionally, `custom_model` can also take a `grammar` argument. In the case where you specify a `grammar` upon agent initialization, this argument will be passed to the calls to model, with the `grammar` that you defined upon initialization, to allow [constrained generation](https://huggingface.co/docs/text-generation-inference/conceptual/guidance) in order to force properly-formatted agent outputs.

### TransformersModel

For convenience, we have added a `TransformersModel` that implements the points above by building a local `transformers` pipeline for the model_id given at initialization.

```python
from smolagents import TransformersModel

model = TransformersModel(model_id="HuggingFaceTB/SmolLM-135M-Instruct")

print(model([{"role": "user", "content": "Ok!"}], stop_sequences=["great"]))
```
```text
>>> What a
```

> [!TIP]
> You must have `transformers` and `torch` installed on your machine. Please run `pip install smolagents[transformers]` if it's not the case.

[[autodoc]] TransformersModel

### HfApiModel

The `HfApiModel` wraps huggingface_hub's [InferenceClient](https://huggingface.co/docs/huggingface_hub/main/en/guides/inference) for the execution of the LLM. It supports both HF's own [Inference API](https://huggingface.co/docs/api-inference/index) as well as all [Inference Providers](https://huggingface.co/blog/inference-providers) available on the Hub.

```python
from smolagents import HfApiModel

messages = [
  {"role": "user", "content": "Hello, how are you?"},
  {"role": "assistant", "content": "I'm doing great. How can I help you today?"},
  {"role": "user", "content": "No need to help, take it easy."},
]

model = HfApiModel()
print(model(messages))
```
```text
>>> Of course! If you change your mind, feel free to reach out. Take care!
```
[[autodoc]] HfApiModel

### LiteLLMModel

The `LiteLLMModel` leverages [LiteLLM](https://www.litellm.ai/) to support 100+ LLMs from various providers.
You can pass kwargs upon model initialization that will then be used whenever using the model, for instance below we pass `temperature`.

```python
from smolagents import LiteLLMModel

messages = [
  {"role": "user", "content": "Hello, how are you?"},
  {"role": "assistant", "content": "I'm doing great. How can I help you today?"},
  {"role": "user", "content": "No need to help, take it easy."},
]

model = LiteLLMModel("anthropic/claude-3-5-sonnet-latest", temperature=0.2, max_tokens=10)
print(model(messages))
```

[[autodoc]] LiteLLMModel

### OpenAIServerModel

This class lets you call any OpenAIServer compatible model.
Here's how you can set it (you can customise the `api_base` url to point to another server):
```py
from smolagents import OpenAIServerModel

model = OpenAIServerModel(
    model_id="gpt-4o",
    api_base="https://api.openai.com/v1",
    api_key=os.environ["OPENAI_API_KEY"],
)
```

[[autodoc]] OpenAIServerModel

### AzureOpenAIServerModel

`AzureOpenAIServerModel` allows you to connect to any Azure OpenAI deployment. 

Below you can find an example of how to set it up, note that you can omit the `azure_endpoint`, `api_key`, and `api_version` arguments, provided you've set the corresponding environment variables -- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, and `OPENAI_API_VERSION`.

Pay attention to the lack of an `AZURE_` prefix for `OPENAI_API_VERSION`, this is due to the way the underlying [openai](https://github.com/openai/openai-python) package is designed. 

```py
import os

from smolagents import AzureOpenAIServerModel

model = AzureOpenAIServerModel(
    model_id = os.environ.get("AZURE_OPENAI_MODEL"),
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
    api_version=os.environ.get("OPENAI_API_VERSION")    
)
```

[[autodoc]] AzureOpenAIServerModel