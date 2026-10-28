from tools.tavily_tool import tavily_search
from tools.flight_tool import search_flights

# res=tavily_search("Best Hotels in India")
# print(res)


res=search_flights("Find me a flight from Bangalore to New York City on July 2026")
print(res)

