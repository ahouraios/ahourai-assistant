    import os
    from flask import Flask, redirect, url_for, session, request
    from werkzeug.middleware.proxy_fix import ProxyFix
    from authlib.integrations.flask_client import OAuth

    # پیکربندی Flask
    app = Flask(__name__)
    # SECRET_KEY برای امن کردن session استفاده می‌شود. حتماً در Render تنظیم شود.
    app.secret_key = os.environ.get("SECRET_KEY", "a_default_dev_secret_key_that_is_long_and_random")

    # اعمال ProxyFix برای تشخیص درست پروتکل (HTTPS) و میزبان در پشت پروکسی Render
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    # تنظیمات OAuth با خواندن از متغیرهای محیطی
    oauth = OAuth(app)
    google = oauth.register(
        name='google',
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        access_token_url='https://accounts.google.com/o/oauth2/token',
        access_token_params=None,
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        authorize_params=None,
        api_base_url='https://www.googleapis.com/oauth2/v1/',
        # اسکوپ‌ها: openid, email, profile اطلاعات پایه کاربر را درخواست می‌کنند
        client_kwargs={'scope': 'openid email profile'},
        # نام سرور برای فراخوانی‌های بعدی
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
    )

    @app.route('/')
    def index():
        user = session.get('user')
        if user:
            return f'سلام {user["name"]}! <br> ایمیل: {user["email"]} <br><a href="/logout">خروج</a>'
        return '<h1>پروژه اهورایی</h1><a href="/login">ورود با گوگل</a>'

    @app.route('/login')
    def login():
        # آدرس بازگشت (callback) را به صورت داینامیک و با پروتکل صحیح تولید می‌کنیم
        redirect_uri = url_for('auth', _external=True)
        return google.authorize_redirect(redirect_uri)

    @app.route('/auth')
    def auth():
        # دریافت توکن دسترسی از گوگل
        token = google.authorize_access_token()
        # دریافت اطلاعات کاربر با استفاده از توکن
        user_info = google.parse_id_token(token)
        # ذخیره اطلاعات کاربر در session
        session['user'] = user_info
        return redirect('/')

    @app.route('/logout')
    def logout():
        # پاک کردن اطلاعات کاربر از session
        session.pop('user', None)
        return redirect('/')

    if __name__ == '__main__':
        # این بخش فقط در زمان اجرای محلی (local) استفاده می‌شود
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port, debug=True)
