# import asyncio
# from typing import Annotated
# import os
# from dotenv import load_dotenv
# from fastmcp.server import FastMCP
# from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair # type: ignore
# from mcp import ErrorData, McpError
# from mcp.server.auth.provider import AccessToken
# from mcp.types import TextContent, ImageContent, INVALID_PARAMS, INTERNAL_ERROR
# from pydantic import BaseModel, Field, AnyUrl
# import tempfile
# from datetime import datetime, timedelta

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
#         # If pdf_data is base64 encoded, decode it
#             if isinstance(pdf_data, str):
#                 try:
#                     pdf_bytes = base64.b64decode(pdf_data)
#                 except:
#                     # If not base64, assume it's already bytes
#                     pdf_bytes = pdf_data.encode() if isinstance(pdf_data, str) else pdf_data
#             else:
#                 pdf_bytes = pdf_data
        
#         # Create a BytesIO object from the PDF data
#             pdf_stream = BytesIO(pdf_bytes)
            
#             text = ""
#             try:
#                 pdf_reader = PyPDF2.PdfReader(pdf_stream)
                
#                 # Check if pdf_reader is valid and has pages
#                 if pdf_reader is None:
#                     return "Error: Failed to create PDF reader"
                
#                 if not hasattr(pdf_reader, 'pages') or pdf_reader.pages is None:
#                     return "Error: PDF reader could not access pages"
                
#                 # Check if PDF has pages
#                 if len(pdf_reader.pages) == 0:
#                     return "Error: PDF appears to be empty"
                
#                 # Extract text from all pages
#                 for page in pdf_reader.pages:
#                     if page is not None:
#                         extracted_text = page.extract_text()
#                         if extracted_text:
#                             text += extracted_text + "\n"
                            
#             except PdfReadError as e:
#                 return f"Error: Invalid or corrupted PDF file - {str(e)}"
#             except Exception as e:
#                 return f"Error reading PDF: {str(e)}"
            
#             if not text.strip():
#                 return "Error: No text could be extracted from the PDF"
            
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

# # --- Tool: chat_with_pdf ---
# ChatWithPDFDescription = RichToolDescription(
#     description="Analyze and answer questions about PDF documents",
#     use_when="User provides a PDF document and wants to ask questions about its content",
#     side_effects="The PDF content will be processed and analyzed"
# )

# @mcp.tool(description=ChatWithPDFDescription.model_dump_json())
# async def chat_with_pdf(
#     pdf_data: Annotated[str, Field(description="Base64-encoded PDF file data")],
#     question: Annotated[str, Field(description="Question about the PDF content")],
# ) -> str:
#     """
#     Analyze a PDF document and answer questions about its content.
#     """
#     # First extract text from PDF
#     pdf_text = await PDFProcessor.process_pdf(pdf_data)

#     if "summary" in question.lower():
#         return f"PDF Summary (first 500 chars):\n\n{pdf_text[:500]}..."
#     elif "page count" in question.lower():
#         return "This is a simple text extractor. For page count, please use a full PDF processing tool."
#     else:
#         return (
#             f"PDF Content Analysis\n\n"
#             f"Question: {question}\n\n"
#             f"Relevant content from PDF (first 1000 chars):\n\n"
#             f"{pdf_text[:1000]}..."
#         )

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
#     """+'
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

# # import asyncio
# # from typing import Annotated
# # import os
# # from dotenv import load_dotenv
# # from fastmcp import FastMCP
# # from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
# # from mcp import ErrorData, McpError
# # from mcp.server.auth.provider import AccessToken
# # from mcp.types import TextContent, ImageContent, INVALID_PARAMS, INTERNAL_ERROR
# # from pydantic import BaseModel, Field, AnyUrl

# # import markdownify
# # import httpx
# # import readabilipy

# # # --- Load environment variables ---
# # load_dotenv()

# # TOKEN = os.environ.get("AUTH_TOKEN")
# # MY_NUMBER = os.environ.get("MY_NUMBER")

# # assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
# # assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"

# # # --- Auth Provider ---
# # class SimpleBearerAuthProvider(BearerAuthProvider):
# #     def __init__(self, token: str):
# #         k = RSAKeyPair.generate()
# #         super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
# #         self.token = token

# #     async def load_access_token(self, token: str) -> AccessToken | None:
# #         if token == self.token:
# #             return AccessToken(
# #                 token=token,
# #                 client_id="puch-client",
# #                 scopes=["*"],
# #                 expires_at=None,
# #             )
# #         return None

# # # --- Rich Tool Description model ---
# # class RichToolDescription(BaseModel):
# #     description: str
# #     use_when: str
# #     side_effects: str | None = None

# # # --- Fetch Utility Class ---
# # class Fetch:
# #     USER_AGENT = "Puch/1.0 (Autonomous)"

# #     @classmethod
# #     async def fetch_url(
# #         cls,
# #         url: str,
# #         user_agent: str,
# #         force_raw: bool = False,
# #     ) -> tuple[str, str]:
# #         async with httpx.AsyncClient() as client:
# #             try:
# #                 response = await client.get(
# #                     url,
# #                     follow_redirects=True,
# #                     headers={"User-Agent": user_agent},
# #                     timeout=30,
# #                 )
# #             except httpx.HTTPError as e:
# #                 raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url}: {e!r}"))

# #             if response.status_code >= 400:
# #                 raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url} - status code {response.status_code}"))

# #             page_raw = response.text

# #         content_type = response.headers.get("content-type", "")
# #         is_page_html = "text/html" in content_type

# #         if is_page_html and not force_raw:
# #             return cls.extract_content_from_html(page_raw), ""

# #         return (
# #             page_raw,
# #             f"Content type {content_type} cannot be simplified to markdown, but here is the raw content:\n",
# #         )

# #     @staticmethod
# #     def extract_content_from_html(html: str) -> str:
# #         """Extract and convert HTML content to Markdown format."""
# #         ret = readabilipy.simple_json.simple_json_from_html_string(html, use_readability=True)
# #         if not ret or not ret.get("content"):
# #             return "<error>Page failed to be simplified from HTML</error>"
# #         content = markdownify.markdownify(ret["content"], heading_style=markdownify.ATX)
# #         return content

# #     @staticmethod
# #     async def google_search_links(query: str, num_results: int = 5) -> list[str]:
# #         """
# #         Perform a scoped DuckDuckGo search and return a list of job posting URLs.
# #         (Using DuckDuckGo because Google blocks most programmatic scraping.)
# #         """
# #         ddg_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
# #         links = []

# #         async with httpx.AsyncClient() as client:
# #             resp = await client.get(ddg_url, headers={"User-Agent": Fetch.USER_AGENT})
# #             if resp.status_code != 200:
# #                 return ["<error>Failed to perform search.</error>"]

# #         from bs4 import BeautifulSoup
# #         soup = BeautifulSoup(resp.text, "html.parser")
# #         for a in soup.find_all("a", class_="result__a", href=True):
# #             href = a["href"]
# #             if "http" in href:
# #                 links.append(href)
# #             if len(links) >= num_results:
# #                 break

# #         return links or ["<error>No results found.</error>"]

# # # --- MCP Server Setup ---
# # mcp = FastMCP(
# #     "Job Finder MCP Server",
# #     auth=SimpleBearerAuthProvider(TOKEN),
# # )

# # # --- Tool: validate (required by Puch) ---
# # @mcp.tool
# # async def validate() -> str:
# #     return MY_NUMBER

# # # --- Tool: job_finder (now smart!) ---
# # JobFinderDescription = RichToolDescription(
# #     description="Smart job tool: analyze descriptions, fetch URLs, or search jobs based on free text.",
# #     use_when="Use this to evaluate job descriptions or search for jobs using freeform goals.",
# #     side_effects="Returns insights, fetched job descriptions, or relevant job links.",
# # )

# # @mcp.tool(description=JobFinderDescription.model_dump_json())
# # async def job_finder(
# #     user_goal: Annotated[str, Field(description="The user's goal (can be a description, intent, or freeform query)")],
# #     job_description: Annotated[str | None, Field(description="Full job description text, if available.")] = None,
# #     job_url: Annotated[AnyUrl | None, Field(description="A URL to fetch a job description from.")] = None,
# #     raw: Annotated[bool, Field(description="Return raw HTML content if True")] = False,
# # ) -> str:
# #     """
# #     Handles multiple job discovery methods: direct description, URL fetch, or freeform search query.
# #     """
# #     if job_description:
# #         return (
# #             f"📝 **Job Description Analysis**\n\n"
# #             f"---\n{job_description.strip()}\n---\n\n"
# #             f"User Goal: **{user_goal}**\n\n"
# #             f"💡 Suggestions:\n- Tailor your resume.\n- Evaluate skill match.\n- Consider applying if relevant."
# #         )

# #     if job_url:
# #         content, _ = await Fetch.fetch_url(str(job_url), Fetch.USER_AGENT, force_raw=raw)
# #         return (
# #             f"🔗 **Fetched Job Posting from URL**: {job_url}\n\n"
# #             f"---\n{content.strip()}\n---\n\n"
# #             f"User Goal: **{user_goal}**"
# #         )

# #     if "look for" in user_goal.lower() or "find" in user_goal.lower():
# #         links = await Fetch.google_search_links(user_goal)
# #         return (
# #             f"🔍 **Search Results for**: _{user_goal}_\n\n" +
# #             "\n".join(f"- {link}" for link in links)
# #         )

# #     raise McpError(ErrorData(code=INVALID_PARAMS, message="Please provide either a job description, a job URL, or a search query in user_goal."))


# # # Image inputs and sending images

# # MAKE_IMG_BLACK_AND_WHITE_DESCRIPTION = RichToolDescription(
# #     description="Convert an image to black and white and save it.",
# #     use_when="Use this tool when the user provides an image URL and requests it to be converted to black and white.",
# #     side_effects="The image will be processed and saved in a black and white format.",
# # )

# # @mcp.tool(description=MAKE_IMG_BLACK_AND_WHITE_DESCRIPTION.model_dump_json())
# # async def make_img_black_and_white(
# #     puch_image_data: Annotated[str, Field(description="Base64-encoded image data to convert to black and white")] = None,
# # ) -> list[TextContent | ImageContent]:
# #     import base64
# #     import io

# #     from PIL import Image

# #     try:
# #         image_bytes = base64.b64decode(puch_image_data)
# #         image = Image.open(io.BytesIO(image_bytes))

# #         bw_image = image.convert("L")

# #         buf = io.BytesIO()
# #         bw_image.save(buf, format="PNG")
# #         bw_bytes = buf.getvalue()
# #         bw_base64 = base64.b64encode(bw_bytes).decode("utf-8")

# #         return [ImageContent(type="image", mimeType="image/png", data=bw_base64)]
# #     except Exception as e:
# #         raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))

# # # --- Run MCP Server ---
# # async def main():
# #     print("🚀 Starting MCP server on http://0.0.0.0:8086")
# #     await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)

# # if __name__ == "__main__":
# #     asyncio.run(main())