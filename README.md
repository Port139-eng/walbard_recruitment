# Recruitment Telegram Autopilot

A Railway-friendly infinite-loop autopilot for **automatically recruiting newly founded nations** in NationStates.

## Features

- **Auto-discovers newly founded nations**: Continuously queries NationStates API for new nations
- **Automatic recruitment**: Sends telegrams to every newly founded/refounded nation 24/7
- **Persistent state tracking**: Tracks discovered and sent nations to avoid duplicates across restarts
- **Resilient**: HTTPAdapter with exponential backoff on 429/5xx errors (3 retries)
- **Environment-driven**: All secrets via environment variables (no hardcoding)
- **Railway-ready**: Structured for Railway deployment with proper signal handling

## How It Works

1. **Every 60 seconds**: Queries the NationStates API for newly founded nations
2. **For each new nation**: Sends your recruitment telegram automatically
3. **Persistent tracking**: Saves state to `sent_nations.json` and `discovered_nations.json`
4. **180-second delays**: Respects API rate limits with delays between sends
5. **Survives restarts**: State persists across container/process restarts on Railway

## Setup

### 1. Install dependencies

```powershell
pip install -r requirements.txt
```

Or with a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure environment variables

Set these in your shell or Railway dashboard:

- `NS_CLIENT_KEY` - Your NationStates API client key (required)
- `NS_TGID` - Telegram ID in your nation (required)
- `NS_SECRET_KEY` - Your NationStates API secret (required)
- `NS_USER_AGENT` - User-Agent header (default: "WalbardRecruitBot")
- `NS_DELAY` - Seconds between telegram sends (default: 120, min: 60, max: 180)
- `NS_DISCOVER_SLEEP` - Seconds between polling for new nations (default: 60)

### 3. Run the autopilot

```powershell
python recruitment.py
```

The script will:
- Query NationStates every 60 seconds for newly founded nations
- Automatically send telegrams to each new nation
- Maintain state to track discovered/sent nations
- Sleep 180 seconds between sends to respect rate limits
- Press `Ctrl+C` to stop

## Testing

Run the test suite:

```powershell
python -m unittest tests.test_recruitment -v
```

Test the discovery feature:

```powershell
python test_discovery.py
```

Test sending to specific nations:

```powershell
python test_send.py
```

## Deployment to Railway

1. **Push to git**:
   ```powershell
   git add .
   git commit -m "Auto-discovery recruitment autopilot"
   git push
   ```

2. **Create Railway project** at https://railway.app/

3. **Set environment variables** in Railway dashboard:
   - `NS_CLIENT_KEY`
   - `NS_TGID`
   - `NS_SECRET_KEY`
   - `NS_DELAY` (optional, default 180)
   - `NS_DISCOVER_SLEEP` (optional, default 60)

4. **Railway will automatically run**: `python recruitment.py` and restart on crashes

## Architecture

### Core Functions

- **`discover_new_nations()`**: Queries NationStates API for newly founded nations
- **`send_tg()`**: Posts recruitment telegram to a specific nation
- **`make_session()`**: Creates requests.Session with retry/backoff logic
- **`main_loop()`**: Infinite loop that discovers, tracks, and sends to new nations

### State Files

- **`sent_nations.json`**: Track of nations already sent telegrams to
- **`discovered_nations.json`**: Track of all nations ever discovered (to avoid re-discovering)
- **`targets.txt`**: Optional manual target list (overridden by auto-discovery)

## Customization

### Rate Limiting (NS_DELAY)

Adjust delay between telegram sends. **All options are rate-limit safe:**

| Delay | Speed | Timeline for 50 nations | Notes |
|-------|-------|------------------------|-------|
| **60s** | ⚡ Fastest | ~50 min | Very respectful to API |
| **120s** | 👍 Default | ~100 min | Balanced speed/safety |
| **180s** | Conservative | ~150 min | Extra safe |

Example: Set faster rate for Railway:
```bash
# In Railway environment variables:
NS_DELAY=60
```

### Polling Frequency (NS_DISCOVER_SLEEP)

How often to check for newly founded nations:

- `60` (default): Check every 1 minute
- `30`: Check every 30 seconds (more responsive)
- `120`: Check every 2 minutes (less API calls)

## Troubleshooting

- **"Missing environment variables"**: Ensure NS_CLIENT_KEY, NS_TGID, NS_SECRET_KEY are set
- **"Failed to discover new nations"**: Check User-Agent and API connectivity
- **No telegrams sending**: Verify recruitment telegrams are enabled in your nation's preferences
- **Rate limiting**: Increase NS_DELAY or NS_DISCOVER_SLEEP
