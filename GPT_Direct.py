from flask import Flask, jsonify, request
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from apify_client import ApifyClient
from datetime import datetime, timedelta
import openai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

openai.api_key = os.getenv('OPENAI_API_KEY')

client = ApifyClient(token=os.getenv('APIFY_TOKEN'))

@app.route('/query_tweets', methods=['GET'])
def query_tweets():
    username = request.args.get('username')
    query = request.args.get('query')

    if not username or not query:
        return jsonify({"error": "Missing username or query parameter"}), 400
    
    date_a_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

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
            # Retrieve tweets from the specified user within the last year
            run = client.actor("jupri/twitter-scraper").call(run_input=run_input)
            tweets = [item for item in client.dataset(run["defaultDatasetId"]).iterate_items()]
            
            # Proceed with searching within these tweets
            unique_tweets = []
            for tweet in tweets:
                if 'content' in tweet and tweet['content'] not in unique_tweets:
                    unique_tweets.append(tweet['content'])
                    if len(unique_tweets) == 10:  # Limiting to 10 unique tweets for simplicity
                        break
            
            # Formulate the prompt for GPT based on the query and retrieved tweets
            tweet_texts = " ".join(unique_tweets)
            prompt = f"How would the user @{username} respond to the question: '{query}' based on their tweets? " \
                    f"Generate a response using only the information from the tweets."
            
            gpt_response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )
            answer = gpt_response.choices[0].message['content']
            return jsonify({"answer": answer})
    except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)