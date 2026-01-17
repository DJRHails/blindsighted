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

class GeminiAgent:
    def __init__(self, role_name, system_prompt, api_key):
        self.role_name = role_name
        self.model = google.LLM(
            model="gemini-2.0-flash-exp",
            api_key=api_key,
        )
        self.system_prompt = system_prompt

    async def generate(self, user_content, image_data_url=None):
        chat_ctx = llm.ChatContext()
        chat_ctx.add_message(role="system", content=self.system_prompt)
        
        msg_content = [user_content]
        if image_data_url:
            msg_content.append(llm.ImageContent(image=image_data_url))
            
        chat_ctx.add_message(role="user", content=msg_content)

        print(f"[{self.role_name}] Processing request...")
        
        try:
            stream = self.model.chat(chat_ctx=chat_ctx)
            full_response = ""
            async for chunk in stream:
                if chunk.delta and chunk.delta.content:
                    full_response += chunk.delta.content
            return full_response
        except Exception as e:
            return f"Error: {e}"

async def test_gemini_agents():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found.")
        return

    # Image Setup
    image_path = "/Users/shashankdurgad/Documents/GitHub/ef-accessibility-hack/Screenshot 2026-01-17 at 1.46.20 PM.png"
    if not os.path.exists(image_path):
        # Fallback to local file if available
        image_path = "Screenshot 2026-01-17 at 1.46.20 PM.png"
    
    if not os.path.exists(image_path):
        print(f"Error: Image {image_path} not found.")
        return

    with open(image_path, "rb") as f:
        image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = "image/png" if image_path.endswith(".png") else "image/jpeg"
        image_data_url = f"data:{mime_type};base64,{image_b64}"

    # --- AGENT 1: ITEM LISTER ---
    lister_prompt = """You are an AI assistant for the visually impaired.
    Your job is to scan the image and provide a numbered list of ALL distinct items visible.
    - Be concise.
    - format: 1. [Item Name] - [Brief Location]
    - Do not give navigation instructions yet.
    """
    
    lister_agent = GeminiAgent("ITEM_LISTER", lister_prompt, api_key)
    
    print("\n--- Step 1: Listing Items ---")
    items_list_response = await lister_agent.generate("List all items you see.", image_data_url)
    print(items_list_response)

    # --- SIMULATE USER SELECTION ---
    # In a real app, the user would select from the list. 
    # Here typically we'd parse the list, but for the demo we'll assume they want "Tea" if present, or just the first item.
    target_item = "box of Vahdam Teas"
    print(f"\n[Simulated User Selection]: I want to find the '{target_item}'.")

    # --- MOCK DATABASE LOOKUP ---
    # Simulating fetching "stored photos" or metadata about this item
    mock_db_context = f"""
    [DATABASE INFO]
    Item: {target_item}
    Last Known Location: Kitchen Counter, near the coffee maker.
    Appearance: Green box with floral patterns.
    """

    # --- AGENT 2: RETRIEVER / GUIDANCE ---
    retriever_prompt = """You are a navigation assistant for the visually impaired.
    You will receive:
    1. A target item the user wants.
    2. Optional database info about the item (appearance, last location).
    3. The current live view (image).

    Your Goal: Guide the user's hand to the item.
    - Use "Clock Face" or "Centimeters/Inches" directions.
    - Reference the database info if it helps confirm identity (e.g. "I see the green box you stored previously").
    - If the hand is visible, guide relative to the hand.
    """

    retriever_agent = GeminiAgent("RETRIEVER", retriever_prompt, api_key)

    print("\n--- Step 2: Retrieving/Guiding ---")
    guidance_request = f"Help me find the {target_item}. Here is what I know about it: {mock_db_context}"
    guidance_response = await retriever_agent.generate(guidance_request, image_data_url)
    print(guidance_response)

if __name__ == "__main__":
    asyncio.run(test_gemini_agents())
