AI CRYPTO ANALYSIS WEBSITE — SETUP

1) ZIP ko extract karein.
2) GitHub par login karke New repository banayein.
3) Extract kiye gaye folder ke andar ki sab files GitHub repository mein upload karein.
   app.py, requirements.txt, Procfile, render.yaml aur templates/index.html zaroor upload hon.
4) Render.com par login karein, New > Web Service chunein, aur GitHub repository connect karein.
5) Build Command: pip install -r requirements.txt
6) Start Command: gunicorn app:app
7) Deploy par click karein. Deploy complete hone par Render aapko public onrender.com link dega.

LOCAL TEST:
  python -m venv venv
  venv\Scripts\activate
  pip install -r requirements.txt
  python app.py
Browser mein http://127.0.0.1:5000 kholein.

IMPORTANT:
- Ye app Delta Exchange India ke public market-data endpoints use karti hai.
- Ismein API key/secret ki zaroorat nahi hai aur koi order place nahi hota.
- Live ticker price aur 4-hour candle based EMA/RSI signal alag cheezein hain.
- Hosting provider ke free plan mein sleep/availability limits ho sakti hain.
- Signal guaranteed profit ya financial advice nahi hai.
