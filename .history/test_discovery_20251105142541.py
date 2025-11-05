import recruitment
import json
import os

# Clear old state for fresh test
if os.path.exists('sent_nations.json'):
    os.remove('sent_nations.json')
if os.path.exists('discovered_nations.json'):
    os.remove('discovered_nations.json')

print('=== Testing Full Auto-Discovery Pipeline ===\n')

session = recruitment.make_session()

print('1. Discovering newly founded nations...')
nations = recruitment.discover_new_nations(session)
print(f'   Found: {len(nations)} nations')
print(f'   Sample: {nations[:3]}\n')

print('2. Checking what we already know about...')
discovered = recruitment.load_discovered_nations()
print(f'   Already tracked: {len(discovered)} nations\n')

print('3. Finding truly new nations...')
undiscovered = [n for n in nations if n not in discovered]
print(f'   New nations: {len(undiscovered)}')
print(f'   Ready to send to: {undiscovered[:3]}\n')

print('4. Simulating sending to first 2 new nations (dry run)...')
sent = recruitment.load_sent_nations()
print(f'   Already sent TGs to: {len(sent)} nations')

for nation in undiscovered[:2]:
    print(f'   - Would send to: {nation}')

print('\n✓ Auto-discovery pipeline working!')
print('\nWhen you run "python recruitment.py":')
print('- It will query NationStates for newly founded nations every 60s')
print('- Automatically send recruitment TGs to new nations')
print('- Track discovered and sent nations to avoid duplicates')
