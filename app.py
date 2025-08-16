"""Minimal Strands Agent Streamlit Application."""

import streamlit as st
import json
import os
from datetime import datetime
from strands import Agent
from strands.models import BedrockModel
from strands_tools import calculator

# Set page config
st.set_page_config(
    page_title="AI Agent Chat",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state for chat history and agent
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Initialize file uploader key for clearing after uploads
if 'file_uploader_key' not in st.session_state:
    st.session_state.file_uploader_key = 0

if 'agent' not in st.session_state:
    # Initialize Bedrock model with basic settings
    bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",  # Update model ID as needed
        temperature=0.1,
        top_p=0.9,
        max_tokens=4000,
        region_name="us-east-1"  # Update region as needed
    )
    
    # State for tracking current message components
    st.session_state.accumulated_text = ""
    st.session_state.current_message_tools = []
    st.session_state.current_message_results = []
    st.session_state.current_message_accumulated = ""  # Store accumulated text per message
    st.session_state.all_agent_text = ""  # Store ALL text from entire agent call
    st.session_state.conversation_flow = []  # Track the chronological flow of thoughts and tools

    def callback_handler(**kwargs):
        """Handle streaming responses and tool calls."""
        
        # Handle streaming text data
        if "data" in kwargs and kwargs["data"]:
            st.session_state.accumulated_text += kwargs["data"]
            st.session_state.all_agent_text += kwargs["data"]  # Accumulate ALL text
            # Don't display streaming text here - let it accumulate
        
        # Handle tool use streaming (current_tool_use indicates tool call being built)
        elif "current_tool_use" in kwargs:
            # We'll handle the complete tool call in the "message" callback
            pass
        
        # Handle complete messages (both assistant and user messages)
        elif "message" in kwargs:
            message = kwargs["message"]
            
            # Handle assistant messages with tool calls
            if message.get("role") == "assistant" and "content" in message:
                
                for i, content in enumerate(message["content"]):
                    # Handle text content first
                    if "text" in content:
                        text_content = content["text"]
                        # Display this text chunk immediately
                        st.write(text_content)
                        # Add to conversation flow
                        st.session_state.conversation_flow.append({
                            "type": "text",
                            "content": text_content
                        })
                    
                    # Handle tool calls
                    elif "toolUse" in content:
                        tool_use = content["toolUse"]
                        
                        tool_info = {
                            "name": tool_use["name"],
                            "input": tool_use["input"],
                            "tool_use_id": tool_use["toolUseId"]
                        }
                        
                        # Display tool call in real-time
                        st.info(f"🔧 **Tool Call:** {tool_use['name']}")
                        with st.expander("Tool Input", expanded=False):
                            st.json(tool_use["input"])
                        
                        # Add to conversation flow
                        st.session_state.conversation_flow.append({
                            "type": "tool_call",
                            "tool": tool_info
                        })
                        
                        # Store for chat history
                        st.session_state.current_message_tools.append(tool_info)
            
            # Handle tool results (come as user messages)
            elif message.get("role") == "user" and "content" in message:
                for i, content in enumerate(message["content"]):
                    if "toolResult" in content:
                        result = content["toolResult"]
                        
                        result_info = {
                            "status": result.get("status"),
                            "content": result.get("content", [])
                        }
                        
                        # Display tool result in real-time
                        if result.get("status") == "success":
                            st.success("✅ **Tool Result:** Success")
                            
                            # Display result content in expandable format
                            result_content = result.get("content", [])
                            if result_content:
                                with st.expander("Tool Result", expanded=True):
                                    for item in result_content:
                                        if "text" in item:
                                            st.code(item["text"])
                                        elif "json" in item:
                                            st.json(item["json"])
                        else:
                            st.error(f"❌ **Tool Result:** {result.get('status', 'Failed')}")
                            if "content" in result:
                                with st.expander("Error Details", expanded=True):
                                    st.code(str(result["content"]))
                        
                        # Add to conversation flow
                        st.session_state.conversation_flow.append({
                            "type": "tool_result",
                            "result": result_info
                        })
                        
                        # Store for chat history
                        st.session_state.current_message_results.append(result_info)
        
        # Ignore other callback types (events, lifecycle, etc.)
        else:
            pass

    # Create agent with your tools (replace with your actual tools)
    # Example tools - replace with your actual tool imports
    tools = [calculator]  # Add your tools here: [tool1, tool2, tool3]
    
    st.session_state.agent = Agent(
        tools=tools,
        callback_handler=callback_handler,
        model=bedrock_model,
        system_prompt="You are a helpful AI assistant. Use the available tools to help users with their requests."
    )

# Main UI
st.title("🤖 AI Agent Chat")
st.markdown("Chat with an AI agent that can use tools to help you.")

# Display chat messages
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        # For assistant messages with conversation flow, display in chronological order
        if message["role"] == "assistant" and "conversation_flow" in message:
            for flow_item in message["conversation_flow"]:
                if flow_item["type"] == "text":
                    st.write(flow_item["content"])
                elif flow_item["type"] == "tool_call":
                    tool = flow_item["tool"]
                    st.info(f"🔧 **Tool Call:** {tool['name']}")
                    with st.expander("Tool Input", expanded=False):
                        st.json(tool["input"])
                elif flow_item["type"] == "tool_result":
                    result = flow_item["result"]
                    if result["status"] == "success":
                        st.success("✅ **Tool Result:** Success")
                    else:
                        st.error(f"❌ **Tool Result:** {result['status']}")
                    
                    # Display result content in expandable format
                    with st.expander("Tool Result", expanded=False):
                        for item in result.get("content", []):
                            if "text" in item:
                                st.code(item["text"])
                            elif "json" in item:
                                st.json(item["json"])
        else:
            # Fallback for regular messages or older format
            if message["content"]:
                st.write(message["content"])
            
            # Display tool calls and results for backward compatibility
            if message["role"] == "assistant":
                if "tools" in message:
                    for tool in message["tools"]:
                        st.info(f"🔧 **Tool Call:** {tool['name']}")
                        with st.expander("Tool Input", expanded=False):
                            st.json(tool["input"])
                
                if "results" in message:
                    for result in message["results"]:
                        if result["status"] == "success":
                            st.success("✅ **Tool Result:** Success")
                        else:
                            st.error(f"❌ **Tool Result:** {result['status']}")
                        
                        with st.expander("Tool Result", expanded=False):
                            for item in result.get("content", []):
                                if "text" in item:
                                    st.code(item["text"])
                                elif "json" in item:
                                    st.json(item["json"])

# File upload section - positioned above chat input
st.markdown("---")
uploaded_files = st.file_uploader(
    "Upload files for the agent to analyze",
    accept_multiple_files=True,
    key=f"file_uploader_{st.session_state.file_uploader_key}",
    help="Upload any files you want the agent to have access to"
)

# Chat input
if prompt := st.chat_input("Ask me anything..."):
    # Handle file uploads if present
    file_info = ""
    uploaded_file_paths = []
    
    if uploaded_files:
        # Create uploads directory if it doesn't exist
        uploads_dir = "uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        
        for uploaded_file in uploaded_files:
            # Save file to uploads directory
            file_path = os.path.join(uploads_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            uploaded_file_paths.append(file_path)
        
        # Create file notification for agent
        file_info = f"\n\nUploaded files: {', '.join(uploaded_file_paths)}"
        st.success(f"✅ Uploaded {len(uploaded_file_paths)} file(s) to uploads/ directory")
    
    # Combine prompt with file info
    full_prompt = prompt + file_info
    # Add user message to chat (display original prompt, but send full_prompt to agent)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message with file info if files were uploaded
    with st.chat_message("user"):
        st.write(prompt)
        if uploaded_file_paths:
            st.caption(f"📎 Files: {', '.join([os.path.basename(f) for f in uploaded_file_paths])}")
    
    # Reset current message tracking
    st.session_state.accumulated_text = ""
    st.session_state.current_message_tools = []
    st.session_state.current_message_results = []
    st.session_state.current_message_accumulated = ""
    st.session_state.all_agent_text = ""  # Reset for new agent call
    st.session_state.conversation_flow = []  # Reset conversation flow
    
    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = st.session_state.agent(full_prompt)  # Use full_prompt with file info
        
        # Display any remaining accumulated text as final thoughts
        if st.session_state.accumulated_text:
            st.write(st.session_state.accumulated_text)
        
        # Don't display the result again if it's the same as accumulated text
        # The final result is typically just the last accumulated text chunk
    
    # Add assistant response to chat history with chronological flow
    message_data = {
        "role": "assistant", 
        "content": st.session_state.all_agent_text if st.session_state.all_agent_text else str(result),
        "conversation_flow": st.session_state.conversation_flow.copy()  # Store the chronological flow
    }
    
    # Add tool calls and results if any
    if st.session_state.current_message_tools:
        message_data["tools"] = st.session_state.current_message_tools.copy()
    
    if st.session_state.current_message_results:
        message_data["results"] = st.session_state.current_message_results.copy()
    
    st.session_state.messages.append(message_data)
    
    # Clear the file uploader by incrementing the key
    if uploaded_files:
        st.session_state.file_uploader_key += 1
    
    st.rerun()

# Sidebar with configuration and help
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
    
    # File management
    st.markdown("---")
    st.header("📁 File Management")
    
    # Show uploaded files
    uploads_dir = "uploads"
    if os.path.exists(uploads_dir):
        files = os.listdir(uploads_dir)
        if files:
            st.write(f"**Files in uploads/ ({len(files)}):**")
            for file in files[:10]:  # Show first 10 files
                file_path = os.path.join(uploads_dir, file)
                file_size = os.path.getsize(file_path)
                st.text(f"📄 {file} ({file_size:,} bytes)")
            
            if len(files) > 10:
                st.caption(f"... and {len(files) - 10} more files")
            
            # Clear uploads button
            if st.button("🗑️ Clear Uploaded Files"):
                import shutil
                shutil.rmtree(uploads_dir)
                st.success("All uploaded files cleared!")
                st.rerun()
        else:
            st.info("No files uploaded yet")
    else:
        st.info("No files uploaded yet")
    
    # Chat statistics
    if st.session_state.messages:
        st.markdown("---")
        st.header("📊 Chat Stats")
        
        user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
        assistant_messages = len([m for m in st.session_state.messages if m["role"] == "assistant"])
        total_tools = sum(len(m.get("tools", [])) for m in st.session_state.messages)
        
        st.metric("User Messages", user_messages)
        st.metric("Assistant Messages", assistant_messages)
        st.metric("Tool Calls", total_tools)
    
    # Help section
    st.markdown("---")
    with st.expander("ℹ️ Help", expanded=False):
        st.markdown("""
        ### How to Use
        
        1. **Upload files** (optional) - Use the file uploader to give the agent access to files
        2. **Type your message** in the chat input at the bottom  
        3. **Watch tool calls** - The agent will show when it calls tools
        4. **See tool results** - Results are displayed in real-time
        5. **Review chat history** - All interactions are saved during your session
        
        ### File Handling
        
        - **Upload multiple files** - All file types supported
        - **Automatic storage** - Files saved to `uploads/` directory
        - **Agent awareness** - Agent is told about uploaded files
        - **File management** - View and clear uploaded files from sidebar
        
        ### Features
        
        - **Real-time tool execution** - See tools being called as they happen
        - **Tool input/output display** - Inspect what data is sent to and received from tools
        - **Persistent chat history** - Messages stay until you clear them
        - **Streaming responses** - See the agent's thoughts as they develop
        """)