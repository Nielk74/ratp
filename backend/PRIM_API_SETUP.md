# PRIM API Setup Guide

## Why PRIM API?

The community RATP API (`api-ratp.pierre-grimaud.fr`) is currently **unavailable/timing out**. To get **real-time traffic data**, you need to use the **official PRIM API** from Île-de-France Mobilités.

## Benefits of PRIM API

✅ **Official API** from Île-de-France Mobilités
✅ **Real-time traffic information** for all Paris transport lines
✅ **Free** with generous quota (20,000 requests/day)
✅ **Reliable** and maintained by IDFM
✅ **Comprehensive data** including incidents, disruptions, planned works

## How to Get Your Free API Key

### Step 1: Create an Account

1. Go to **https://prim.iledefrance-mobilites.fr**
2. Click **"S'inscrire"** (Sign up) or **"Créer un compte"**
3. Fill in your details:
   - Email
   - Password
   - Accept terms of service
4. **Verify your email** (check inbox/spam)

### Step 2: Generate API Token

1. **Login** to your PRIM account
2. Go to **"Mon compte"** (My Account) or **"Mes jetons d'authentification"** (My authentication tokens)
3. Navigate to the **"API"** tab
4. Click **"Générer mon jeton"** (Generate my token)
5. **Copy the token** - it will only be shown once!
6. **Save it securely** (you can't view it again later)

### Step 3: Configure Your Backend

Add the API key to your environment:

```bash
# Option 1: Export directly (temporary)
export PRIM_API_KEY="your_api_key_here"

# Option 2: Create .env file (recommended)
echo 'PRIM_API_KEY="your_api_key_here"' > .env

# Option 3: Add to shell profile (permanent)
echo 'export PRIM_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

### Step 4: Restart the Server

```bash
cd /data/data/com.termux/files/home/projects/ratp/backend
python main.py
```

### Step 5: Test the Traffic Endpoint

```bash
# Test traffic endpoint
curl http://localhost:8000/api/traffic/

# Test with specific line
curl http://localhost:8000/api/traffic/?line_code=1
```

## Expected Response with PRIM API

With the API key configured, you'll get **real traffic data**:

```json
{
  "status": "ok",
  "message": "Traffic data from PRIM API",
  "source": "prim_api",
  "timestamp": "2025-10-07T02:00:00",
  "data": {
    "line_reports": [
      {
        "line": {"code": "1", "name": "Métro 1"},
        "pt_objects": [...],
        "disruptions": [
          {
            "severity": "information",
            "cause": "Travaux programmés",
            "messages": [...]
          }
        ]
      }
    ]
  }
}
```

## Without API Key (Current State)

Without the PRIM API key, you'll get:

```json
{
  "status": "unavailable",
  "message": "Unable to fetch real-time traffic data. Please configure PRIM_API_KEY...",
  "source": "no_api_available",
  "help": {
    "prim_api_configured": false,
    "instructions": "To enable real-time traffic data, get a free API key from https://prim.iledefrance-mobilites.fr and set PRIM_API_KEY environment variable."
  }
}
```

## API Limits

- **Rate limit**: 20,000 requests per day
- **Quota tracking**: Automatically tracked in the backend
- **Caching**: Traffic data cached for 2 minutes (configurable)

## Troubleshooting

### "PRIM API rate limit exceeded"
- Wait until the next day (resets at midnight)
- Check `rate_limit_prim_traffic_per_day` in config

### "PRIM API error: ..."
- Verify your API key is correct
- Check https://prim.iledefrance-mobilites.fr for API status
- Review API documentation at PRIM portal

### Still showing "unavailable"
- Ensure `PRIM_API_KEY` is set: `echo $PRIM_API_KEY`
- Restart the server after setting the key
- Check server logs for error messages

## Additional Resources

- **PRIM Portal**: https://prim.iledefrance-mobilites.fr
- **API Documentation**: https://prim.iledefrance-mobilites.fr/en/aide-et-contact/documentation
- **Traffic API Docs**: https://prim.iledefrance-mobilites.fr/en/apis/idfm-navitia-line_reports-v2
- **Support**: Contact PRIM support through the portal

---

**Created**: 2025-10-07
**Last Updated**: 2025-10-07
**Status**: Required for real-time traffic data
