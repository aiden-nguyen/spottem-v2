from flask import Flask, request, url_for, session, redirect
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from datetime import datetime

app = Flask(__name__)

app.secret_key = "spottem"
app.config['SESSION_COOKIE_NAME'] = 'spottem cookie'
TOKEN_INFO = "token_info"

# Including the class here since importing it from outside was giving issues
# response: API call response in JSON format
# playing: boolean to determine if user is currently played a song or paused a song
class SongInfo:
    def __init__(self, response, playing = True):
        if playing: # user is currently playing a song
            # Song Information
            self.song_name = response["item"]["name"]
            self.artist_name = response["item"]["artists"][0]["name"]

            # Time Interval Variables
            self.last_played = 0 # UTC integer of time elapsed since user last played song
            self.time_started = response["timestamp"] // 1000 # Time the user started playing the song
            now = int(time.time())
            self.time_elapsed = self.getTimeStr((now - self.time_started) // 60)

            # User Status Variables
            self.is_playing = response["is_playing"] # determines if user is currently playing a song
            print(f"is_playing: {self.is_playing}")

            # Song Status
            self.current = playing

        else: # User has not played a song in a while
            # Song Information
            self.song_name = response["items"][0]["track"]["name"]
            self.artist_name = response["items"][0]["track"]["artists"][0]["name"]
            
            # Time Interval Variables
            self.time_started = response["items"][0]["played_at"]
            self.played_time = datetime.strptime(self.time_started[0:19], '%Y-%m-%dT%H:%M:%S') # converting string to datetime object
            now = datetime.utcnow()
            self.time_elapsed = self.getTimeStr(int((now - self.played_time).total_seconds()) // 60)

            # User Status Variables
            self.is_playing = False

            # song status
            self.current = not playing

    
    def updated_elapsed_time(self):
        if not self.current: # the song is pulled from current_user_recently_played
            now = datetime.utcnow()
            return self.getTimeStr(int((now - self.played_time).total_seconds()) // 60)
        else:
            now = int(time.time())
            self.time_elapsed = self.getTimeStr((now - self.time_started) // 60)

    def getTimeStr(self, time_elapsed):
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

    def get_details(self, username):
        if self.is_playing: # currently playing a song
            return f"{username} is listening to {self.song_name} by {self.artist_name}"
        else: # The user either paused the song or has not played any recently
            return f"{username} listened to {self.song_name} by {self.artist_name} {self.time_elapsed} ago."

    def print(self):
        print(f"{self.song_name} by {self.artist_name}, time elapsed: {self.time_elapsed}")

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

@app.route('/testing')
def testing():
    try:
        token_info = get_token()
    except:
        print("user not logged in")
        return redirect(url_for("login", _external=False)) # redirects to login page

@app.route('/getUserInfo')
def getUserInfo():

    try:
        token_info = get_token()
    except:
        print("user not logged in")
        return redirect(url_for("login", _external=False)) # redirects to login page
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    user_display_name = sp.current_user()["display_name"]
    
    response = sp.current_user_playing_track()
    
    print(f"Response None: {response is None}")

    if response is None: # if not currently playing anything, retrieves most recently played object
        recent = sp.current_user_recently_played(limit = 1)
        last_song = SongInfo(recent, playing = False)
        
        return last_song.get_details(user_display_name)

    curr_song = SongInfo(response)
    return curr_song.get_details(user_display_name)

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