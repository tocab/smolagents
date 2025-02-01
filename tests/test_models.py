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
import json
import os
import unittest
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest
from transformers.testing_utils import get_tests_dir

from smolagents import ChatMessage, HfApiModel, TransformersModel, models, tool
from smolagents.models import get_clean_message_list, parse_json_if_needed


class ModelTests(unittest.TestCase):
    def test_get_json_schema_has_nullable_args(self):
        @tool
        def get_weather(location: str, celsius: Optional[bool] = False) -> str:
            """
            Get weather in the next days at given location.
            Secretly this tool does not care about the location, it hates the weather everywhere.

            Args:
                location: the location
                celsius: the temperature type
            """
            return "The weather is UNGODLY with torrential rains and temperatures below -10°C"

        assert (
            "nullable" in models.get_tool_json_schema(get_weather)["function"]["parameters"]["properties"]["celsius"]
        )

    def test_chatmessage_has_model_dumps_json(self):
        message = ChatMessage("user", [{"type": "text", "text": "Hello!"}])
        data = json.loads(message.model_dump_json())
        assert data["content"] == [{"type": "text", "text": "Hello!"}]

    def test_get_hfapi_message_no_tool(self):
        model = HfApiModel(max_tokens=10)
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hello!"}]}]
        model(messages, stop_sequences=["great"])

    @pytest.mark.skipif(not os.getenv("RUN_ALL"), reason="RUN_ALL environment variable not set")
    def test_get_hfapi_message_no_tool_external_provider(self):
        model = HfApiModel(model="Qwen/Qwen2.5-Coder-32B-Instruct", provider="together", max_tokens=10)
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hello!"}]}]
        model(messages, stop_sequences=["great"])

    def test_transformers_message_no_tool(self):
        model = TransformersModel(
            model_id="HuggingFaceTB/SmolLM2-135M-Instruct",
            max_new_tokens=5,
            device_map="auto",
            do_sample=False,
        )
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hello!"}]}]
        output = model(messages, stop_sequences=["great"]).content
        assert output == "assistant\nHello"

    def test_transformers_message_vl_no_tool(self):
        from PIL import Image

        img = Image.open(Path(get_tests_dir("fixtures")) / "000000039769.png")
        model = TransformersModel(
            model_id="llava-hf/llava-interleave-qwen-0.5b-hf",
            max_new_tokens=5,
            device_map="auto",
            do_sample=False,
        )
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hello!"}, {"type": "image", "image": img}]}]
        output = model(messages, stop_sequences=["great"]).content
        assert output == "Hello! How can"

    def test_parse_json_if_needed(self):
        args = "abc"
        parsed_args = parse_json_if_needed(args)
        assert parsed_args == "abc"

        args = '{"a": 3}'
        parsed_args = parse_json_if_needed(args)
        assert parsed_args == {"a": 3}

        args = "3"
        parsed_args = parse_json_if_needed(args)
        assert parsed_args == 3

        args = 3
        parsed_args = parse_json_if_needed(args)
        assert parsed_args == 3


def test_get_clean_message_list_basic():
    messages = [
        {"role": "user", "content": [{"type": "text", "text": "Hello!"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "Hi there!"}]},
    ]
    result = get_clean_message_list(messages)
    assert len(result) == 2
    assert result[0]["role"] == "user"
    assert result[0]["content"][0]["text"] == "Hello!"
    assert result[1]["role"] == "assistant"
    assert result[1]["content"][0]["text"] == "Hi there!"


def test_get_clean_message_list_role_conversions():
    messages = [
        {"role": "tool-call", "content": [{"type": "text", "text": "Calling tool..."}]},
        {"role": "tool-response", "content": [{"type": "text", "text": "Tool response"}]},
    ]
    result = get_clean_message_list(messages, role_conversions={"tool-call": "assistant", "tool-response": "user"})
    assert len(result) == 2
    assert result[0]["role"] == "assistant"
    assert result[0]["content"][0]["text"] == "Calling tool..."
    assert result[1]["role"] == "user"
    assert result[1]["content"][0]["text"] == "Tool response"


@pytest.mark.parametrize(
    "convert_images_to_image_urls, expected_clean_message",
    [
        (
            False,
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": "encoded_image"},
                    {"type": "image", "image": "second_encoded_image"},
                ],
            },
        ),
        (
            True,
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,encoded_image"}},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,second_encoded_image"}},
                ],
            },
        ),
    ],
)
def test_get_clean_message_list_image_encoding(convert_images_to_image_urls, expected_clean_message):
    messages = [
        {
            "role": "user",
            "content": [{"type": "image", "image": b"image_data"}, {"type": "image", "image": b"second_image_data"}],
        }
    ]
    with patch("smolagents.models.encode_image_base64") as mock_encode:
        mock_encode.side_effect = ["encoded_image", "second_encoded_image"]
        result = get_clean_message_list(messages, convert_images_to_image_urls=convert_images_to_image_urls)
        mock_encode.assert_any_call(b"image_data")
        mock_encode.assert_any_call(b"second_image_data")
        assert len(result) == 1
        assert result[0] == expected_clean_message


def test_get_clean_message_list_flatten_messages_as_text():
    messages = [
        {"role": "user", "content": [{"type": "text", "text": "Hello!"}]},
        {"role": "user", "content": [{"type": "text", "text": "How are you?"}]},
    ]
    result = get_clean_message_list(messages, flatten_messages_as_text=True)
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "Hello!How are you?"
