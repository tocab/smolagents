# coding=utf-8
# Copyright 2024 HuggingFace Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

from smolagents import (
    AgentError,
    AgentImage,
    CodeAgent,
    ToolCallingAgent,
    stream_to_gradio,
)
from smolagents.models import (
    ChatMessage,
    ChatMessageToolCall,
    ChatMessageToolCallDefinition,
)
from smolagents.monitoring import AgentLogger, LogLevel


class FakeLLMModel:
    def __init__(self):
        self.last_input_token_count = 10
        self.last_output_token_count = 20

    def __call__(self, prompt, tools_to_call_from=None, **kwargs):
        if tools_to_call_from is not None:
            return ChatMessage(
                role="assistant",
                content="",
                tool_calls=[
                    ChatMessageToolCall(
                        id="fake_id",
                        type="function",
                        function=ChatMessageToolCallDefinition(name="final_answer", arguments={"answer": "image"}),
                    )
                ],
            )
        else:
            return ChatMessage(
                role="assistant",
                content="""
Code:
```py
final_answer('This is the final answer.')
```""",
            )


class MonitoringTester(unittest.TestCase):
    def test_code_agent_metrics(self):
        agent = CodeAgent(
            tools=[],
            model=FakeLLMModel(),
            max_steps=1,
        )
        agent.run("Fake task")

        self.assertEqual(agent.monitor.total_input_token_count, 10)
        self.assertEqual(agent.monitor.total_output_token_count, 20)

    def test_toolcalling_agent_metrics(self):
        agent = ToolCallingAgent(
            tools=[],
            model=FakeLLMModel(),
            max_steps=1,
        )

        agent.run("Fake task")

        self.assertEqual(agent.monitor.total_input_token_count, 10)
        self.assertEqual(agent.monitor.total_output_token_count, 20)

    def test_code_agent_metrics_max_steps(self):
        class FakeLLMModelMalformedAnswer:
            def __init__(self):
                self.last_input_token_count = 10
                self.last_output_token_count = 20

            def __call__(self, prompt, **kwargs):
                return ChatMessage(role="assistant", content="Malformed answer")

        agent = CodeAgent(
            tools=[],
            model=FakeLLMModelMalformedAnswer(),
            max_steps=1,
        )

        agent.run("Fake task")

        self.assertEqual(agent.monitor.total_input_token_count, 20)
        self.assertEqual(agent.monitor.total_output_token_count, 40)

    def test_code_agent_metrics_generation_error(self):
        class FakeLLMModelGenerationException:
            def __init__(self):
                self.last_input_token_count = 10
                self.last_output_token_count = 20

            def __call__(self, prompt, **kwargs):
                self.last_input_token_count = 10
                self.last_output_token_count = 0
                raise Exception("Cannot generate")

        agent = CodeAgent(
            tools=[],
            model=FakeLLMModelGenerationException(),
            max_steps=1,
        )
        agent.run("Fake task")

        self.assertEqual(agent.monitor.total_input_token_count, 20)  # Should have done two monitoring callbacks
        self.assertEqual(agent.monitor.total_output_token_count, 0)

    def test_streaming_agent_text_output(self):
        agent = CodeAgent(
            tools=[],
            model=FakeLLMModel(),
            max_steps=1,
        )

        # Use stream_to_gradio to capture the output
        outputs = list(stream_to_gradio(agent, task="Test task"))

        self.assertEqual(len(outputs), 7)
        final_message = outputs[-1]
        self.assertEqual(final_message.role, "assistant")
        self.assertIn("This is the final answer.", final_message.content)

    def test_streaming_agent_image_output(self):
        agent = ToolCallingAgent(
            tools=[],
            model=FakeLLMModel(),
            max_steps=1,
        )

        # Use stream_to_gradio to capture the output
        outputs = list(
            stream_to_gradio(
                agent,
                task="Test task",
                additional_args=dict(image=AgentImage(value="path.png")),
            )
        )

        self.assertEqual(len(outputs), 5)
        final_message = outputs[-1]
        self.assertEqual(final_message.role, "assistant")
        self.assertIsInstance(final_message.content, dict)
        self.assertEqual(final_message.content["path"], "path.png")
        self.assertEqual(final_message.content["mime_type"], "image/png")

    def test_streaming_with_agent_error(self):
        logger = AgentLogger(level=LogLevel.INFO)

        def dummy_model(prompt, **kwargs):
            raise AgentError("Simulated agent error", logger)

        agent = CodeAgent(
            tools=[],
            model=dummy_model,
            max_steps=1,
        )

        # Use stream_to_gradio to capture the output
        outputs = list(stream_to_gradio(agent, task="Test task"))

        self.assertEqual(len(outputs), 9)
        final_message = outputs[-1]
        self.assertEqual(final_message.role, "assistant")
        self.assertIn("Simulated agent error", final_message.content)
