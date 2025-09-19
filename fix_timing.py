#!/usr/bin/env python3

# Read the current conversation demo file
with open('examples/conversation_demo.py', 'r') as f:
    content = f.read()

# Fix the timing issues
# 1. Make the real-time communication section longer and more consistent
old_realtime = '''    # Let the agents communicate for a while with periodic updates
    for i in range(15):  # 15 seconds total
        await asyncio.sleep(1)
        if i % 3 == 0:  # Update every 3 seconds
            print(f"⏱️  {15-i} seconds remaining...")'''

new_realtime = '''    # Let the agents communicate for a while with periodic updates
    print("⏱️  Agents will communicate for 30 seconds...")
    for i in range(30):  # 30 seconds total (doubled the time)
        await asyncio.sleep(1)
        if i % 5 == 0:  # Update every 5 seconds
            print(f"⏱️  {30-i} seconds remaining...")'''

content = content.replace(old_realtime, new_realtime)

# 2. Add more consistent delays between major steps
# Add delay after starting real-time communication
old_start_realtime = '''    # Start message processing for both agents
    procurement_task = asyncio.create_task(procurement_agent.process_messages())
    supplier_task = asyncio.create_task(supplier_agent.process_messages())'''

new_start_realtime = '''    # Start message processing for both agents
    procurement_task = asyncio.create_task(procurement_agent.process_messages())
    supplier_task = asyncio.create_task(supplier_agent.process_messages())
    
    # Give agents time to start processing
    await asyncio.sleep(3)'''

content = content.replace(old_start_realtime, new_start_realtime)

# 3. Add delay before final status check
old_final_status = '''    # Step 6: Final status
    print("\n📊 Step 6: Final Status Check...")'''

new_final_status = '''    # Step 6: Final status
    print("\n📊 Step 6: Final Status Check...")
    await asyncio.sleep(2)  # Brief pause before final status'''

content = content.replace(old_final_status, new_final_status)

# 4. Fix the step-by-step demo timing too
old_step_by_step_realtime = '''    # Let agents communicate for a while
    for i in range(20):  # 20 seconds
        await asyncio.sleep(1)
        if i % 5 == 0:
            print(f"⏱️  {20-i} seconds remaining...")'''

new_step_by_step_realtime = '''    # Let agents communicate for a while
    print("⏱️  Agents will communicate for 45 seconds...")
    for i in range(45):  # 45 seconds (more time for step-by-step)
        await asyncio.sleep(1)
        if i % 5 == 0:
            print(f"⏱️  {45-i} seconds remaining...")'''

content = content.replace(old_step_by_step_realtime, new_step_by_step_realtime)

# Write the updated content
with open('examples/conversation_demo.py', 'w') as f:
    f.write(content)

print("Fixed timing issues in conversation demo!")
