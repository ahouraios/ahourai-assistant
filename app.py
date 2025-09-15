import os
import json
from flask import Flask, redirect, request, session, url_for
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# از یک متغیر محیطی برای کلید مخفی استفاده می‌کنیم
app.secret_key = os.environ.get("SECRET_KEY")
# برای مدیریت پروکسی در Render
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# این متغیرها ثابت می‌مانند
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
API_SERVICE_NAME = 'drive'
API_VERSION = 'v2'

# --- تغییر کلیدی ۱: خواندن اطلاعات از متغیر محیطی ---
# محتوای JSON را از متغیر محیطی که در Render تنظیم کردیم می‌خوانیم
client_secrets_content = os.environ.get('CLIENT_SECRETS_JSON')

# بررسی می‌کنیم که آیا متغیر محیطی وجود دارد یا نه
if not client_secrets_content:
    raise ValueError("Missing CLIENT_SECRETS_JSON environment variable")

# رشته JSON را به یک دیکشنری پایتون تبدیل می‌کنیم
client_config = json.loads(client_secrets_content)

@app.route('/')
def index():
    if 'credentials' not in session:
        return '<a href="/authorize">Login with Google</a>'
    
    credentials = Credentials(**session['credentials'])
    drive = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    files = drive.files().list().execute()
    
    file_list = "<ul>"
    for item in files.get('items', []):
        file_list += f"<li>{item['title']} ({item['id']})</li>"
    file_list += "</ul>"
    
    return f'You are logged in. <br>Files in your Drive:<br>{file_list}'

@app.route('/authorize')
def authorize():
    # --- تغییر کلیدی ۲: استفاده از from_client_config به جای from_client_secrets_file ---
    # ما دیگر از فایل استفاده نمی‌کنیم، بلکه از دیکشنری که از متغیر محیطی ساختیم
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')

    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    
    # --- تغییر کلیدی ۳: اینجا هم از from_client_config استفاده می‌کنیم ---
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    
    flow.fetch_token(authorization_response=request.url)
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

@app.route('/logout')
def logout():
    session.pop('credentials', None)
    return 'You have been logged out. <a href="/">Login again</a>'

# این بخش برای اجرای محلی است و در Render استفاده نمی‌شود
if __name__ == '__main__':
    # توجه: برای اجرای محلی، باید متغیرهای محیطی را تنظیم کنید
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run('localhost', 8080, debug=True)
