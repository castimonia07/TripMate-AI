import os
import certifi

from dotenv import load_dotenv
load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from typing import TypedDict,Annotated
import operator  # It is used to perform operations on the data, such as sorting or filtering.
import uuid 

import psycopg # It is used to connect to a PostgreSQL database and execute SQL queries.
from psycopg.rows import dict_row

from langgraph.graph import StateGraph, START,END
from langgraph.checkpoint.postgres import PostgresSaver

from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq


from tools.tavily_tool import tavily_search
from tools.flight_tool import search_flights

from pydantic import BaseModel


# function to get database connection
def get_database_url():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set.")

    # Ensure that the database URL has the correct format for SSL mode
    # (SSL mode is a security feature that encrypts the connection between the client and the database server.)
    if "sslmode" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

    return database_url


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set.")

## LLM

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="openai/gpt-oss-120b"
)

# =========================
# State (Used to store the state of the travel planning process)
# =========================

class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary: str
    llm_calls: int  # it is used to keep track of the number of calls made to the language model (LLM) during the travel planning process.

# =========================
# Flight Agent
# =========================

def flight_agent(state: TravelState):
    """
    This function takes a TravelState object as input and performs the following steps:
    1. It extracts the user's query from the state.
    2. It calls the search_flights function to get flight results based on the user's query.
    3. It updates the state with the flight results and increments the llm_calls counter.
    4. It returns the updated state.
    """
    user_query = state["user_query"]
    flight_data = search_flights(user_query)

    return{
        "flight_results": flight_data,
        "messages":[
            AIMessage(content="Flight results fetched.")
        ],
        "llm_calls": state.get("llm_calls",0) + 1
    }


# =========================
# Hotel Agent
# =========================

def hotel_agent(state: TravelState):
    """
    This function takes a TravelState object as input and performs the following steps:
    1. It extracts the user's query from the state.
    2. It calls the tavily_search function to get hotel results based on the user's query.
    3. It updates the state with the hotel results and increments the llm_calls counter.
    4. It returns the updated state.
    """
    user_query = state["user_query"]
    hotel_data = tavily_search(user_query)

    return{
        "hotel_results": hotel_data,
        "messages":[
            AIMessage(content="Hotel results fetched.")
        ],
        "llm_calls": state.get("llm_calls",0) + 1
    }


# =========================
# Itinerary Agent
# =========================
# This function takes a TravelState object as input and performs the following steps:
# 1. It constructs a prompt that includes the user's query, flight results, and hotel results.
# 2. It calls the language model (llm) to generate a complete travel itinerary  
# 3. It updates the state with the generated itinerary and increments the llm_calls counter.
# 4. It returns the updated state.

def itinerary_agent(state: TravelState):
    prompt = f"""
Create a complete travel itinerary.

User Query:
{state['user_query']}

Flight Results:
{state['flight_results']}

Hotel Results:
{state['hotel_results']}

Make the itinerary practical, budget-aware, and easy to follow.
"""

    response = llm.invoke([
        SystemMessage(content="You are an expert travel planner."),
        HumanMessage(content=prompt)
    ])

    return {
        "itinerary": response.content,
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }



# =========================
# Final Response Agent
# =========================
## This function takes a TravelState object as input and performs the following steps:
# 1. It constructs a final prompt that includes the user's query, flight results, hotel results, and itinerary.
# 2. It calls the language model (llm) to generate a final travel response
# 3. It updates the state with the final response and increments the llm_calls counter.
# 4. It returns the updated state.



def final_agent(state: TravelState):
    final_prompt = f"""
Generate the final travel response for the user.

User Request:
{state['user_query']}

Flights:
{state['flight_results']}

Hotels:
{state['hotel_results']}

Itinerary:
{state['itinerary']}

Format the final answer beautifully using these sections:

1. Trip Summary
2. Flight Information
3. Hotel Suggestions
4. Day-by-Day Itinerary
5. Estimated Budget
6. Final Recommendations

Important:
- Be clear and practical.
- Mention that live flight API may not provide ticket prices if pricing is unavailable.
- Keep the response useful for real travel planning.
"""

    response = llm.invoke([
        SystemMessage(content="You are a professional AI travel booking assistant."),
        HumanMessage(content=final_prompt)
    ])

    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# =========================
# Build Graph
# =========================

graph=StateGraph(TravelState) # It is used to create a state graph that represents the flow of the travel planning process, with each agent as a node in the graph.

## Adding nodes to the graph for each agent
graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)

## Adding edges to the graph to define the flow between agents
graph.add_edge(START, "flight_agent")
graph.add_edge("flight_agent", "hotel_agent")
graph.add_edge("hotel_agent", "itinerary_agent")
graph.add_edge("itinerary_agent", "final_agent")
graph.add_edge("final_agent", END)


# =========================
# PostgreSQL Checkpointer(Checkpointing is a technique used to save the state of a process at certain points in time, allowing for recovery in case of failures.)
# =========================

# Get the database URL from the environment variable and ensure it has the correct format for SSL mode

DATABASE_URL = get_database_url()

_conn=psycopg.connect(
    DATABASE_URL,
    row_factory=dict_row   # it is used to specify that the rows returned from the database queries should be in the form of dictionaries, allowing for easier access to column values by name.
)

_conn.autocommit = True # it is used to set the connection to autocommit mode, meaning that each SQL statement is automatically committed to the database without requiring an explicit commit command.


checkpointer = PostgresSaver(_conn)
checkpointer.setup()

travel_graph = graph.compile(checkpointer=checkpointer) # It is used to compile the state graph with the PostgreSQL checkpointer, enabling the saving and loading of the travel planning process state to and from the database.



# =========================
# Function for FastAPI
# =========================

# This function is designed to run the travel agent process based on user input and an optional thread ID. It performs the following steps:
# 1. If no thread ID is provided, it generates a unique thread ID for the
# 2. It creates a configuration dictionary that includes the thread ID.
# 3. It invokes the travel_graph with the user's input and the configuration, which runs through the entire travel planning process.
# 4. It retrieves the final answer from the last message in the result.

def run_travel_agent(user_input:str,thread_id:str | None=None):
    if not thread_id:
        thread_id=f"user_{uuid.uuid4().hex}"  # Generate a unique thread ID if not provided

    #config LangGraph ko execution ki configuration deta hai, 
    # aur thread_id specifically batata hai ki ye execution kis 
    # conversation/checkpoint thread ka part hai.
    config={
        "configurable": {
            "thread_id":thread_id
        }
    }


    result=travel_graph.invoke(
        {
            "messages":[
                HumanMessage(content=user_input)
            ],
            "user_query":user_input,
            "flight_results":"",
            "hotel_results":"",
            "itinerary":"",
            "llm_calls":0
        },config=config
    )

    final_answer=result["messages"][-1].content

    return {
        "thread_id": thread_id,
        "answer": final_answer,
        "flight_results": result.get("flight_results", ""),
        "hotel_results": result.get("hotel_results", ""),
        "itinerary": result.get("itinerary", ""),
        "llm_calls": result.get("llm_calls", 0),
    }