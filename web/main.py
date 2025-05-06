import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import uvicorn

# Add parent directory to path so we can import from the root
sys.path.append(str(Path(__file__).parent.parent))

from storage.data_ingestion import DataIngestion
from storage.vector_store import FAISSVectorStore
from markdown.generator import MarkdownGenerator

# Create FastAPI app
app = FastAPI(
    title="Conversation Archive",
    description="Web interface for searching and browsing conversation data",
    version="1.0.0",
)

# Create data access objects
data_ingestion = DataIngestion()
vector_store = FAISSVectorStore()
markdown_generator = MarkdownGenerator()

# Set up templates and static files
templates_path = Path(__file__).parent / "templates"
static_path = Path(__file__).parent / "static"

if not templates_path.exists():
    templates_path.mkdir(exist_ok=True, parents=True)
if not static_path.exists():
    static_path.mkdir(exist_ok=True, parents=True)

templates = Jinja2Templates(directory=str(templates_path))
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Home page with calendar view
    """
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "title": "Conversation Archive",
            "current_date": datetime.now().strftime("%Y-%m-%d"),
        }
    )


@app.get("/api/calendar")
async def get_calendar_data(
    year: int = None,
    month: int = None
):
    """
    Get calendar data for a specific month
    """
    if not year:
        year = datetime.now().year
    if not month:
        month = datetime.now().month
    
    # Get statistics from vector store
    stats = vector_store.get_stats()
    
    # Extract conversation counts by date
    date_counts = stats.get("dates", {})
    
    # Format for calendar display
    calendar_data = []
    
    # Get the first day of the month
    first_day = datetime(year, month, 1)
    
    # Calculate the number of days in the month
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    
    num_days = (next_month - first_day).days
    
    # Create calendar data
    for day in range(1, num_days + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        calendar_data.append({
            "date": date_str,
            "day": day,
            "count": date_counts.get(date_str, 0),
            "has_data": date_str in date_counts
        })
    
    return {
        "year": year,
        "month": month,
        "days": calendar_data
    }


@app.get("/api/day/{date}")
async def get_day_data(date: str):
    """
    Get conversation data for a specific day
    """
    try:
        # Validate date format
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get all conversations for this date from both sources
    limitless_results = data_ingestion.search_conversations(
        query="",
        k=100,
        date=date,
        source="limitless"
    )
    
    bee_results = data_ingestion.search_conversations(
        query="",
        k=100,
        date=date,
        source="bee"
    )
    
    # Combine and sort by timestamp
    results = limitless_results + bee_results
    results.sort(key=lambda x: x.get("timestamp", ""))
    
    # Format the results
    formatted_results = []
    for result in results:
        # Format the timestamp for display
        timestamp = result.get("timestamp", "")
        time_str = ""
        if timestamp:
            try:
                time_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = time_obj.strftime('%I:%M %p')
            except:
                pass
        
        # Format the location
        location = ""
        if result.get("metadata", {}).get("location"):
            location = str(result.get("metadata", {}).get("location", ""))
        
        # Format the duration
        duration = ""
        if result.get("metadata", {}).get("duration"):
            duration_min = int(result.get("metadata", {}).get("duration", 0) / 60)
            duration = f"{duration_min} minutes"
        
        # Add to formatted results
        formatted_results.append({
            "id": result.get("id", ""),
            "source": result.get("source", ""),
            "time": time_str,
            "summary": result.get("summary", "No summary available"),
            "location": location,
            "duration": duration,
            "has_transcript": bool(result.get("text", ""))
        })
    
    return {
        "date": date,
        "conversation_count": len(formatted_results),
        "conversations": formatted_results
    }


@app.get("/api/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get details of a specific conversation
    """
    # Get the conversation from the vector store
    conversation = vector_store.get_document_by_id(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Format the timestamp for display
    timestamp = conversation.get("timestamp", "")
    time_str = ""
    if timestamp:
        try:
            time_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = time_obj.strftime('%Y-%m-%d %I:%M %p')
        except:
            pass
    
    # Format the result
    result = {
        "id": conversation.get("id", ""),
        "source": conversation.get("source", ""),
        "time": time_str,
        "date": conversation.get("date", ""),
        "summary": conversation.get("summary", ""),
        "text": conversation.get("text", ""),
        "metadata": conversation.get("metadata", {})
    }
    
    return result


@app.get("/api/search")
async def search_conversations(
    query: str = Query(..., description="Search query"),
    date: str = Query(None, description="Filter by date in YYYY-MM-DD format"),
    source: str = Query(None, description="Filter by source (limitless or bee)"),
    limit: int = Query(10, description="Maximum number of results to return")
):
    """
    Search for conversations
    """
    results = data_ingestion.search_conversations(
        query=query,
        k=limit,
        date=date,
        source=source
    )
    
    # Format the results
    formatted_results = []
    for result in results:
        # Format the timestamp for display
        timestamp = result.get("timestamp", "")
        time_str = ""
        date_str = result.get("date", "")
        
        if timestamp:
            try:
                time_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = time_obj.strftime('%I:%M %p')
                date_str = time_obj.strftime('%Y-%m-%d')
            except:
                pass
        
        # Extract a snippet from the text
        text = result.get("text", "")
        snippet = text[:300] + "..." if len(text) > 300 else text
        
        # Add to formatted results
        formatted_results.append({
            "id": result.get("id", ""),
            "score": round(result.get("score", 0) * 100),  # Convert to percentage
            "source": result.get("source", ""),
            "date": date_str,
            "time": time_str,
            "summary": result.get("summary", "No summary available"),
            "snippet": snippet
        })
    
    return {
        "query": query,
        "result_count": len(formatted_results),
        "results": formatted_results
    }


@app.post("/api/ingest")
async def ingest_data(
    days: int = Query(1, description="Number of days to ingest"),
    limit_per_day: int = Query(50, description="Maximum number of entries per day per API")
):
    """
    Ingest new data from APIs
    """
    try:
        result = data_ingestion.ingest_data(days=days, limit_per_day=limit_per_day)
        return {
            "status": "success",
            "message": f"Ingested {result.get('added_to_vector_store', 0)} documents",
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ingesting data: {str(e)}")


@app.post("/api/markdown/generate")
async def generate_markdown(
    date: str = Query(None, description="Date in YYYY-MM-DD format"),
    days: int = Query(1, description="Number of days to generate"),
    force: bool = Query(False, description="Force regeneration of existing files")
):
    """
    Generate markdown files
    """
    try:
        if date:
            result = markdown_generator.generate_daily_markdown(date_str=date, force_regenerate=force)
            results = [result]
        else:
            results = markdown_generator.generate_date_range(days=days, force_regenerate=force)
        
        return {
            "status": "success",
            "message": f"Generated {len(results)} markdown files",
            "files": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating markdown: {str(e)}")


@app.get("/day/{date}", response_class=HTMLResponse)
async def day_view(request: Request, date: str):
    """
    Day view page
    """
    try:
        # Validate date format
        datetime.strptime(date, "%Y-%m-%d")
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%B %d, %Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    return templates.TemplateResponse(
        "day.html", 
        {
            "request": request, 
            "title": f"Conversations - {formatted_date}",
            "date": date,
            "formatted_date": formatted_date,
        }
    )


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, query: str = ""):
    """
    Search page
    """
    return templates.TemplateResponse(
        "search.html", 
        {
            "request": request, 
            "title": "Search Conversations",
            "query": query,
        }
    )


@app.get("/conversation/{conversation_id}", response_class=HTMLResponse)
async def conversation_view(request: Request, conversation_id: str):
    """
    Conversation detail page
    """
    # We'll fetch the conversation data in the template with JavaScript
    return templates.TemplateResponse(
        "conversation.html", 
        {
            "request": request, 
            "title": "Conversation Details",
            "conversation_id": conversation_id,
        }
    )


# Run the application
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)