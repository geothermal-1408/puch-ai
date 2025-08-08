import asyncio
from typing import Annotated
import os
from dotenv import load_dotenv
from fastmcp.server import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp import ErrorData, McpError
from mcp.server.auth.provider import AccessToken
from mcp.types import TextContent, ImageContent, INVALID_PARAMS, INTERNAL_ERROR
from pydantic import BaseModel, Field, AnyUrl
import tempfile
from datetime import datetime, timedelta

# --- Load environment variables ---
load_dotenv()

TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")

assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"

# --- Auth Provider ---
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(
                token=token,
                client_id="puch-client",
                scopes=["*"],
                expires_at=None,
            )
        return None

# --- Rich Tool Description model ---
class RichToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None = None

# --- PDF Processing Class ---
class PDFProcessor:
    @staticmethod
    async def process_pdf(pdf_data: str) -> str:
        """Process PDF data and return extracted text"""
        import base64
        from PyPDF2 import PdfReader
        from io import BytesIO
        
        try:
            # Decode base64 PDF data
            pdf_bytes = base64.b64decode(pdf_data)
            
            # Create a PDF reader object
            pdf_reader = PdfReader(BytesIO(pdf_bytes))
            
            # Extract text from each page
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n\n"
            
            return text if text.strip() else "No text could be extracted from the PDF."
        
        except Exception as e:
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to process PDF: {str(e)}"
            ))

# --- MCP Server Setup ---
mcp = FastMCP(
    "PDF Chat & Schedule Generator MCP Server",
    auth=SimpleBearerAuthProvider(TOKEN),
)

# --- Tool: validate (required by Puch) ---
@mcp.tool
async def validate() -> str:
    return MY_NUMBER

# --- Tool: chat_with_pdf ---
ChatWithPDFDescription = RichToolDescription(
    description="Analyze and answer questions about PDF documents",
    use_when="User provides a PDF document and wants to ask questions about its content",
    side_effects="The PDF content will be processed and analyzed"
)

@mcp.tool(description=ChatWithPDFDescription.model_dump_json())
async def chat_with_pdf(
    pdf_data: Annotated[str, Field(description="Base64-encoded PDF file data")],
    question: Annotated[str, Field(description="Question about the PDF content")],
) -> str:
    """
    Analyze a PDF document and answer questions about its content.
    """
    # First extract text from PDF
    pdf_text = await PDFProcessor.process_pdf(pdf_data)
    
    # Here you would typically use an LLM to answer questions about the text
    # For this example, we'll just return the relevant section that might contain the answer
    
    # Simple keyword-based answer (in a real implementation, use an LLM)
    if "summary" in question.lower():
        return f"PDF Summary (first 500 chars):\n\n{pdf_text[:500]}..."
    elif "page count" in question.lower():
        return "This is a simple text extractor. For page count, please use a full PDF processing tool."
    else:
        return (
            f"PDF Content Analysis\n\n"
            f"Question: {question}\n\n"
            f"Relevant content from PDF (first 1000 chars):\n\n"
            f"{pdf_text[:1000]}..."
        )

# --- Tool: generate_schedule ---
ScheduleGeneratorDescription = RichToolDescription(
    description="Generate a daily or weekly schedule based on tasks and priorities",
    use_when="User needs help organizing their time with a structured schedule",
    side_effects="Creates a time-blocked schedule"
)

class ScheduleItem(BaseModel):
    task: str
    duration_minutes: int
    priority: int = Field(ge=1, le=3, description="1=high, 2=medium, 3=low")

@mcp.tool(description=ScheduleGeneratorDescription.model_dump_json())
async def generate_schedule(
    tasks: Annotated[list[ScheduleItem], Field(description="List of tasks to schedule")],
    start_time: Annotated[str, Field(description="Schedule start time (HH:MM)")] = "08:00",
    end_time: Annotated[str, Field(description="Schedule end time (HH:MM)")] = "20:00",
    date: Annotated[str | None, Field(description="Date for schedule (YYYY-MM-DD)")] = None,
) -> str:
    """
    Generate a time-blocked schedule based on provided tasks and time constraints.
    """
    try:
        # Parse time inputs
        start_h, start_m = map(int, start_time.split(':'))
        end_h, end_m = map(int, end_time.split(':'))
        
        # Calculate total available minutes
        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt = datetime.strptime(end_time, "%H:%M")
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)  # Handle overnight schedules
        total_minutes = int((end_dt - start_dt).total_seconds() / 60)
        
        # Sort tasks by priority then duration
        sorted_tasks = sorted(tasks, key=lambda x: (x.priority, x.duration_minutes))
        
        # Schedule tasks
        current_time = start_dt
        schedule = []
        remaining_minutes = total_minutes
        
        for task in sorted_tasks:
            if task.duration_minutes <= remaining_minutes:
                end_time = current_time + timedelta(minutes=task.duration_minutes)
                schedule.append({
                    'task': task.task,
                    'start': current_time.strftime("%H:%M"),
                    'end': end_time.strftime("%H:%M"),
                    'duration': task.duration_minutes,
                    'priority': task.priority
                })
                current_time = end_time
                remaining_minutes -= task.duration_minutes
            else:
                break  # Skip tasks that don't fit
        
        # Format the schedule
        date_str = f" for {date}" if date else ""
        result = [f"📅 Generated Schedule{date_str} ({start_time} - {end_time}):\n"]
        
        for item in schedule:
            priority_emoji = "❗" if item['priority'] == 1 else "🔹" if item['priority'] == 2 else "▪️"
            result.append(
                f"{priority_emoji} {item['start']}-{item['end']} ({item['duration']}min): {item['task']}"
            )
        
        if remaining_minutes > 0:
            result.append(f"\n⏳ Remaining unscheduled time: {remaining_minutes} minutes")
        
        return "\n".join(result)
    
    except Exception as e:
        raise McpError(ErrorData(
            code=INVALID_PARAMS,
            message=f"Invalid schedule parameters: {str(e)}"
        ))

# --- Run MCP Server ---
async def main():
    print("🚀 Starting MCP server on http://0.0.0.0:8086")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)

if __name__ == "__main__":
    asyncio.run(main())