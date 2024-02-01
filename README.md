GPT_DIRECT.py:

This file simply just requires a apify key and chat gpt key and will get all tweets of the user provided in the endpoint. It will also return the answer that GPT creates after passing all tweets into gpt as well as the query passed in the endpoint. 

QUERY EXAMPLE: http://localhost:5000/query_tweets?username=**elonmusk**&query=**What%20Does%20he%20like?**

VectorQuery.py

This file is a little more complicated as it requires elastic on your computer as well as gpt, and apify. What this does is it stores the json tweets in a vector database after converting to embeddings. It then uses the search feature in vector dbs, and finds 5 tweets that are most related with the query. It passes these into chat gpt and returns an answer

This needs two queries: one that returns the tweets, one that returns the answer

Query 1 EXAMPLE: localhost:5000/tweets/**elonmusk**
Query 2 EXAMPLE: http://localhost:5000/search?query=**What%20cologne%20does%20elon%20musk%20like**
