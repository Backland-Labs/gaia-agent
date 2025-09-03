#!/usr/bin/env python3
"""
GaiaNet Chatbot Streamlit UI - Simple chat interface
Integrates with backend API for secure chat completion
"""

import json
import time
from typing import Dict, List, Any

import requests
import streamlit as st


# Configuration
BACKEND_URL = "http://localhost:8080"
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30


def init_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None


def handle_api_response(response: requests.Response) -> Dict[str, Any]:
    """Handle API response with proper error handling"""
    if response.status_code == 200:
        return response.json()
    if response.status_code == 429:
        st.error("Rate limit exceeded. Please wait before sending another message.")
        return {"error": "rate_limit", "message": "Rate limit exceeded"}

    error_data = (response.json()
                  if response.headers.get('content-type', '').startswith('application/json')
                  else {})
    st.error(f"API Error: {error_data.get('error', 'Unknown error')}")
    return {"error": "api_error", "message": error_data.get('error', 'Unknown error')}


def call_chat_api(message: str, conversation: List[Dict[str, str]]) -> Dict[str, Any]:
    """Call backend chat API with error handling"""
    payload = {
        "message": message,
        "conversation": conversation
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/chat",
                json=payload,
                timeout=REQUEST_TIMEOUT
            )
            return handle_api_response(response)

        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES - 1:
                st.error("Request timed out. Please try again.")
                return {"error": "timeout", "message": "Request timed out"}
            time.sleep(1)
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend. Please ensure the backend is running.")
            return {"error": "connection", "message": "Backend connection failed"}
        except requests.exceptions.RequestException as e:
            st.error(f"Request error: {str(e)}")
            return {"error": "request", "message": str(e)}

    return {"error": "max_retries", "message": "Maximum retries exceeded"}


def stream_chat_response(message: str, conversation: List[Dict[str, str]]):
    """Handle streaming chat response with SSE"""
    payload = {
        "message": message,
        "conversation": conversation,
        "stream": True
    }

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/chat/stream",
            json=payload,
            stream=True,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            return call_chat_api(message, conversation)

        # Create placeholder for streaming response
        response_placeholder = st.empty()
        full_response = ""

        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith('data: '):
                try:
                    data = json.loads(line[6:])  # Remove 'data: ' prefix
                    if data.get('content'):
                        full_response += data['content']
                        response_placeholder.markdown(full_response + "▋")
                    elif data.get('done'):
                        break
                except json.JSONDecodeError:
                    continue

        # Remove cursor and return final response
        response_placeholder.markdown(full_response)
        return {"response": full_response}

    except requests.exceptions.RequestException as e:
        st.error(f"Streaming error: {str(e)}")
        return call_chat_api(message, conversation)


def get_backend_status() -> str:
    """Get backend health status"""
    try:
        health_response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            return health_data.get('status', 'Unknown')
        return "Error"
    except requests.exceptions.RequestException:
        return "Disconnected"


def render_sidebar():
    """Render sidebar with options and status"""
    with st.sidebar:
        st.header("Options")

        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

        # Show backend status
        status = get_backend_status()
        if status == "healthy":
            st.success(f"Backend Status: {status}")
        else:
            st.error(f"Backend Status: {status}")

        st.caption("💡 This chatbot connects directly to GaiaNet nodes for AI responses")


def process_user_message(prompt: str):
    """Process user message and generate response"""
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare conversation context for API
    conversation = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in st.session_state.messages[:-1]  # Exclude current user message
    ]

    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Try streaming first, fallback to regular API
            try:
                result = stream_chat_response(prompt, conversation)
            except requests.exceptions.RequestException:
                result = call_chat_api(prompt, conversation)

            if result.get("error"):
                st.error(f"Error: {result.get('message', 'Unknown error')}")
                assistant_response = ("I apologize, but I encountered an error "
                                      "processing your request. Please try again.")
            else:
                assistant_response = result.get(
                    "response", "I apologize, but I didn't receive a proper response."
                )

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": assistant_response})


def chat_interface():
    """Main chat interface"""
    st.title("🌍 GaiaNet Chatbot")
    st.caption("Powered by GaiaNet's decentralized AI network")

    # Initialize session state
    init_session_state()

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask me anything..."):
        process_user_message(prompt)

    # Sidebar with options
    render_sidebar()


def main():
    """Main application entry point"""
    # Page configuration
    st.set_page_config(
        page_title="GaiaNet Chatbot",
        page_icon="🌍",
        layout="centered",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for better mobile responsiveness
    st.markdown("""
        <style>
        .stApp {
            max-width: 1000px;
        }
        .stChatMessage {
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 0.5rem;
        }
        .stSpinner {
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

    # Run chat interface
    chat_interface()


if __name__ == "__main__":
    main()
