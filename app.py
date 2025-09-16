import os
import json
from flask import Flask, redirect, url_for, session, request, jsonify
from authlib.integrations.flask_client import OAuth
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from werkzeug.middleware.proxy_fix import ProxyFix # <--- تغییر ۱: ایمپورت جدید

# Load client secrets from a file
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

app = Flask(__name__)
# Flask secret key required for session management
app.secret_key = os.urandom(24)

# تغییر ۲: این خط برای مدیریت صحیح HTTPS پشت پروکسی Render اضافه شده است
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

@app.route('/')
def index():
    if 'credentials' not in session:
        return '<a href="/login">Login with Google</a>'
    
    # Optional: You can show user info if they are already logged in
    # For now, let's just show a link to view files
    return 'Logged in. <a href="/drive/files">View Google Drive Files</a>'

@app.route('/login')
def login():
    # Create a flow instance to manage the OAuth 2.0 Authorization flow.
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )

    # The url_for('oauth2callback', _external=True) generates the absolute callback URL.
    # _external=True is crucial for generating a full URL like https://.../oauth2callback
    # ProxyFix ensures that this URL uses https instead of http.

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )

    # Store the state so we can verify it in the callback
    session['state'] = state
    
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    # Verify the state to protect against CSRF attacks
    state = session.pop('state', None)
    if not state or state != request.args.get('state'):
        return 'State mismatch error', 400

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )

    # Exchange the authorization code for an access token
    flow.fetch_token(authorization_response=request.url)
    
    # Store the credentials in the session
    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

    return redirect(url_for('index'))


@app.route('/drive/files')
def drive_files():
    if 'credentials' not in session:
        return redirect(url_for('login'))

    # Load credentials from the session
    creds = Credentials(**session['credentials'])

    try:
        # Build the Google Drive service
        service = build('drive', 'v3', credentials=creds)

        # Call the Drive v3 API
        results = service.files().list(
            pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])

        if not items:
            return "No files found."
        
        # Create a simple list of file names
        file_list = "Files:<br>" + "<br>".join([f"{file['name']} (ID: {file['id']})" for file in items])
        return file_list

    except Exception as e:
        return f"An error occurred: {e}"


@app.route('/logout')
def logout():
    session.pop('credentials', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    # This block is for local development. 
    # Render uses the 'gunicorn' command and ignores this.
    # We ensure it listens on all IPs and gets the port from the environment.
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
