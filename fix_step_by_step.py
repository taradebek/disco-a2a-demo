#!/usr/bin/env python3

# Read the current conversation demo file
with open('examples/conversation_demo.py', 'r') as f:
    content = f.read()

# Fix the step-by-step demo timing
old_step_by_step = '''    # Let it run for a while
    print("Agents are now communicating...")
    await asyncio.sleep(10)'''

new_step_by_step = '''    # Let it run for a while
    print("⏱️  Agents will communicate for 45 seconds...")
    for i in range(45):  # 45 seconds (more time for step-by-step)
        await asyncio.sleep(1)
        if i % 5 == 0:
            print(f"⏱️  {45-i} seconds remaining...")'''

content = content.replace(old_step_by_step, new_step_by_step)

# Write the updated content
with open('examples/conversation_demo.py', 'w') as f:
    f.write(content)

print("Fixed step-by-step demo timing!")
