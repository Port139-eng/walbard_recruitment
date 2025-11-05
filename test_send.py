import recruitment
import os

print('=== Checking Configuration ===')
print(f'NS_CLIENT_KEY set: {bool(os.getenv("NS_CLIENT_KEY"))}')
print(f'NS_TGID set: {bool(os.getenv("NS_TGID"))}')
print(f'NS_SECRET_KEY set: {bool(os.getenv("NS_SECRET_KEY"))}')

print('\n=== Loading Targets ===')
targets = recruitment.load_targets()
print(f'Targets: {targets}')

print('\n=== Checking State ===')
sent = recruitment.load_sent_nations()
print(f'Already sent: {sent}')

to_send = [n for n in targets if n not in sent]
print(f'Ready to send to: {to_send}')

if to_send:
    print('\n=== Attempting Send ===')
    session = recruitment.make_session()
    for nation in to_send:
        print(f'Sending to {nation}...')
        resp = recruitment.send_tg(session, nation)
        if resp:
            print(f'  Status: {resp.status_code}')
            print(f'  Response: {resp.text}')
            sent.add(nation)
            recruitment.save_sent_nations(sent)
            print(f'  Saved to state file')
        else:
            print(f'  FAILED')
else:
    print('\n!!! No nations to send to !!!')
