import os
import flask
from flask import Flask, redirect, request, session, url_for, render_template_string

# کتابخانه‌های گوگل
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# این میدل‌ور برای اجرای صحیح HTTPS در Replit ضروری است
from werkzeug.middleware.proxy_fix import ProxyFix

# --- پیکربندی اولیه برنامه ---
app = Flask(__name__)
# برای استفاده از session در Flask، حتما باید یک secret_key تنظیم شود
# بهتر است این مقدار را در بخش "Secrets" در Replit ذخیره کنید
# برای مثال: SECRET_KEY = os.environ['MY_SECRET_KEY']
app.secret_key = 'a-very-secret-key-change-it-later'

# اعمال میدل‌ور ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# --- تنظیمات مربوط به API گوگل ---
# نام فایل JSON که از کنسول گوگل دانلود کرده‌اید
CLIENT_SECRETS_FILE = "client_secrets.json"
# سطح دسترسی مورد نیاز (در اینجا: فقط خواندن فایل‌های گوگل درایو)
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
# آدرس کامل callback که در کنسول گوگل هم وارد کرده‌اید
REDIRECT_URI = 'https://ahourai-assistant.omid.repl.co/oauth2callback'

# یک تابع کمکی برای تبدیل آبجکت credentials به دیکشنری قابل ذخیره در session
def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}

# --- تعریف روت‌ها (صفحات برنامه) ---

@app.route('/')
def index():
    """صفحه اصلی که لینک لاگین را نمایش می‌دهد."""
    return """
    <h1>پروژه اهورایی - تست اتصال به گوگل درایو</h1>
    <p>برای شروع، لطفاً با حساب گوگل خود وارد شوید.</p>
    <a href="/authorize"><button>ورود با گوگل</button></a>
    """

@app.route('/authorize')
def authorize():
    """کاربر را برای احراز هویت به گوگل هدایت می‌کند."""
    # ساخت آبجکت Flow برای اپلیکیشن تحت وب
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)

    # تنظیم redirect_uri به صورت دستی تا اطمینان حاصل شود آدرس درست ارسال می‌شود
    flow.redirect_uri = REDIRECT_URI

    # ساخت URL برای صفحه لاگین گوگل
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')

    # ذخیره state در session برای امنیت
    session['state'] = state

    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    """
    این روت پس از تایید کاربر توسط گوگل فراخوانی می‌شود.
    کد احراز هویت را با توکن دسترسی (access token) تعویض می‌کند.
    """
    # بررسی state برای جلوگیری از حملات CSRF
    state = session['state']

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state)
    flow.redirect_uri = REDIRECT_URI

    # استفاده از URL کامل بازگشتی برای دریافت توکن
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    # ذخیره کردن credentials در session برای استفاده‌های بعدی
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

    return redirect(url_for('list_files'))

@app.route('/drive/files')
def list_files():
    """یک صفحه محافظت شده که لیست فایل‌های گوگل درایو را نمایش می‌دهد."""
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    # بازیابی credentials از session
    credentials = Credentials(**session['credentials'])

    try:
        # ساخت سرویس API گوگل درایو
        drive_service = build('drive', 'v3', credentials=credentials)

        # دریافت لیست ۱۰ فایل اول
        results = drive_service.files().list(
            pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])

        if not items:
            return 'هیچ فایلی در گوگل درایو شما یافت نشد.'

        # نمایش لیست فایل‌ها
        file_list_html = "<h1>لیست فایل‌های شما در گوگل درایو:</h1><ul>"
        for item in items:
            file_list_html += f"<li>{item['name']} (ID: {item['id']})</li>"
        file_list_html += "</ul><br><a href='/logout'>خروج</a>"
        return file_list_html

    except HttpError as error:
        return f'خطایی رخ داد: {error}'
    except Exception as e:
        # اگر توکن منقضی شده باشد یا مشکلی پیش بیاید، کاربر را مجدد به صفحه لاگین بفرست
        return redirect(url_for('authorize'))


@app.route('/logout')
def logout():
    """پاک کردن session و خروج کاربر."""
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
