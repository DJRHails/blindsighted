import os
import asyncio
import base64
from livekit.agents import llm
from livekit.plugins import google
from dotenv import load_dotenv

# Load env - look for .env in current or agents/ directory
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("agents/.env"):
    load_dotenv("agents/.env")
else:
    load_dotenv()

async def test_gemini():
    # Use direct Google API key
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in environment.")
        print("Please ensure agents/.env contains GOOGLE_API_KEY or export it.")
        return

    # Initialize Gemini via Google plugin
    # Using gemini-2.0-flash-exp for latest flash capabilities
    model = google.LLM(
        model="gemini-2.0-flash-exp",
        api_key=api_key,
    )

    image_path = "/Users/shashankdurgad/Documents/GitHub/ef-accessibility-hack/Screenshot 2026-01-17 at 1.46.20 PM.png"
    
    if not os.path.exists(image_path):
        # Fallback if the script is run from inside agents/
        image_path = "../Screenshot 2026-01-17 at 1.46.20 PM.png"
        if not os.path.exists(image_path):
            print(f"Error: Image not found at {image_path}")
            return

    with open(image_path, "rb") as f:
        image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        # Determine mime type from extension
        mime_type = "image/png" if image_path.endswith(".png") else "image/jpeg"
        image_data_url = f"data:{mime_type};base64,{image_b64}"

    # System prompt for guidance
    system_instructions = """You are a helpful AI assistant for visually impaired users. 
You have access to their camera feed. Your goal is to guide them to collect the item they are looking for.

Instructions:
1. Provide EXACT physical guidance (e.g., 'Raise your hand', 'Move your hand 10cm left', 'The item is directly in front of you').
2. If the item is only partially visible or off-center, give 'step-back' or 'pivot' instructions to reframe. If the item is still not visible, say that the required item is not visible in the current frame.
3. If you see their hand, use it as a reference point (e.g., 'Your hand is just to the right of the tea').
4. If the item is identified, validate it clearly (e.g., 'I see the Vahdam Assorted Teas box directly in front of you').
5. Be concise and actionable.
"""

    chat_ctx = llm.ChatContext()
    
    user_content = "I'm looking for the tea. Can you see it? Guide me to it."
    chat_ctx.add_message(role="system", content=system_instructions)
    chat_ctx.add_message(
        role="user",
        content=[
            user_content,
            llm.ImageContent(image=image_data_url)
        ]
    )

    print(f"Testing Gemini with image: {os.path.basename(image_path)}")
    print(f"User Request: {user_content}")
    print("-" * 30)

    try:
        # Note: model.chat() returns an LLMStream, we need to iterate to get the final message
        stream = model.chat(chat_ctx=chat_ctx)
        content = ""
        async for chunk in stream:
            if chunk.delta and chunk.delta.content:
                content += chunk.delta.content
        
        print("\nGemini Response:")
        print(content)
    except Exception as e:
        print(f"Error calling Gemini: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini())
