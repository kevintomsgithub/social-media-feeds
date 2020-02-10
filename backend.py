from flask import Flask, render_template, jsonify, request
from datetime import datetime
from flask_cors import CORS

import json

import tweepy
import facebook

app = Flask(__name__)
CORS(app)

twitter_id = 'Your twitter ID'
consumer_key = "Your twitter Consumer Key"
consumer_secret = "Your consumer secret for Twitter"
tw_access_token = "Your Twitter access token"
tw_access_token_secret = "Your Twitter access token secret"

fb_access_token = "Your Facebook Access Token"

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(tw_access_token, tw_access_token_secret)

api = tweepy.API(auth)

graph = facebook.GraphAPI(access_token=fb_access_token, version="3.1")

previous_tw_post_id = []
previous_fb_post_id = []

twitter_stream_id = None
twitter_stream_tweet = None

#override tweepy.StreamListener to add logic to on_status
class MyStreamListener(tweepy.StreamListener):

    def on_status(self, tweet):
        global twitter_stream_id
        global twitter_stream_tweet
        twitter_stream_tweet = {
            'posts': []
        }
        twitter_stream_id = tweet.id

        post = {}
        post['created_time'] = convert_to_time(tweet.created_at)
        post['post_id'] = tweet.id
        post['username'] = tweet.user.name
        post['text'] = tweet.text
        post['profile_image'] = tweet.user.profile_image_url_https

        if 'extended_entities' in tweet._json:
            media_type = tweet.extended_entities['media'][0]['type']
            if media_type == 'photo':
                post['image_url'] = tweet.entities['media'][0]['media_url_https']
            elif media_type == 'video':
                post['video_url'] = tweet.extended_entities['media'][0]['video_info']['variants'][0]['url']

        twitter_stream_tweet['posts'].append(post)

        print(tweet.id)
        print(tweet.text)

    def on_error(self, status_code):
        if status_code == 420:
            #returning False in on_error disconnects the stream
            return False

myStreamListener = MyStreamListener()
myStream = tweepy.Stream(auth = api.auth, listener=myStreamListener)
myStream.filter(follow=[twitter_id], is_async=True)


def convert_to_time(x):
    m = x.strftime("%B")
    d = x.strftime("%d")
    H = x.strftime("%I")
    M = x.strftime("%M")
    ap = x.strftime("%p") 
    return f'{m} {d} at {H}:{M} {ap.upper()}'


@app.route('/')
def root():
    return render_template("index.html")


@app.route('/db_cred', methods=['POST'])
def db_cred():
    cred = {
        # Paste down your firebase credentials from the Web
    }
    return jsonify(cred)


@app.route('/get_tweets')
def get_tweets():

    tw_data_json = {
        'posts': []
    }

    my_tweets = api.user_timeline(twitter_id)

    for tweet in my_tweets:
        if tweet.id not in previous_tw_post_id:
            post = {}
            previous_tw_post_id.append(tweet.id)

            post['created_time'] = convert_to_time(tweet.created_at)
            
            post['post_id'] = tweet.id
            post['username'] = tweet.user.name
            post['text'] = tweet.text
            post['profile_image'] = tweet.user.profile_image_url_https

            if 'extended_entities' in tweet._json:
                media_type = tweet.extended_entities['media'][0]['type']
                if media_type == 'photo':
                    post['image_url'] = tweet.entities['media'][0]['media_url_https']
                elif media_type == 'video':
                    post['video_url'] = tweet.extended_entities['media'][0]['video_info']['variants'][0]['url']

            tw_data_json['posts'].append(post)
    
    return jsonify(tw_data_json)


@app.route('/get_fb_stories')
def get_fb_stories():

    fb_data_json = {
        'posts': []
    }

    data = graph.get_object('me', fields='id,name,posts{full_picture,message,caption,created_time,source}')

    for feed in data['posts']['data']:
        if feed['id'] not in previous_fb_post_id:
            post = {}
            previous_fb_post_id.append(feed['id'])

            post['created_time'] = convert_to_time(datetime.strptime(feed['created_time'], '%Y-%m-%dT%H:%M:%S+0000'))
            
            post['post_id'] = feed['id']
            post['username'] = data['name']
            post['text'] = feed['message']
            post['profile_image'] = ''

            if 'source' in feed:
                post['video_url'] = feed['source']
            elif 'full_picture' in feed:
                post['image_url'] = feed['full_picture']

            fb_data_json['posts'].append(post)

    return jsonify(fb_data_json)


@app.route('/get_live_tweets')
def get_live_tweets():

    if twitter_stream_id not in previous_tw_post_id and twitter_stream_id != None:
        previous_tw_post_id.append(twitter_stream_id)
        print('Live data : ', twitter_stream_tweet)
        return jsonify(twitter_stream_tweet)

    return jsonify({
        'posts': []
    })


@app.route('/delete_tw_post')
def detele_tw_post():
    post_id = request.args.get('post_id')
    print(f"Delete tw post id : {post_id}")
    api.destroy_status(post_id)
    
    return jsonify({
        'success': 200
    })


@app.route('/post_tweet')
def post_tweet():
    tweet = request.args.get('tweet')
    print(f"Posting tweet : {tweet}")
    api.update_status(tweet)
    
    return jsonify({
        'success': 200
    })


@app.route('/logout')
def logout():

    global previous_tw_post_id, previous_fb_post_id
    global twitter_stream_id, twitter_stream_tweet

    previous_tw_post_id = []
    previous_fb_post_id = []

    twitter_stream_id = None
    twitter_stream_tweet = None

    print(f"Data Cleared")
    
    return jsonify({
        'success': 200
    })


if __name__ == '__main__':
    app.run(host='localhost', port=5000)