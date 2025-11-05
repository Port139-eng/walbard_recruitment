"""
Quick demo of the auto-discovery recruitment autopilot.
Shows what it will do when you run: python recruitment.py
"""

import recruitment

print("=" * 60)
print("RECRUITMENT AUTOPILOT - AUTO-DISCOVERY DEMO")
print("=" * 60)

session = recruitment.make_session()

print("\n[STEP 1] Discovering newly founded nations from NationStates API...")
nations = recruitment.discover_new_nations(session)
print(f"✓ Found {len(nations)} newly founded nations")
print(f"  Sample: {', '.join(nations[:5])}")

print("\n[STEP 2] Checking state files...")
sent = recruitment.load_sent_nations()
discovered = recruitment.load_discovered_nations()
print(f"✓ Already sent TGs to: {len(sent)} nations")
print(f"✓ Already discovered: {len(discovered)} nations")

print("\n[STEP 3] Finding NEW nations to recruit...")
new_nations = [n for n in nations if n not in discovered]
print(f"✓ Found {len(new_nations)} brand new nations!")
print(f"  Ready to send to: {', '.join(new_nations[:3])}")

print("\n[STEP 4] What happens next...")
print("  → Send recruitment TG to first new nation")
print("  → Wait 180 seconds")
print("  → Send TG to next new nation")
print("  → Repeat until all new nations receive TGs")
print("  → Every 60 seconds, check for MORE new nations")
print("  → 24/7 continuous recruitment!")

print("\n" + "=" * 60)
print("TO START THE AUTOPILOT, RUN:")
print("  python recruitment.py")
print("=" * 60)
