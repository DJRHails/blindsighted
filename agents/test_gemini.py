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

class LocalPhotoManager:
    """
    Simulates the Swift PhotoFileManager.
    Reads from ~/Documents/BlindsightedPhotos/
    """
    def __init__(self):
        self.directory_path = os.path.expanduser("~/Documents/BlindsightedPhotos")
        print(f"[LocalPhotoManager] Storage Path: {self.directory_path}")
    
    def list_photos(self):
        """Returns a list of filenames in the directory."""
        if not os.path.exists(self.directory_path):
            return []
        
        photos = [f for f in os.listdir(self.directory_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        return photos

    def load_image(self, filename):
        """Loads an image and returns a data URL for Gemini."""
        path = os.path.join(self.directory_path, filename)
        if not os.path.exists(path):
            return None
        
        with open(path, "rb") as f:
            image_bytes = f.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            mime_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
            return f"data:{mime_type};base64,{image_b64}"

class GeminiAgent:
    def __init__(self, role_name, system_prompt, api_key):
        self.role_name = role_name
        self.model = google.LLM(
            model="gemini-2.0-flash-exp",
            api_key=api_key,
        )
        self.system_prompt = system_prompt

    async def generate(self, user_content, image_data_url=None, reference_image_url=None):
        chat_ctx = llm.ChatContext()
        chat_ctx.add_message(role="system", content=self.system_prompt)
        
        # User message content list
        msg_content = [user_content]
        
        # Live View (Primary Image)
        if image_data_url:
            msg_content.append(llm.ImageContent(image=image_data_url))
        
        # Reference Image (Secondary Image from DB)
        if reference_image_url:
            print(f"[{self.role_name}] Attaching Reference Image from History.")
            msg_content.append(llm.ImageContent(image=reference_image_url))
            
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

    # Image Setup (Live View Simulation)
    image_path = "/Users/shashankdurgad/Documents/GitHub/ef-accessibility-hack/Screenshot 2026-01-17 at 1.46.20 PM.png"
    if not os.path.exists(image_path):
        image_path = "Screenshot 2026-01-17 at 1.46.20 PM.png"
    
    if not os.path.exists(image_path):
        print(f"Error: Image {image_path} not found.")
        return

    with open(image_path, "rb") as f:
        image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = "image/png" if image_path.endswith(".png") else "image/jpeg"
        live_image_url = f"data:{mime_type};base64,{image_b64}"

    # --- AGENT 1: ITEM LISTER ---
    lister_prompt = """You are an AI assistant for the visually impaired.
    Your job is to scan the image and provide a numbered list of ALL distinct items visible.
    - Be concise.
    - format: 1. [Item Name] - [Brief Location]
    """
    
    lister_agent = GeminiAgent("ITEM_LISTER", lister_prompt, api_key)
    
    print("\n--- Step 1: Listing Items ---")
    items_list_response = await lister_agent.generate("List all items you see.", live_image_url)
    print(items_list_response)

    # --- SIMULATE USER SELECTION ---
    target_item = "box of Vahdam Teas"
    print(f"\n[Simulated User Selection]: I want to find the '{target_item}'.")

    # --- LOCAL PHOTO MANAGER LOOKUP ---
    photo_manager = LocalPhotoManager()
    stored_photos = photo_manager.list_photos()
    
    reference_image_url = None
    found_photo_name = None

    # Simple keyword match to simulate database validation
    # looking for a file that might match "vahdam" or "tea"
    keywords = ["vahdam", "tea", "box"]
    for photos_file in stored_photos:
        if any(k in photos_file.lower() for k in keywords):
            print(f"[Database] Found stored photo for item: {photos_file}")
            reference_image_url = photo_manager.load_image(photos_file)
            found_photo_name = photos_file
            break
    
    db_context_msg = f"Target Item: {target_item}."
    if found_photo_name:
        db_context_msg += f" I have attached a REFERENCE PHOTO called '{found_photo_name}' from my history which shows exactly what I am looking for."
    else:
        db_context_msg += " No reference photo found in history."

    # --- AGENT 2: RETRIEVER / GUIDANCE ---
    retriever_prompt = """You are a navigation assistant for the visually impaired.
    You will receive:
    1. A target item request.
    2. THE LIVE VIEW IMAGE (First Image).
    3. OPTIONAL: A REFERENCE PHOTO (Second Image) from the user's history.

    Your Goal: Guide the user's hand to the item in the LIVE VIEW.
    - Compare the REFERENCE PHOTO (if provided) with objects in the LIVE VIEW to confirm identity.
    - If you see the user's hand, guide relative to it (clock face, distance).
    - If the item is not in the live view, say so.
    """

    retriever_agent = GeminiAgent("RETRIEVER", retriever_prompt, api_key)

    print("\n--- Step 2: Retrieving/Guiding ---")
    guidance_response = await retriever_agent.generate(db_context_msg, live_image_url, reference_image_url)
    print(guidance_response)

if __name__ == "__main__":
    asyncio.run(test_gemini_agents())
