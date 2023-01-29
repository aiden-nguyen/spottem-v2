from flask import Flask, request, url_for, session, redirect
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from datetime import datetime

app = Flask(__name__)

app.secret_key = "spottem"
app.config['SESSION_COOKIE_NAME'] = 'spottem cookie'
TOKEN_INFO = "token_info"

@app.route('/')
def login():
    session.clear()
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/logout')
def logout():
    session.clear() # clear the session data
    return redirect('/')

@app.route('/callback')
def callback():
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code') # retrive authorization code
    token_info = sp_oauth.get_access_token(code) # exchange authorization code for access token
    session[TOKEN_INFO] = token_info # saving token information in session
    return redirect(url_for('getUserInfo', _external=True)) # redirects to /getUserInfo

def getTimeStr(time_elapsed):
    if time_elapsed >= 1440: # been over a day since last song
            time_elapsed = (time_elapsed // 1440)
            if time_elapsed > 1:
                time_elapsed = str(time_elapsed) + " days"
            else:
                time_elapsed = str(time_elapsed) + " day"
    elif time_elapsed >= 60: # been over an hour since last song
        time_elapsed = (time_elapsed // 60)
        if time_elapsed > 1:
            time_elapsed = str(time_elapsed) + " hours"
        else:
            time_elapsed = str(time_elapsed) + " hour"
    elif time_elapsed > 1:
        time_elapsed = str(time_elapsed)  + " minutes"
    else:
            time_elapsed = str(time_elapsed) + " minute"

    return time_elapsed

@app.route('/getUserInfo')
def getUserInfo():
    try:
        token_info = get_token()
    except:
        print("user not logged in")
        return redirect(url_for("login", _external=False)) # redirects to login page

    sp = spotipy.Spotify(auth=token_info['access_token'])

    user_display_name = sp.current_user()["display_name"]
    current = sp.current_user_playing_track()
    if current is None: # if not currently playing anything, retrieves most recently played object
        recent = sp.current_user_recently_played(limit = 1)
        #int(time.time())
        now = datetime.utcnow() # retrieving current utc time
        print("now:", now)

        timestamp = recent["items"][0]["played_at"] # retrieving timestamp object
        print("timestamp:", timestamp)
        played_time = datetime.strptime(timestamp[0:19], '%Y-%m-%dT%H:%M:%S') # converting string to datetime object
        print("played_time:", played_time)

        time_elapsed = (now - played_time) # calculating time passed since last song played
        time_elapsed = (int(time_elapsed.total_seconds()) // 60 ) # converting to minutes
        time_elapsed = getTimeStr(time_elapsed)

        return user_display_name + " listened to " + recent["items"][0]["track"]["name"] + " by " + recent["items"][0]["track"]["artists"][0]["name"] + " " + time_elapsed + " ago."
    elif not current["is_playing"]:
        now = int(time.time())
        timestamp = current["timestamp"] // 1000
        print("timestamp:", timestamp)
        print("now:", now)
        time_elapsed = (now - timestamp) // 60
        print("time elapsed:", time_elapsed)
        time_elapsed = getTimeStr(time_elapsed)
        print(time_elapsed)
        return user_display_name + " listened to " + current["item"]["name"] + " by " + current["item"]["artists"][0]["name"] + " " + time_elapsed + " ago."

    return user_display_name + " is listening to " + current["item"]["name"] + " by " + current["item"]["artists"][0]["name"] + "."

'''
checks if token info exists
if not, redirects user to login
if it does, checks if token info expired,
if not, returns token
if so, retrieves refesh token
'''
def get_token():
    token_info = session.get(TOKEN_INFO, None)

    if not token_info: # if token_info doesn't exist
        raise 'exception'

    # checks if token is expired
    now = int(time.time())
    is_expired = token_info['expires_at'] - now < 60
    if is_expired:
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])

    return token_info

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id= "86124f4dcd8246639526dfc7105016e9",
        client_secret="0fd17b71370844f5920ab205e5a54347", # environmental variable, move to gitignore or backend
        redirect_uri=url_for('callback', _external=True),
        scope="user-read-recently-played, user-read-private, user-read-currently-playing" # privilege - 
    )