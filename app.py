from pathlib import Path
import traceback
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates  # for rendering HTML templates
from fastapi.staticfiles import StaticFiles  # for serving static files like CSS, JS, images
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from backend import run_travel_agent

BASE_DIR = Path(__file__).resolve().parent


# Create FastAPI app
app= FastAPI(
    title="TripMate-AI",
    description="An AI-powered travel planning assistant that helps users plan their trips by providing flight and hotel recommendations, as well as a complete travel itinerary.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)

# Initialize Jinja2 templates
templates=Jinja2Templates(directory=BASE_DIR / "templates")


#=========================
# Travel Request Model
#=========================

# using Pydantic's BaseModel to define the structure of the travel request data
class TravelRequest(BaseModel):
    message: str
    thread_id: str  # to keep track of the conversation thread for each user
    images: list

# API endpoint to serve the home page and handle travel requests
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    This endpoint serves the home page of the TripMate-AI application.
    It renders the 'index.html' template and passes the request object to it.
    """
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )



# API endpoint to handle travel requests from the user. 
# It receives a TravelRequest object, processes it using the travel agent, and returns the response.
@app.post("/api/travel")
async def travel_planner(travel_request: TravelRequest):
    try:
        # Extract user input from the request
        user_message = travel_request.message.strip()

        # Validate that the user message is not empty
        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Message cannot be empty."
                }
            )

        # Call the travel agent to process the user's request and get the response
        result=run_travel_agent(
            user_input=user_message,
            thread_id=travel_request.thread_id
        )

        return JSONResponse(
            content={
                "success": True,
                "thread_id": result["thread_id"],
                "answer": result["answer"],
                "flight_results": result["flight_results"],
                "hotel_results": result["hotel_results"],
                "itinerary": result["itinerary"],
                "llm_calls": result["llm_calls"],
                "images": result["images"]
            }
        )

    # Handle exceptions and return an error response
    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )



# This endpoint serves as a health check for the TripMate-AI application.
# It returns a simple JSON response indicating that the application is running.
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "message": "AI Travel Planner API is running"
    }

# This endpoint serves the favicon for the application.
# favicon.ico is a small icon that represents the website in the browser tab.
@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
