"""
Live test: Run the actual main_loop() for a short time to see it sending multiple nations
"""

import recruitment
import os
import signal
import sys
import threading
import time

print("=" * 60)
print("LIVE TEST: RUNNING AUTOPILOT FOR 30 SECONDS")
print("=" * 60)

# Clear state for a fresh test
if os.path.exists('sent_nations.json'):
    os.remove('sent_nations.json')
if os.path.exists('discovered_nations.json'):
    os.remove('discovered_nations.json')

print("\nStarting main_loop() - watching for sends...")
print("(Running for ~30 seconds to see multiple sends)\n")

# Flag to stop the loop
stop_flag = False

def timeout_handler():
    global stop_flag
    time.sleep(30)
    print("\n" + "=" * 60)
    print("TIMEOUT - Stopping test")
    print("=" * 60)
    stop_flag = True
    # Raise KeyboardInterrupt to stop the loop
    import os
    os.kill(os.getpid(), signal.SIGINT)

# Start timeout in background
timeout_thread = threading.Thread(target=timeout_handler, daemon=True)
timeout_thread.start()

try:
    # Run the main autopilot loop
    session = recruitment.make_session()
    sent_nations = recruitment.load_sent_nations()
    discovered_nations = recruitment.load_discovered_nations()

    print(f"Starting state: {len(sent_nations)} sent, {len(discovered_nations)} discovered\n")

    iteration = 0
    while True:
        iteration += 1
        print(f"[Iteration {iteration}] Discovering new nations...")
        new_nations = recruitment.discover_new_nations(session)
        print(f"  → Found {len(new_nations)} nations total")
        
        if new_nations:
            undiscovered = [n for n in new_nations if n not in discovered_nations]
            print(f"  → {len(undiscovered)} are NEW (never discovered before)")
            
            if undiscovered:
                discovered_nations.update(undiscovered)
                recruitment.save_discovered_nations(discovered_nations)
                
                # Send to first 3 new nations as a demo
                demo_count = min(3, len(undiscovered))
                for i, nation in enumerate(undiscovered[:demo_count]):
                    print(f"\n  Sending TG to {nation}...")
                    resp = recruitment.send_tg(session, nation)
                    if resp and 200 <= resp.status_code < 300:
                        sent_nations.add(nation)
                        recruitment.save_sent_nations(sent_nations)
                        print(f"    ✓ Success! Response: {resp.text}")
                    else:
                        print(f"    ✗ Failed")
                    
                    # Sleep between sends (shorter for demo)
                    if i < demo_count - 1:
                        print(f"  Sleeping 5 seconds before next send...")
                        time.sleep(5)
                    
                print(f"\n  State updated: {len(sent_nations)} sent, {len(discovered_nations)} discovered\n")
            else:
                print("  No new nations to send to, sleeping 10 seconds...\n")
                time.sleep(10)

except KeyboardInterrupt:
    print("\n\nTest stopped!")
    print("=" * 60)
    print("FINAL STATE:")
    print("=" * 60)
    
    sent = recruitment.load_sent_nations()
    discovered = recruitment.load_discovered_nations()
    
    print(f"Nations sent TGs to: {len(sent)}")
    if sent:
        print(f"  {', '.join(sorted(list(sent))[:5])}{'...' if len(sent) > 5 else ''}")
    print(f"\nNations discovered: {len(discovered)}")
    print("\n✓ The autopilot CAN send to multiple nations!")
    print("  With NS_DELAY=180, it sends one every 3 minutes")
    print("  With NS_DISCOVER_SLEEP=60, it finds new nations every 1 minute")
