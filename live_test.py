"""
Live test: Actually discover and send to a real newly founded nation
"""

import recruitment
import time

print("=" * 60)
print("LIVE TEST: AUTO-DISCOVERING AND SENDING")
print("=" * 60)

# Clear state for a fresh test
import os
if os.path.exists('sent_nations.json'):
    os.remove('sent_nations.json')
if os.path.exists('discovered_nations.json'):
    os.remove('discovered_nations.json')

session = recruitment.make_session()

print("\n[1] Discovering newly founded nations...")
nations = recruitment.discover_new_nations(session)
print(f"✓ Discovered {len(nations)} nations")

print("\n[2] Filtering for brand new nations...")
discovered = recruitment.load_discovered_nations()
undiscovered = [n for n in nations if n not in discovered]
print(f"✓ Found {len(undiscovered)} NEW nations")
print(f"   First 3: {', '.join(undiscovered[:3])}")

if undiscovered:
    target = undiscovered[0]
    print(f"\n[3] SENDING RECRUITMENT TG TO: {target}")
    print("-" * 60)
    
    resp = recruitment.send_tg(session, target)
    
    if resp:
        print(f"✓ SUCCESS!")
        print(f"   Status Code: {resp.status_code}")
        print(f"   Response: {resp.text}")
        
        # Save to state
        discovered.update(undiscovered)
        recruitment.save_discovered_nations(discovered)
        
        sent = recruitment.load_sent_nations()
        sent.add(target)
        recruitment.save_sent_nations(sent)
        
        print(f"\n✓ Saved to state files")
        print(f"   discovered_nations.json: {len(discovered)} nations")
        print(f"   sent_nations.json: {len(sent)} nations")
        
        print("\n" + "=" * 60)
        print("LIVE TEST SUCCESSFUL!")
        print("=" * 60)
        print(f"\nTelegram sent to: {target}")
        print("Check your telegram log on NationStates to verify delivery!")
    else:
        print("✗ FAILED to send")
else:
    print("No new nations to send to")
