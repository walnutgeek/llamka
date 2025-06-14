import requests
import streamlit as st

from botglue.llore.api import ChatMsg, ChatRequest, ChatResponse, Models


def init_session_state():
    if "models" not in st.session_state:
        st.session_state.models = send_models_request()
    if "messages" not in st.session_state:
        st.session_state.messages = []


def send_models_request() -> Models:
    url = "http://localhost:7532/models"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code} - {response.text}")
    return Models.model_validate_json(response.content)


def send_chat_request(
    messages: list[ChatMsg], bot_name: str | None = None, llm_name: str | None = None
) -> ChatResponse:
    url = "http://localhost:7532/chats"
    request = ChatRequest(messages=messages, bot_name=bot_name, llm_name=llm_name)
    response = requests.post(url, json=request.model_dump(mode="json"))
    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code} - {response.text}")
    return ChatResponse.model_validate_json(response.content)


st.title("botglue Chat")

init_session_state()

# Sidebar for configuration
with st.sidebar:
    bot_name = st.selectbox("Bot", options=[None, *st.session_state.models.bots])
    llm_name = st.selectbox("LLM", options=[None, *st.session_state.models.llms])
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()


def display_message(message: ChatMsg):
    with st.chat_message(message.role):
        st.write(message.content)


# Display chat messages
for message in st.session_state.messages:
    display_message(message)

# Chat input
if prompt := st.chat_input("What's on your mind?"):
    # Add user message to chat history
    new_msg = ChatMsg(role="user", content=prompt)
    st.session_state.messages.append(new_msg)
    display_message(new_msg)

    # Get bot response
    try:
        response = send_chat_request(
            messages=st.session_state.messages, bot_name=bot_name, llm_name=llm_name
        )

        # Add assistant response to chat history
        st.session_state.messages.append(response.generation)
        display_message(response.generation)

    except Exception as e:
        st.error(f"Error: {str(e)}")
