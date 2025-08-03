from fastapi import FastAPI, Request, Depends, HTTPException, Cookie
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse

import os
from dotenv import load_dotenv
import httpx
from baza import init_db, get_user, add_user
from jose import jwt, JWTError

# pip install "python-jose[cryptography]"
init_db()

load_dotenv()
app = FastAPI()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGO = "HS256"

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
BACK_URI = os.getenv("BACK_URI")

print(BACK_URI)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return """
    <html>
    <head><title>Moja Apka</title></head>
    <body>
    <h1>Witaj!</h1>
    <a href='/login'>Zaloguj się przez Google</a>
    </body>
    </html>
    """


@app.get("/login")
def login():
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&scope=openid%20email%20profile"
        "&access_type=offline"
    )
    print(google_auth_url)
    return RedirectResponse(google_auth_url)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(400, "Brak kodu OAuth2")

    # return "OK"
    # wymiana code na access_token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL,
                                       data={
                                           "client_id": CLIENT_ID,
                                           "client_secret": CLIENT_SECRET,
                                           "code": code,
                                           "grant_type": "authorization_code",
                                           "redirect_uri": REDIRECT_URI
                                       })

        token_data = token_resp.json()  # słownik
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(400, "Brak access token")

        # pobranie user info
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
        )

        userinfo = userinfo_resp.json()
        email = userinfo.get("email")
        print(email)
        if not email:
            raise HTTPException(400, "Brak e-mail w Google")

    token = jwt.encode({"sub": email}, JWT_SECRET, algorithm=JWT_ALGO)
    # return {"access_token": token, "user": userinfo}

    response = RedirectResponse(url="/me")
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600,
        samesite="lax"
    )
    return response


@app.get("/me", response_class=HTMLResponse)
def me(request: Request, access_token: str = Cookie(None)):
    if not access_token:
        return HTMLResponse(
            "<h2>Brak tokena - nie jesteś zalogowany.</h2><h2><a href='/'>Logowanie</a>", status_code=401)
    try:
        payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGO])
        user = payload.get("sub")
        user_in_db = get_user(user)
        is_new = False
        return f"""
        <html>
        <head><title>Konto</title></head>
        <body>
        <h1>Zalogowana jako: {user}</h1>
        <a href='/logout'>Wyloguj się</a>
        </body>
        </html>
        """
    except JWTError:
        return HTMLResponse(
            "<h1>Błąd tokena</h1><a href='/'>Logowanie</a>", status_code=401
        )


@app.get("/logout", response_class=HTMLResponse)
def logout(request: Request):
    return f"""
            <html>
            <head><title>wylogowano</title></head>
            <body>
            <h1>Wylogowano!</h1>
            <a href='/'>Powrót do strony głównej</a>
            </body>
            </html>
            """
