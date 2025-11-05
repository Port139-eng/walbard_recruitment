import requests
import time

CLIENT_KEY = "f1db6341"  # your new client key
TGID = "36674241"         # your recruitment telegram ID
SECRET_KEY = "41414cbef296"  # your secret key
USER_AGENT = "RecruitBot (by Ephraim)"  

# List of nations to send telegrams to
targets = ["nation1", "nation2", "nation3"]  # replace with actual targets

def send_tg(nation):
    url = f"https://www.nationstates.net/cgi-bin/api.cgi"
    payload = {
        "a": "sendTG",
        "client": CLIENT_KEY,
        "tgid": TGID,
        "key": SECRET_KEY,
        "to": nation
    }
    headers = {"User-Agent": USER_AGENT}
    response = requests.post(url, data=payload, headers=headers)
    print(f"Sent TG to {nation}: {response.text}")

# Send telegrams with safe timing
for nation in targets:
    send_tg(nation)
    time.sleep(180)  # 3 minutes per telegram (recruitment API limit)
