# import asyncio
# from typing import Annotated
# import os
# from dotenv import load_dotenv
# from fastmcp.server import FastMCP # type: ignore
# from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair # type: ignore
# from mcp import ErrorData, McpError
# from mcp.server.auth.provider import AccessToken
# from mcp.types import TextContent, ImageContent, INVALID_PARAMS, INTERNAL_ERROR
# from pydantic import BaseModel, Field, AnyUrl
# import tempfile
# from datetime import datetime, timedelta
# import re
# from enum import Enum

# # --- Load environment variables ---
# load_dotenv()

# TOKEN = os.environ.get("AUTH_TOKEN")
# MY_NUMBER = os.environ.get("MY_NUMBER")

# assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
# assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"

# # --- Auth Provider ---
# class SimpleBearerAuthProvider(BearerAuthProvider):
#     def __init__(self, token: str):
#         k = RSAKeyPair.generate()
#         super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
#         self.token = token

#     async def load_access_token(self, token: str) -> AccessToken | None:
#         if token == self.token:
#             return AccessToken(
#                 token=token,
#                 client_id="puch-client",
#                 scopes=["*"],
#                 expires_at=None,
#             )
#         return None

# # --- Rich Tool Description model ---
# class RichToolDescription(BaseModel):
#     description: str
#     use_when: str
#     side_effects: str | None = None

# # --- SONG RECOMMENDATION CLASSES ---
# class Mood(Enum):
#     HAPPY = "happy"
#     SAD = "sad"
#     NEUTRAL = "neutral"
#     ANGRY = "angry"
#     EXCITED = "excited"

# class SongRecommendationEngine:
#     """Engine for analyzing mood and recommending songs"""
    
#     # Hardcoded curated playlists for each mood
#     PLAYLISTS = {
#         "happy": [
#             {"title": "Happy", "artist": "Pharrell Williams", "spotify_url": "https://open.spotify.com/track/60nZcImufyMA1MKQY3dcCH"},
#             {"title": "Can't Stop the Feeling!", "artist": "Justin Timberlake", "spotify_url": "https://open.spotify.com/track/20I6sIOMTCkB6w7ryavxtO"},
#             {"title": "Good as Hell", "artist": "Lizzo", "spotify_url": "https://open.spotify.com/track/1PckUlxKqWQs3RlWXVBLw3"},
#             {"title": "Uptown Funk", "artist": "Mark Ronson ft. Bruno Mars", "spotify_url": "https://open.spotify.com/track/32OlwWuMpZ6b0aN2RZOeMS"},
#             {"title": "Walking on Sunshine", "artist": "Katrina and the Waves", "spotify_url": "https://open.spotify.com/track/05wIrZSwuaVWhcv5FfqeH0"}
#         ],
#         "sad": [
#             {"title": "Someone Like You", "artist": "Adele", "spotify_url": "https://open.spotify.com/track/4bHsxqR3GMrXTxEPLuK5ue"},
#             {"title": "Mad World", "artist": "Gary Jules", "spotify_url": "https://open.spotify.com/track/3JOVTQ5h8HGFnDdp4VT3MP"},
#             {"title": "The Sound of Silence", "artist": "Simon & Garfunkel", "spotify_url": "https://open.spotify.com/track/7GElp5u1l2Xfgd5z8L8PaL"},
#             {"title": "Hurt", "artist": "Johnny Cash", "spotify_url": "https://open.spotify.com/track/2o4H9vWfjkJWKlvr5wlZRX"},
#             {"title": "Black", "artist": "Pearl Jam", "spotify_url": "https://open.spotify.com/track/4XblTJYZEn4y3SXWNx9JRt"}
#         ],
#         "angry": [
#             {"title": "Break Stuff", "artist": "Limp Bizkit", "spotify_url": "https://open.spotify.com/track/5bIgwJD4kWQ4LVgUhvnEQs"},
#             {"title": "Bodies", "artist": "Drowning Pool", "spotify_url": "https://open.spotify.com/track/4KNMTEhkEKmjZhb2Dn6VHh"},
#             {"title": "Killing in the Name", "artist": "Rage Against the Machine", "spotify_url": "https://open.spotify.com/track/59WN2psjkt1tyaxjspN8fp"},
#             {"title": "Chop Suey!", "artist": "System of a Down", "spotify_url": "https://open.spotify.com/track/2DlHlPMa4M17kufBvI2lEN"},
#             {"title": "In the End", "artist": "Linkin Park", "spotify_url": "https://open.spotify.com/track/60a0Rd6pjrkxjPbaKzXjfq"}
#         ],
#         "excited": [
#             {"title": "Thunder", "artist": "Imagine Dragons", "spotify_url": "https://open.spotify.com/track/0tBbt8CrmxbjRP0pueQkyU"},
#             {"title": "Pump It", "artist": "The Black Eyed Peas", "spotify_url": "https://open.spotify.com/track/7Jh1bpe76CNTCgdgAdBw4Z"},
#             {"title": "Eye of the Tiger", "artist": "Survivor", "spotify_url": "https://open.spotify.com/track/2KH16WveTQWT6KOG9Rg6e2"},
#             {"title": "We Will Rock You", "artist": "Queen", "spotify_url": "https://open.spotify.com/track/4pbJqGIASGPr0ZpGpnWkDn"},
#             {"title": "Don't Stop Believin'", "artist": "Journey", "spotify_url": "https://open.spotify.com/track/4bHsxqR3GMrXTxEPLuK5ue"}
#         ],
#         "neutral": [
#             {"title": "Shape of You", "artist": "Ed Sheeran", "spotify_url": "https://open.spotify.com/track/7qiZfU4dY1lWllzX7mPBI3"},
#             {"title": "Blinding Lights", "artist": "The Weeknd", "spotify_url": "https://open.spotify.com/track/0VjIjW4GlULA0mG8km5iU8"},
#             {"title": "Watermelon Sugar", "artist": "Harry Styles", "spotify_url": "https://open.spotify.com/track/6UelLqGlWMcVH1E5c4H7lY"},
#             {"title": "Levitating", "artist": "Dua Lipa", "spotify_url": "https://open.spotify.com/track/463CkQjx2Zk1yXoBuierM9"},
#             {"title": "Stay", "artist": "The Kid LAROI & Justin Bieber", "spotify_url": "https://open.spotify.com/track/5HCyWlXZPP0y6Gqq8TgA20"}
#         ]
#     }
    
#     # Keywords for mood detection
#     MOOD_KEYWORDS = {
#         "happy": ["happy", "joy", "excited", "great", "amazing", "wonderful", "fantastic", "love", "good", "smile", "laugh", "cheerful"],
#         "sad": ["sad", "depressed", "down", "upset", "hurt", "cry", "lonely", "heartbreak", "miss", "lost", "blue", "melancholy"],
#         "angry": ["angry", "mad", "furious", "hate", "annoyed", "frustrated", "rage", "pissed", "irritated", "livid"],
#         "excited": ["excited", "pumped", "hyped", "energy", "party", "celebration", "workout", "motivated", "adrenaline", "intense"],
#         "neutral": ["okay", "fine", "normal", "regular", "whatever", "meh", "calm", "peaceful", "relaxed"]
#     }
    
#     @classmethod
#     def analyze_mood(cls, text: str) -> str:
#         """Analyze text and return the detected mood"""
#         text_lower = text.lower()
#         mood_scores = {mood: 0 for mood in cls.MOOD_KEYWORDS.keys()}
        
#         # Count keyword matches for each mood
#         for mood, keywords in cls.MOOD_KEYWORDS.items():
#             for keyword in keywords:
#                 if keyword in text_lower:
#                     mood_scores[mood] += 1
        
#         # Return the mood with highest score, default to neutral
#         detected_mood = max(mood_scores, key=mood_scores.get)
#         if mood_scores[detected_mood] == 0:
#             detected_mood = "neutral"
            
#         return detected_mood
    
#     @classmethod
#     def get_recommendations(cls, mood: str, count: int = 5) -> list:
#         """Get song recommendations for a specific mood"""
#         return cls.PLAYLISTS.get(mood, cls.PLAYLISTS["neutral"])[:count]

# # --- PDF Processing Class ---
# class PDFProcessor:
#     @staticmethod
#     async def process_pdf(pdf_data: str) -> str:
#         """Process PDF data and return extracted text"""
#         import base64
#         from PyPDF2 import PdfReader
#         from PyPDF2.errors import PdfReadError
#         import logging
#         from io import BytesIO
        
#         try:
#             # Decode base64 data
#             try:
#                 pdf_bytes = base64.b64decode(pdf_data)
#             except Exception as e:
#                 return f"Error: Failed to decode PDF data - {str(e)}"
            
#             # Create BytesIO object
#             pdf_stream = BytesIO(pdf_bytes)
            
#             # Extract text from PDF
#             text = ""
#             try:
#                 pdf_reader = PdfReader(pdf_stream)
                
#                 if len(pdf_reader.pages) == 0:
#                     return "Error: PDF appears to be empty"
                
#                 # Extract text from all pages
#                 for page_num, page in enumerate(pdf_reader.pages):
#                     try:
#                         page_text = page.extract_text()
#                         if page_text:
#                             text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
#                     except Exception as page_error:
#                         text += f"\n--- Page {page_num + 1} ---\n[Error extracting page: {str(page_error)}]\n"
#                         continue
                        
#             except Exception as e:
#                 return f"Error: Failed to read PDF - {str(e)}"
            
#             if not text.strip():
#                 return "Error: No text could be extracted from the PDF. The PDF might be image-based or password protected."
            
#             return text.strip()
            
#         except Exception as e:
#             logging.error(f"Unexpected error in process_pdf: {str(e)}")
#             return f"Error: Failed to process PDF - {str(e)}"
    

# # --- MCP Server Setup ---
# mcp = FastMCP(
#     "PDF Chat & Schedule Generator MCP Server",
#     auth=SimpleBearerAuthProvider(TOKEN),
# )

# # --- Tool: validate (required by Puch) ---
# @mcp.tool
# async def validate() -> str:
#     return MY_NUMBER

# # --- Tool: extract_pdf_text ---
# ExtractPDFTextDescription = RichToolDescription(
#     description="Extract text content from PDF files for analysis and chat",
#     use_when="User uploads a PDF file and wants to extract text content for further processing or chat",
#     side_effects="Returns extracted text from all pages of the PDF"
# )

# @mcp.tool(description=ExtractPDFTextDescription.model_dump_json())
# async def extract_pdf_text(
#     puch_pdf_data: Annotated[str, Field(description="The file ID of the uploaded PDF provided by the platform")] = None,
# ) -> str:
#     """
#     Extract text from a PDF document. This text can then be used by Puch AI's LLM for chat.
#     """
#     if not puch_pdf_data:
#         return "Error: No PDF file ID was provided. Please upload a PDF to extract its text."

#     try:
#         file_id = puch_pdf_data
#         file_object = await mcp.get_file_by_id(file_id)

#         if not file_object or not hasattr(file_object, 'data'):
#             return "Error: Could not retrieve the file from the platform using the provided ID."

#         pdf_base64_data = file_object.data

#         pdf_text = await PDFProcessor.process_pdf(pdf_base64_data)
#         if pdf_text.startswith("Error:"):
#             return pdf_text

#         word_count = len(pdf_text.split())
#         char_count = len(pdf_text)
#         result = [
#             "📄 **PDF Text Extraction Complete**",
#             "",
#             f"📊 **Statistics:**",
#             f"• Word count: {word_count:,}",
#             f"• Character count: {char_count:,}",
#             "",
#             "📝 **Extracted Text:**",
#             "=" * 50,
#             pdf_text,
#             "=" * 50,
#             "",
#             "✅ **Ready for Chat:** The text has been extracted successfully. You can now ask questions about this content!"
#         ]
#         return "\n".join(result)
#     except Exception as e:
#         raise McpError(ErrorData(
#             code=INTERNAL_ERROR,
#             message=f"Failed to extract PDF text: {str(e)}"
#         ))
# # --- Tool: generate_schedule ---
# ScheduleGeneratorDescription = RichToolDescription(
#     description="Generate a daily or weekly schedule based on tasks and priorities",
#     use_when="User needs help organizing their time with a structured schedule",
#     side_effects="Creates a time-blocked schedule"
# )

# class ScheduleItem(BaseModel):
#     task: str
#     duration_minutes: int
#     priority: int = Field(ge=1, le=3, description="1=high, 2=medium, 3=low")

# @mcp.tool(description=ScheduleGeneratorDescription.model_dump_json())
# async def generate_schedule(
#     tasks: Annotated[list[ScheduleItem], Field(description="List of tasks to schedule")],
#     start_time: Annotated[str, Field(description="Schedule start time (HH:MM)")] = "08:00",
#     end_time: Annotated[str, Field(description="Schedule end time (HH:MM)")] = "20:00",
#     date: Annotated[str | None, Field(description="Date for schedule (YYYY-MM-DD)")] = None,
# ) -> str:
#     """
#     Generate a time-blocked schedule based on provided tasks and time constraints.
#     """
#     try:
#         # Parse time inputs
#         start_h, start_m = map(int, start_time.split(':'))
#         end_h, end_m = map(int, end_time.split(':'))
        
#         # Calculate total available minutes
#         start_dt = datetime.strptime(start_time, "%H:%M")
#         end_dt = datetime.strptime(end_time, "%H:%M")
#         if end_dt <= start_dt:
#             end_dt += timedelta(days=1)  # Handle overnight schedules
#         total_minutes = int((end_dt - start_dt).total_seconds() / 60)
        
#         # Sort tasks by priority then duration
#         sorted_tasks = sorted(tasks, key=lambda x: (x.priority, x.duration_minutes))
        
#         # Schedule tasks
#         current_time = start_dt
#         schedule = []
#         remaining_minutes = total_minutes
        
#         for task in sorted_tasks:
#             if task.duration_minutes <= remaining_minutes:
#                 end_time = current_time + timedelta(minutes=task.duration_minutes)
#                 schedule.append({
#                     'task': task.task,
#                     'start': current_time.strftime("%H:%M"),
#                     'end': end_time.strftime("%H:%M"),
#                     'duration': task.duration_minutes,
#                     'priority': task.priority
#                 })
#                 current_time = end_time
#                 remaining_minutes -= task.duration_minutes
#             else:
#                 break  # Skip tasks that don't fit
        
#         # Format the schedule
#         date_str = f" for {date}" if date else ""
#         result = [f"📅 Generated Schedule{date_str} ({start_time} - {end_time}):\n"]
        
#         for item in schedule:
#             priority_emoji = "❗" if item['priority'] == 1 else "🔹" if item['priority'] == 2 else "▪️"
#             result.append(
#                 f"{priority_emoji} {item['start']}-{item['end']} ({item['duration']}min): {item['task']}"
#             )
        
#         if remaining_minutes > 0:
#             result.append(f"\n⏳ Remaining unscheduled time: {remaining_minutes} minutes")
        
#         return "\n".join(result)
    
#     except Exception as e:
#         raise McpError(ErrorData(
#             code=INVALID_PARAMS,
#             message=f"Invalid schedule parameters: {str(e)}"
#         ))

# # --- NEW TOOL: Song Recommendations ---
# SongRecommendationDescription = RichToolDescription(
#     description="Analyze user's mood from text and recommend songs from curated Spotify playlists",
#     use_when="User expresses emotions, asks for music recommendations, or mentions their current mood/feelings",
#     side_effects="Returns personalized song recommendations with Spotify links based on detected or specified mood"
# )

# @mcp.tool(description=SongRecommendationDescription.model_dump_json())
# async def recommend_songs(
#     user_text: Annotated[str, Field(description="Text expressing the user's current mood, feelings, or music request")],
#     mood_override: Annotated[str | None, Field(description="Manually specify mood (happy/sad/angry/excited/neutral)")] = None,
#     count: Annotated[int, Field(description="Number of songs to recommend (1-5)", ge=1, le=5)] = 5,
# ) -> str:
#     """
#     Analyze user's mood from their text and recommend appropriate songs from curated playlists.
#     Supports automatic mood detection or manual mood specification.
#     """
#     try:
#         # Use manual mood if provided, otherwise analyze text
#         if mood_override and mood_override.lower() in ["happy", "sad", "angry", "excited", "neutral"]:
#             detected_mood = mood_override.lower()
#             mood_source = "manually specified"
#         else:
#             detected_mood = SongRecommendationEngine.analyze_mood(user_text)
#             mood_source = "detected from your message"
        
#         # Get song recommendations
#         songs = SongRecommendationEngine.get_recommendations(detected_mood, count)
        
#         # Format response
#         mood_emoji = {
#             "happy": "😊",
#             "sad": "😢", 
#             "angry": "😠",
#             "excited": "🚀",
#             "neutral": "😐"
#         }
        
#         result = [
#             f"🎵 **Song Recommendations Based on Your Mood**",
#             f"",
#             f"**Detected Mood:** {mood_emoji.get(detected_mood, '🎵')} {detected_mood.title()} ({mood_source})",
#             f"**Your Message:** \"{user_text}\"",
#             f"",
#             f"**🎧 Recommended Songs:**"
#         ]
        
#         for i, song in enumerate(songs, 1):
#             result.append(f"{i}. **{song['title']}** by {song['artist']}")
#             result.append(f"   🔗 [Listen on Spotify]({song['spotify_url']})")
        
#         result.extend([
#             f"",
#             f"💡 **Tip:** Click the Spotify links to listen to these tracks!",
#             f"🔄 Want different recommendations? Try specifying a different mood!"
#         ])
        
#         return "\n".join(result)
        
#     except Exception as e:
#         raise McpError(ErrorData(
#             code=INTERNAL_ERROR,
#             message=f"Failed to generate song recommendations: {str(e)}"
#         ))

# MAKE_IMG_BLACK_AND_WHITE_DESCRIPTION = RichToolDescription(
#     description="Convert an image to black and white and save it.",
#     use_when="Use this tool when the user provides an image URL and requests it to be converted to black and white.",
#     side_effects="The image will be processed and saved in a black and white format.",
# )

# @mcp.tool(description=MAKE_IMG_BLACK_AND_WHITE_DESCRIPTION.model_dump_json())
# async def make_img_black_and_white(
#     puch_image_data: Annotated[str, Field(description="Base64-encoded image data to convert to black and white")] = None,
# ) -> list[TextContent | ImageContent]:
#     import base64
#     import io

#     from PIL import Image

#     try:
#         image_bytes = base64.b64decode(puch_image_data)
#         image = Image.open(io.BytesIO(image_bytes))

#         bw_image = image.convert("L")

#         buf = io.BytesIO()
#         bw_image.save(buf, format="PNG")
#         bw_bytes = buf.getvalue()
#         bw_base64 = base64.b64encode(bw_bytes).decode("utf-8")

#         return [ImageContent(type="image", mimeType="image/png", data=bw_base64)]
#     except Exception as e:
#         raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))

# # --- Run MCP Server ---
# async def main():
#     print("🚀 Starting MCP server on http://0.0.0.0:8086")
#     await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)

# if __name__ == "__main__":
#     asyncio.run(main())