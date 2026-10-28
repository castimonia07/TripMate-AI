from tavily import TavilyClient
import os

from dotenv import load_dotenv
load_dotenv()

client=TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

## function for searching the tavily database for the query and returning the results
def tavily_search(query):

    #here the cleint will call the tavily api and generate the response for the query and return the resultss
    response=client.search(
        query=query,
        max_results=5,
        )

    results=[]

    for i,r in enumerate(response["results"],1):
        title=r.get("title","Unknown")
        url=r.get("url","")
        snippet=r.get("snippet","").strip()

        # keep only the first 300 characters of the snippet
        if len(snippet)>300:
            snippet=snippet[:300].rstrip(" ",1)[0]+"..."

        results.append(f"{i}. **{title}**\n {url}\n {snippet}\n")

    return "\n\n".join(results)