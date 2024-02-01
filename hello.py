from flask import Flask, jsonify, request
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from apify_client import ApifyClient
from datetime import datetime, timedelta
import openai
import os


app = Flask(__name__)

es_username = 'elastic'
es_password = 'MHtdbIroswOBhEsc1z=F'

openai.api_key = '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'

# Elasticsearch setup
es = Elasticsearch("https://localhost:9200", http_auth=(es_username, es_password), verify_certs=False)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize the Apify Client with your token
client = ApifyClient(token='apify_api_B7DcUY3VZbUhQROKDRT7hv0DDxIqUU31sn6e')

@app.route('/tweets/<username>', methods=['GET'])
def get_tweets(username):
    def get_date_a_year_ago():
        return (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    date_a_year_ago = get_date_a_year_ago()
    # Set up the input for the Apify client
    run_input = {
        "dev_dataset_clear": False,
        "dev_dataset_enable": False,
        "dev_transform_enable": False,
        "filters.consumer_video": False,
        "filters.images": False,
        "filters.links": False,
        "filters.media": False,
        "filters.native_video": False,
        "filters.news": False,
        "filters.periscope": False,
        "filters.pro_video": False,
        "filters.replies": False,
        "filters.retweets": False,
        "filters.safe": False,
        "filters.spaces": False,
        "filters.twimg": False,
        "filters.verified": False,
        "filters.videos": False,
        "filters.vine": False,
        "limit": 1000,
        "query": f"(from:{username}) since:{date_a_year_ago}"
    }

    try:
        run = client.actor("jupri/twitter-scraper").call(run_input=run_input)
        tweets = [item for item in client.dataset(run["defaultDatasetId"]).iterate_items()]

        for tweet in tweets:
            if 'content' in tweet:
                embedding = model.encode(tweet['content'])
                # Adjusting the structure to match your tweet JSON format
                tweet_document = {
                    "content": tweet['content'],
                    "created_at": tweet['created_at'],
                    "lang": tweet.get('lang', None),
                    "embedding": embedding.tolist(),
                    # Include other fields as needed
                }
                es.index(index="tweets", document=tweet_document)

        return jsonify(tweets)
    except Exception as e:
        return jsonify({"error": str(e)})
    
@app.route('/search', methods=['GET'])
def search_tweets():
    query = request.args.get('query')
    query_vector = model.encode(query)

    body = {
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "must": {
                            "match": {"content": query}
                        }
                    }
                },
                "script_score": {
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": query_vector}
                    }
                }
            }
        },
        "size": 15
    }
    response = es.search(index="tweets", body=body)
    hits = response['hits']['hits']

    # Filtering duplicates
    seen = set()
    unique_tweets = []
    for hit in hits:
        content = hit['_source']['content']
        print("Tweet:", content)  # Print each tweet
        if content not in seen:
            seen.add(content)
            unique_tweets.append(content)
            if len(unique_tweets) == 10:  # Stop after getting 10 unique tweets
                break

    # Create the prompt
    tweet_texts = " ".join(unique_tweets)
    prompt = f"Here are the tweets created by this user: {tweet_texts}... " \
             f"How would the user respond to this question: '{query}' based on the context from the tweet. " \
             "Make sure to not add additional data or any other text. All I am expecting is a answer without any other text. " \
             "If you can formulate an answer, return that. If not return an error message saying, answers may not be accurate, " \
             "but make sure to return a answer that you guess from the tweets. Make sure not to use any of your previous knowledge to do so."
    print("Sending the following prompt to ChatGPT:", prompt)  # Print the prompt
    

    try:
        gpt_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        answer = gpt_response.choices[0].message['content']
    except Exception as e:
        answer = f"An error occurred: {str(e)}"

    return jsonify({"response": answer})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)

