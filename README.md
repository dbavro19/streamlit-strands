# Streamlit + Strands Integration Guide

A comprehensive guide to building interactive AI agent interfaces using Streamlit and AWS Strands, with real-time tool call visualization and proper chronological flow.

## Table of Contents
1. [Overview](#overview)
2. [Understanding Strands Callbacks](#understanding-strands-callbacks)
3. [Core Integration Architecture](#core-integration-architecture)
4. [Implementing Real-time Display](#implementing-real-time-display)
5. [Maintaining Chronological Order](#maintaining-chronological-order)
6. [Chat History Persistence](#chat-history-persistence)
7. [Complete Implementation](#complete-implementation)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

This guide demonstrates how to create a Streamlit application that integrates with AWS Strands to provide:
- **Real-time streaming** of agent thoughts and responses
- **Live tool call visualization** with expandable inputs/outputs
- **Chronological order preservation** of thoughts → tools → results
- **Persistent chat history** that maintains the complete conversation flow
- **File upload support** for agent processing

### Key Components
- **Streamlit**: Frontend interface and real-time display
- **AWS Strands**: AI agent framework with tool calling capabilities
- **Callback Handler**: Bridge between Strands events and Streamlit UI

## Understanding Strands Callbacks

Strands uses a sophisticated callback system that sends multiple types of events during agent execution:

### Callback Event Types

```python
# Streaming text data
{'data': 'text_chunk', 'delta': {...}, ...}

# Complete messages (structured)
{'message': {'role': 'assistant', 'content': [...]}}

# Tool use streaming (partial)
{'current_tool_use': {'name': 'calculator', 'input': '{"expr'}, ...}

# Event-based callbacks (metadata)
{'event': {'messageStart': {...}}}
{'event': {'contentBlockDelta': {...}}}
{'event': {'messageStop': {...}}}

# Lifecycle callbacks
{'init_event_loop': True}
{'start': True}
{'start_event_loop': True}
```

### Event Flow Pattern

The typical flow for an agent with tool calls:

1. **Lifecycle events**: `init_event_loop` → `start` → `start_event_loop`
2. **Streaming thoughts**: Multiple `data` callbacks with text chunks
3. **Complete message**: Assistant message with text + tool use
4. **Tool execution**: Tool result as user message
5. **More streaming**: Additional cycles for follow-up thoughts
6. **Final message**: Complete assistant response

## Core Integration Architecture

### Session State Management

```python
# Initialize session state for tracking
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'agent' not in st.session_state:
    # Agent state tracking
    st.session_state.accumulated_text = ""
    st.session_state.all_agent_text = ""
    st.session_state.conversation_flow = []
    st.session_state.current_message_tools = []
    st.session_state.current_message_results = []
```

### Callback Handler Design

The callback handler is the heart of the integration, processing different event types:

```python
def callback_handler(**kwargs):
    """Handle streaming responses and tool calls."""
    
    # Handle streaming text data
    if "data" in kwargs and kwargs["data"]:
        st.session_state.accumulated_text += kwargs["data"]
        st.session_state.all_agent_text += kwargs["data"]
        # Accumulate but don't display yet
    
    # Handle complete messages
    elif "message" in kwargs:
        message = kwargs["message"]
        
        # Process assistant messages
        if message.get("role") == "assistant":
            # Handle text and tool calls in order
            
        # Process tool results
        elif message.get("role") == "user":
            # Handle tool execution results
```

## Implementing Real-time Display

### Text Streaming Strategy

Instead of displaying text as it streams, we accumulate it and display complete thoughts:

```python
# In callback handler
if message.get("role") == "assistant" and "content" in message:
    for content in message["content"]:
        if "text" in content:
            text_content = content["text"]
            # Display immediately when we get complete text
            st.write(text_content)
            
            # Track in conversation flow
            st.session_state.conversation_flow.append({
                "type": "text",
                "content": text_content
            })
```

### Tool Call Visualization

Tool calls are displayed with expandable interfaces:

```python
elif "toolUse" in content:
    tool_use = content["toolUse"]
    
    # Real-time display
    st.info(f"🔧 **Tool Call:** {tool_use['name']}")
    with st.expander("Tool Input", expanded=False):
        st.json(tool_use["input"])
    
    # Track in conversation flow
    st.session_state.conversation_flow.append({
        "type": "tool_call",
        "tool": {
            "name": tool_use["name"],
            "input": tool_use["input"],
            "tool_use_id": tool_use["toolUseId"]
        }
    })
```

### Tool Result Display

Tool results are shown with status indicators and expandable content:

```python
if "toolResult" in content:
    result = content["toolResult"]
    
    # Status display
    if result.get("status") == "success":
        st.success("✅ **Tool Result:** Success")
    else:
        st.error(f"❌ **Tool Result:** {result.get('status', 'Failed')}")
    
    # Expandable result content
    result_content = result.get("content", [])
    if result_content:
        with st.expander("Tool Result", expanded=True):
            for item in result_content:
                if "text" in item:
                    st.code(item["text"])
                elif "json" in item:
                    st.json(item["json"])
```

## Maintaining Chronological Order

### The Challenge

Strands sends events in this pattern:
1. All streaming text for a cycle
2. Complete message with text + tool use
3. Tool result
4. Repeat for next cycle

But we want to display: **Thoughts → Tool → Result → Thoughts → Tool → Result**

### The Solution: Conversation Flow Tracking

We maintain a chronological array that records the exact order of events:

```python
# In callback handler - track each event in order
st.session_state.conversation_flow.append({
    "type": "text",
    "content": "I'll help you calculate..."
})

st.session_state.conversation_flow.append({
    "type": "tool_call", 
    "tool": {...}
})

st.session_state.conversation_flow.append({
    "type": "tool_result",
    "result": {...}
})
```

### Chat History Replay

When displaying chat history, we replay the exact chronological sequence:

```python
# Display chat messages in chronological order
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
        # Display result with appropriate styling
```

## Chat History Persistence

### Message Data Structure

Each chat message stores both the complete text and the chronological flow:

```python
message_data = {
    "role": "assistant",
    "content": st.session_state.all_agent_text,  # Complete text
    "conversation_flow": st.session_state.conversation_flow.copy()  # Chronological events
}
```

### Benefits of This Approach

1. **Complete Context**: `all_agent_text` preserves all intermediate thoughts
2. **Chronological Order**: `conversation_flow` maintains exact sequence
3. **Rich Display**: Tool calls and results are preserved with full formatting
4. **Backward Compatibility**: Falls back to simple text display if needed

## Complete Implementation

### Agent Initialization

```python
if 'agent' not in st.session_state:
    # Initialize Bedrock model
    bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        temperature=0.1,
        top_p=0.9,
        max_tokens=4000,
        region_name="us-east-1"
    )
    
    # Initialize tracking variables
    st.session_state.accumulated_text = ""
    st.session_state.all_agent_text = ""
    st.session_state.conversation_flow = []
    st.session_state.current_message_tools = []
    st.session_state.current_message_results = []
    
    # Create agent with callback handler
    st.session_state.agent = Agent(
        tools=[your_tools_here],
        callback_handler=callback_handler,
        model=bedrock_model,
        system_prompt="Your agent instructions..."
    )
```

### Main Chat Interface

```python
# Chat input handling
if prompt := st.chat_input("Ask me anything..."):
    # Reset tracking for new conversation
    st.session_state.accumulated_text = ""
    st.session_state.all_agent_text = ""
    st.session_state.conversation_flow = []
    st.session_state.current_message_tools = []
    st.session_state.current_message_results = []
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Get agent response with real-time display
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = st.session_state.agent(prompt)
        
        # Display any remaining accumulated text
        if st.session_state.accumulated_text:
            st.write(st.session_state.accumulated_text)
    
    # Store complete conversation in chat history
    message_data = {
        "role": "assistant",
        "content": st.session_state.all_agent_text,
        "conversation_flow": st.session_state.conversation_flow.copy()
    }
    st.session_state.messages.append(message_data)
    
    st.rerun()
```

### File Upload Integration

```python
# File upload handling
uploaded_files = st.file_uploader(
    "Upload files for the agent to analyze",
    accept_multiple_files=True
)

if uploaded_files:
    # Save files locally
    uploads_dir = "uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    
    file_paths = []
    for uploaded_file in uploaded_files:
        file_path = os.path.join(uploads_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        file_paths.append(file_path)
    
    # Include file info in agent prompt
    file_info = f"\\n\\nUploaded files: {', '.join(file_paths)}"
    full_prompt = prompt + file_info
```

## Best Practices

### 1. Callback Handler Design

- **Handle all event types**: Even if you ignore some, handle them gracefully
- **Accumulate before displaying**: Don't show partial text chunks
- **Use session state carefully**: Reset tracking variables for each new conversation
- **Track chronological order**: Maintain the exact sequence of events

### 2. Performance Considerations

- **Limit tool call details**: Use expandable sections for large inputs/outputs
- **Manage session state size**: Clear old data when appropriate
- **Handle long conversations**: Consider pagination for very long chat histories

### 3. Error Handling

```python
# Handle tool execution errors gracefully
if result.get("status") == "success":
    st.success("✅ **Tool Result:** Success")
else:
    st.error(f"❌ **Tool Result:** {result.get('status', 'Failed')}")
    if "content" in result:
        with st.expander("Error Details", expanded=True):
            st.code(str(result["content"]))
```

### 4. UI/UX Best Practices

- **Use consistent styling**: Tool calls, results, and text should have clear visual hierarchy
- **Provide expandable details**: Keep the main flow clean but allow drilling down
- **Show loading states**: Use spinners during agent processing
- **Clear visual separation**: Distinguish between thoughts, tools, and results

## Troubleshooting

### Common Issues

**1. Order Problems**
- **Symptom**: Tool calls appear before or after related thoughts
- **Solution**: Ensure you're using the conversation flow tracking approach
- **Debug**: Add console logging to see callback order

**2. Missing Intermediate Thoughts**
- **Symptom**: Only final response appears in chat history
- **Solution**: Accumulate text across all message cycles using `all_agent_text`
- **Debug**: Log what's being stored in `accumulated_text` vs `all_agent_text`

**3. Duplicate Displays**
- **Symptom**: Same content appears multiple times
- **Solution**: Don't display in both callbacks and chat history replay
- **Fix**: Display in callbacks for real-time, use flow for history

**4. Session State Issues**
- **Symptom**: Data persists across conversations or gets cleared unexpectedly
- **Solution**: Reset tracking variables at the right times
- **Pattern**: Reset at start of new conversation, preserve during agent execution

### Debug Techniques

**1. Callback Logging**
```python
def callback_handler(**kwargs):
    # Add debug logging
    print(f"Callback: {list(kwargs.keys())}")
    if "data" in kwargs:
        print(f"Data: {kwargs['data'][:50]}...")
    # ... rest of handler
```

**2. Session State Inspection**
```python
# Add to sidebar for debugging
with st.sidebar:
    if st.checkbox("Debug Mode"):
        st.write("Accumulated Text:", len(st.session_state.accumulated_text))
        st.write("All Agent Text:", len(st.session_state.all_agent_text))
        st.write("Flow Items:", len(st.session_state.conversation_flow))
```

## Conclusion

This integration pattern provides a robust foundation for building Streamlit applications with Strands agents. The key insights are:

1. **Understand the callback patterns** - Strands sends events in a specific sequence
2. **Accumulate before displaying** - Don't show partial text chunks
3. **Track chronological order** - Maintain the natural conversation flow
4. **Separate real-time and history** - Use callbacks for live updates, flow for replay
5. **Handle all event types** - Even if you ignore them, handle gracefully

By following these patterns, you can create rich, interactive AI agent interfaces that feel natural and provide excellent user experience.
