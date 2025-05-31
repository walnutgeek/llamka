import pytest

# from langchain_core.messages import HumanMessage, SystemMessage
# from llamka.llore.llm import get_llm


# This test will only run when --run-integration flag is provided
@pytest.mark.integration
def test_real_llm_api_call():
    """Test making a real API call to the LLM service."""
    # llore = Llore()
    # llm = get_llm()

    # messages = [
    #     SystemMessage(content="You are a helpful assistant."),
    #     HumanMessage(content="What is 2+2?")
    # ]

    # response = llm.invoke(messages)

    # # Basic assertions to verify the response
    # assert response is not None
    # assert hasattr(response, 'content')
    # assert isinstance(response.content, str)
    # assert len(response.content) > 0

    # # The response should contain the answer "4"
    # assert "4" in response.content
    pytest.skip("Test implementation pending")


@pytest.mark.integration
def test_real_llm_api_with_complex_prompt():
    """Test making a real API call with a more complex prompt."""
    # llm = get_llm()

    # messages = [
    #     SystemMessage(content="You are a helpful assistant that provides concise answers."),
    #     HumanMessage(content="Explain the concept of recursion in programming in one sentence.")
    # ]

    # response = llm.invoke(messages)

    # # Basic assertions
    # assert response is not None
    # assert hasattr(response, 'content')
    # assert isinstance(response.content, str)
    # assert len(response.content) > 0

    # # The response should contain relevant keywords
    # assert any(word in response.content.lower() for word in ['recursion', 'function', 'calls', 'itself'])
    pytest.skip("Test implementation pending")
