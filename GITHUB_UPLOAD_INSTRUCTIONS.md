# How to add this to your GitHub repo (nova-cuts-ai-manager1)

## Option A — Upload via GitHub website
1) Go to your repo: github.com/novaquant215/nova-cuts-ai-manager1
2) Click **Add file → Upload files**.
3) Drag these files in:
   - `nova_cuts_ai_manager.py`
   - `requirements.txt` (merge with your existing if needed)
   - `.env.example` (do not put real secrets in Git — use Render/AWS env vars)
4) Commit directly to `main`.
5) Set your Render start command to:  
   `gunicorn nova_cuts_ai_manager:app --bind 0.0.0.0:$PORT`
6) Set environment variables in Render Dashboard using `.env.example` as a template.
7) In Twilio Console → Phone Numbers → Messaging → set webhook to:  
   `https://<your-render-app>.onrender.com/twilio/webhook`

## Option B — Command line (Terminal)
```bash
git clone git@github.com:novaquant215/nova-cuts-ai-manager1.git
cd nova-cuts-ai-manager1

# Copy the files from this package into the repo folder, then:
git add nova_cuts_ai_manager.py requirements.txt .env.example
git commit -m "Add Twilio SMS + smart marketing one-file app"
git push origin main
```

## Local test
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then edit with your Twilio creds
python nova_cuts_ai_manager.py
```

## API quick checks
```bash
# Send a test SMS
curl -X POST http://127.0.0.1:5000/sms/send   -H "Content-Type: application/json" -H "X-API-Key: supersecret"   -d '{"to":"+17035550123","body":"Test from NOVA Cuts ✅"}'

# Log a completed appointment (fires review/rebook flows)
curl -X POST http://127.0.0.1:5000/crm/appointment/log   -H "Content-Type: application/json" -H "X-API-Key: supersecret"   -d '{"phone":"+17035550123","start_time":"2025-09-09T15:30:00Z","end_time":"2025-09-09T16:05:00Z","service":"Haircut+Beard","status":"completed"}'
```

If you want this to be the **main app**, set your process to start with:  
`gunicorn nova_cuts_ai_manager:app --bind 0.0.0.0:$PORT`
