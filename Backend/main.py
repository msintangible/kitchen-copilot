import asyncio
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tool import search_recipes_tool, timer_tool, handle_tool_call

# Load environment variables
load_dotenv()

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def chat_with_kitchen_copilot():
    """
    Main chat interface for Kitchen Copilot
    Supports both recipe search and timer functionality
    """

    print("🍳 Welcome to Kitchen Copilot!")
    print("I can help you find recipes and manage cooking timers.\n")

    # Configure the model with tools
    model = "gemini-2.0-flash"
    tools = [search_recipes_tool, timer_tool]

    # Initialize conversation history
    chat_history = []

    while True:
        try:
            # Get user input
            user_input = input("👤 You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye! Happy cooking!")
                break

            if not user_input:
                continue

            # Add user message to history
            chat_history.append({"role": "user", "parts": [{"text": user_input}]})

            # Generate response with tool calling
            response = client.models.generate_content(
                model=model,
                contents=user_input,
                config=types.GenerateContentConfig(
                    tools=tools,
                    tool_config=types.ToolConfig(
                        function_calling_config=types.FunctionCallingConfig(
                            mode="AUTO"
                        )
                    )
                )
            )

            # Handle tool calls
            tool_calls = []
            if hasattr(response, 'function_calls') and response.function_calls:
                tool_calls = response.function_calls

            # Process tool calls
            tool_results = []
            for tool_call in tool_calls:
                function_name = tool_call.name
                function_args = tool_call.args

                print(f"🔧 Calling tool: {function_name}")

                # Call the appropriate handler
                result = await handle_tool_call(function_name, function_args)
                tool_results.append(result)

                # Add tool result to chat history
                chat_history.append({
                    "role": "model",
                    "parts": [{
                        "function_call": {
                            "name": function_name,
                            "args": function_args
                        }
                    }]
                })
                chat_history.append({
                    "role": "function",
                    "parts": [{
                        "text": str(result)
                    }]
                })

            # Generate final response based on tool results
            if tool_results:
                # Create a summary of tool results for the model
                tool_summary = "\n".join([
                    f"Tool result: {result.get('message', str(result))}"
                    for result in tool_results
                ])

                final_prompt = f"Based on these tool results, provide a helpful response to the user:\n\n{tool_summary}"

                final_response = client.models.generate_content(
                    model=model,
                    contents=final_prompt
                )

                ai_response = final_response.text
            else:
                # No tools were called, use the direct response
                ai_response = response.text if hasattr(response, 'text') else "I understand. How can I help you with cooking?"

            # Display AI response
            print(f"🤖 Kitchen Copilot: {ai_response}\n")

            # Add to chat history
            chat_history.append({"role": "model", "parts": [{"text": ai_response}]})

        except KeyboardInterrupt:
            print("\n👋 Goodbye! Happy cooking!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Please try again.\n")

if __name__ == "__main__":
    asyncio.run(chat_with_kitchen_copilot())
