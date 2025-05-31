import pytest
from langchain_core.messages import ChatMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from llamka.llore.llm import response_to_chat_result

responses = {}
responses["4o"] = {
    "id": "chatcmpl-BWs1cmI1ywC87qPY6uddvY7P5NOo4",
    "object": "chat.completion",
    "created": 1747173868,
    "model": "gpt-4o-2024-08-06",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "The sky appears blue primarily due to a phenomenon called Rayleigh scattering. When sunlight enters Earth's atmosphere, it is made up of many colors that correspond to different wavelengths of light. The atmosphere is filled with gases and particles that scatter shorter wavelengths of light, like blue and violet, more than longer wavelengths, like red and yellow.\n\nEven though violet light is scattered even more than blue light due to its shorter wavelength, the sky does not appear violet to us because:\n\n1. Our eyes are more sensitive to blue light than violet.\n2. A significant amount of violet light is absorbed by the ozone layer in the atmosphere.\n\nAs a result, we perceive the sky as blue. This effect is most prominent when the sun is high in the sky. During sunrise and sunset, the light passes through a greater thickness of the Earth's atmosphere, scattering shorter wavelengths and allowing the longer wavelengths, such as red, orange, and yellow, to dominate the sky’s color during these times.",
                "refusal": None,
                "annotations": [],
            },
            "logprobs": None,
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 11,
        "completion_tokens": 194,
        "total_tokens": 205,
        "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0},
        "completion_tokens_details": {
            "reasoning_tokens": 0,
            "audio_tokens": 0,
            "accepted_prediction_tokens": 0,
            "rejected_prediction_tokens": 0,
        },
    },
    "service_tier": "default",
    "system_fingerprint": "fp_90122d973c",
}

responses["ollama_phi4"] = {
    "model": "phi4:latest",
    "created_at": "2025-05-13T22:30:11.079216Z",
    "message": {
        "role": "assistant",
        "content": "The sky appears blue due to a phenomenon called Rayleigh scattering. Here's how it works:\n\n1. **Sunlight Composition**: Sunlight, or white light, is made up of various colors, each with different wavelengths. Blue and violet light have shorter wavelengths, while red and orange light have longer wavelengths.\n\n2. **Earth’s Atmosphere**: The Earth's atmosphere contains molecules and small particles that scatter sunlight in all directions.\n\n3. **Rayleigh Scattering**: Shorter wavelengths (blue and violet) are scattered more efficiently than longer wavelengths (red and orange). This scattering is inversely proportional to the fourth power of wavelength, meaning shorter wavelengths scatter much more.\n\n4. **Perception by Humans**: Although violet light is scattered even more than blue, our eyes are more sensitive to blue light and less sensitive to violet. Additionally, some of the violet light is absorbed by the upper atmosphere.\n\n5. **Resulting Sky Color**: The combination of these factors results in the sky appearing predominantly blue during daylight hours when the sun is high in the sky.\n\nDuring sunrise and sunset, the sun's light passes through a greater thickness of Earth's atmosphere, scattering shorter wavelengths out of the line of sight and allowing longer wavelengths like reds and oranges to dominate, giving the sky its beautiful hues.",
    },
    "done_reason": "stop",
    "done": True,
    "total_duration": 12963622042,
    "load_duration": 16459709,
    "prompt_eval_count": 14,
    "prompt_eval_duration": 70956167,
    "eval_count": 260,
    "eval_duration": 12874686083,
}

responses["ollama_llama3_2"] = {
    "model": "llama3.2:latest",
    "created_at": "2025-05-13T22:36:09.859685Z",
    "message": {
        "role": "assistant",
        "content": "The sky appears blue because of a phenomenon called scattering, which occurs when sunlight interacts with the tiny molecules of gases in the Earth's atmosphere. Here's a simplified explanation:\n\n1. **Sunlight enters the atmosphere**: When sunlight enters the Earth's atmosphere, it encounters tiny molecules of gases such as nitrogen (N2) and oxygen (O2).\n2. **Scattering occurs**: These gas molecules scatter the light in all directions, but they scatter shorter (blue) wavelengths more than longer (red) wavelengths.\n3. **Blue light is scattered in all directions**: As a result, the blue light is dispersed throughout the atmosphere, reaching our eyes from all parts of the sky.\n4. **Our eyes perceive the scattered light as blue**: When we look up at the sky, we see the scattered blue light, which appears to be the dominant color of the sky.\n\nThis effect is more pronounced during the daytime when the sun is overhead and the atmosphere is relatively clear. At sunset and sunrise, the sky often takes on hues of red, orange, and pink due to the scattering of longer wavelengths by atmospheric particles.\n\nHere are some additional facts:\n\n* The exact shade of blue we see in the sky depends on factors such as air pollution, dust, and water vapor in the atmosphere.\n* In the ocean, water appears blue because of a similar scattering effect, where shorter wavelengths are scattered more than longer wavelengths.\n* On other planets with atmospheres, like Mars or Jupiter, the color of their skies can vary depending on the specific gases present.\n\nI hope this helps you understand why the sky is blue!",
    },
    "done_reason": "stop",
    "done": True,
    "total_duration": 4443947000,
    "load_duration": 21168667,
    "prompt_eval_count": 29,
    "prompt_eval_duration": 31821833,
    "eval_count": 323,
    "eval_duration": 4390044083,
}

responses["ollama_mistral"] = {
    "model": "mistral:latest",
    "created_at": "2025-05-13T22:38:08.25526Z",
    "message": {
        "role": "assistant",
        "content": " The sky appears blue because of a phenomenon called Rayleigh scattering. As sunlight reaches Earth, it is made up of different wavelengths or colors. Short-wavelength light (like violet and blue) are scattered in all directions more than other colors (like red, orange, yellow, and green) because they interact more with the molecules in the Earth's atmosphere. This scattering of blue and violet light toward us is what makes the sky look blue during a clear day. Our eyes are more sensitive to blue light and less sensitive to violet light, so we perceive the sky as blue instead of violet.",
    },
    "done_reason": "stop",
    "done": True,
    "total_duration": 4512194041,
    "load_duration": 1812028916,
    "prompt_eval_count": 9,
    "prompt_eval_duration": 116005125,
    "eval_count": 130,
    "eval_duration": 2582648958,
}

responses["sonnet"] = {
    "id": "msg_01G2zMu9SFzKVEpTyVUQXAp6",
    "type": "message",
    "role": "assistant",
    "model": "claude-3-7-sonnet-20250219",
    "content": [
        {
            "type": "text",
            "text": "The sky appears blue due to a phenomenon called Rayleigh scattering. Sunlight contains all colors of the visible spectrum, but as it passes through Earth's atmosphere, the air molecules scatter the shorter wavelengths of light (blue and violet) more effectively than longer wavelengths (like red and orange). \n\nThis scattered blue light comes at us from all directions in the sky, making the sky appear blue to our eyes. Interestingly, violet light is scattered even more than blue, but our eyes are more sensitive to blue light, which is why we perceive the sky as blue rather than violet.\n\nAt sunrise and sunset, the light travels through more atmosphere to reach us, causing most of the blue light to scatter away before it reaches our eyes, which is why the sky appears red or orange at those times.",
        }
    ],
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {
        "input_tokens": 11,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "output_tokens": 176,
    },
}


@pytest.mark.debug
def test_response_to_chat_result():
    for k, resp in responses.items():
        print(f"==== {k} ====")
        r = response_to_chat_result(resp)
        print(r)
        assert type(r) is ChatResult
        gen: ChatGeneration = r.generations[0]
        assert isinstance(gen.message, ChatMessage)
        msg: ChatMessage = gen.message
        assert msg.role == "assistant"
        assert isinstance(msg.content, str)
        assert msg.content.strip().startswith("The sky appears blue ")
    # assert False
