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

## Deployment to Appwrite

The repository ships an `appwrite.json` that the [Appwrite CLI](https://appwrite.io/docs/tooling/command-line/installation) uses to create and deploy the function.

### Quick deploy (copy/paste)

```bash
npm install -g appwrite-cli
appwrite client --endpoint https://cloud.appwrite.io/v1
appwrite login
# set your Appwrite project id in appwrite.json (replace YOUR_PROJECT_ID)
appwrite deploy function
```

### How it works on Appwrite

Because Appwrite Functions are short-lived, the infinite loop from `recruitment.py` is replaced by `main.py` — a single-execution entry point.  A **cron schedule of every 2 minutes** (`*/2 * * * *`, set in `appwrite.json`) calls the function repeatedly, mirroring the original 120-second delay between sends:

| Each execution | Action |
|---|---|
| Discovers all newly founded nations | Queries NationStates API |
| Finds the first unseen eligible nation | Applies regional campaign filter if active |
| Sends **one** recruitment telegram | Returns result JSON |
| Saves updated state | To Appwrite Storage (or local FS if not configured) |

### Step 1 — Install the Appwrite CLI

```bash
npm install -g appwrite-cli
```

### Step 2 — Log in and initialise

```bash
appwrite client --endpoint https://cloud.appwrite.io/v1
appwrite login
```

Edit `appwrite.json` and replace `YOUR_PROJECT_ID` with your actual Appwrite project ID.

### Step 3 — Create a Storage bucket for persistent state (recommended)

In the Appwrite Console go to **Storage → Create Bucket**.  Note the bucket ID.

Without a bucket, state files are ephemeral (reset each execution); the bot will still work but may re-send telegrams to already-recruited nations after a cold start.

### Step 4 — Deploy the function

```bash
appwrite deploy function
```

Select `recruitment-bot` when prompted.

### Step 5 — Set environment variables in the Appwrite Console

Navigate to **Functions → recruitment-bot → Settings → Variables** and add:

| Variable | Required | Description |
|---|---|---|
| `NS_CLIENT_KEY` | ✅ | NationStates API client key |
| `NS_TGID` | ✅ | Telegram ID in your nation |
| `NS_SECRET_KEY` | ✅ | NationStates API secret |
| `NS_USER_AGENT` | | User-Agent header (default: `WalbardRecruitBot`) |
| `NS_DELAY` | | Seconds between sends (default: `120`) |
| `NS_DISCOVER_SLEEP` | | Polling interval in seconds (default: `60`) |
| `APPWRITE_BUCKET_ID` | | Storage bucket ID for persistent state |
| `APPWRITE_API_KEY` | | Appwrite API key with `storage.read` + `storage.write` scopes |

> **Tip**: `APPWRITE_FUNCTION_API_ENDPOINT` and `APPWRITE_FUNCTION_PROJECT_ID` are injected automatically by the Appwrite runtime — you do not need to set them manually.

### Step 6 — Enable the function

Toggle the function **enabled** in the Console, or it will start automatically on the next cron tick.

---

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

### Region Target Campaigns

- Define time-bound regional pushes in `region_targets.json` (or point `NS_REGION_CAMPAIGNS_FILE` to another JSON file).
- Each campaign entry accepts `tag`, `regions`, `starts_at`, and `ends_at` (ISO-8601, UTC). Omitting `starts_at` makes it live immediately; omitting `ends_at` keeps it running indefinitely.
- While at least one campaign is active, the autopilot fetches the region for every newly founded nation and only sends telegrams to those that match the listed regions. Non-matching nations are skipped (logged as such).
- Example payload shipped with this repo:

```json
{
   "campaigns": [
      {
         "tag": "britannia_push_2025w48",
         "regions": [
            "Britannia",
            "New United Kingdom",
            "Kingdom of Britannia"
         ],
         "starts_at": "2025-11-23T00:00:00Z",
         "ends_at": "2025-11-30T23:59:59Z"
      }
   ]
}
```

- Update the file in Railway (or set the env var to a remote path) whenever you need to retarget; the running process reloads it every discovery cycle.

## Troubleshooting

- **"Missing environment variables"**: Ensure NS_CLIENT_KEY, NS_TGID, NS_SECRET_KEY are set
- **"Failed to discover new nations"**: Check User-Agent and API connectivity
- **No telegrams sending**: Verify recruitment telegrams are enabled in your nation's preferences
- **Rate limiting**: Increase NS_DELAY or NS_DISCOVER_SLEEP
