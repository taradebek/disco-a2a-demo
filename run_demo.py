#!/usr/bin/env python3
"""
A2A Agent Interaction Demo
==========================

This script demonstrates the complete A2A (Agent-to-Agent) protocol implementation
with real-time visualization for retail supply chain automation.

Usage:
    python3 run_demo.py [--dashboard-only] [--scenario-only] [--slow-demo] [--interactive]

Options:
    --dashboard-only    Start only the web dashboard
    --scenario-only     Run only the purchase scenario (no dashboard)
    --slow-demo         Run slow demo with pauses between steps
    --interactive       Run interactive demo where you control the pace
"""

import asyncio
import argparse
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def print_banner():
    """Print the demo banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                          A2A Agent Interaction Demo                        ║
║                                                                              ║
║  🤖 Agent-to-Agent Protocol Implementation                                  ║
║  📊 Real-time Dashboard & Visualization                                     ║
║  🛒 Retail Supply Chain Automation                                          ║
║                                                                              ║
║  This demo showcases two AI agents collaborating to purchase office         ║
║  supplies using the A2A protocol with real-time step-by-step visualization. ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import websockets
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def start_dashboard():
    """Start the web dashboard"""
    print("\n🌐 Starting A2A Dashboard...")
    print("   Dashboard will be available at: http://localhost:8000")
    print("   Press Ctrl+C to stop the dashboard")
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "dashboard.app:app", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped")

def run_scenario():
    """Run the purchase scenario"""
    print("\n🎬 Running Purchase Scenario...")
    
    try:
        from examples.purchase_scenario import run_purchase_scenario
        result = asyncio.run(run_purchase_scenario())
        print(f"\n📋 Scenario completed: {result}")
        return result
    except Exception as e:
        print(f"❌ Scenario failed: {e}")
        return None

def run_slow_demo():
    """Run the slow demo with pauses"""
    print("\n🐌 Running SLOW Demo...")
    print("   This demo pauses between each step so you can follow along!")
    print("   Make sure the dashboard is running at http://localhost:8000")
    
    try:
        from examples.slow_demo import run_slow_demo as slow_demo_func
        result = asyncio.run(slow_demo_func())
        print(f"\n📋 Slow demo completed: {result}")
        return result
    except Exception as e:
        print(f"❌ Slow demo failed: {e}")
        return None

def run_interactive_demo():
    """Run the interactive demo"""
    print("\n🎮 Running INTERACTIVE Demo...")
    print("   You control the pace! Press Enter after each step.")
    print("   Make sure the dashboard is running at http://localhost:8000")
    
    try:
        from examples.slow_demo import run_interactive_demo as interactive_demo_func
        asyncio.run(interactive_demo_func())
        return True
    except Exception as e:
        print(f"❌ Interactive demo failed: {e}")
        return None

def run_full_demo():
    """Run the complete demo with dashboard and scenario"""
    print("\n🚀 Starting Full Demo...")
    
    # Start dashboard in background
    dashboard_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "dashboard.app:app", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ])
    
    try:
        # Wait for dashboard to start
        print("⏳ Waiting for dashboard to start...")
        time.sleep(3)
        
        # Open browser
        print("🌐 Opening dashboard in browser...")
        webbrowser.open("http://localhost:8000")
        
        # Run scenario
        print("\n🎬 Starting purchase scenario...")
        result = run_scenario()
        
        if result:
            print("\n✅ Demo completed successfully!")
            print("📱 The dashboard is still running at http://localhost:8000")
            print("🔄 You can run the scenario again from the dashboard")
            
            # Keep dashboard running
            print("\nPress Ctrl+C to stop the dashboard...")
            dashboard_process.wait()
        else:
            print("❌ Demo failed")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping demo...")
    finally:
        dashboard_process.terminate()
        dashboard_process.wait()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="A2A Agent Interaction Demo")
    parser.add_argument("--dashboard-only", action="store_true", 
                       help="Start only the web dashboard")
    parser.add_argument("--scenario-only", action="store_true", 
                       help="Run only the purchase scenario")
    parser.add_argument("--slow-demo", action="store_true", 
                       help="Run slow demo with pauses between steps")
    parser.add_argument("--interactive", action="store_true", 
                       help="Run interactive demo where you control the pace")
    
    args = parser.parse_args()
    
    print_banner()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Run based on arguments
    if args.dashboard_only:
        start_dashboard()
    elif args.scenario_only:
        run_scenario()
    elif args.slow_demo:
        run_slow_demo()
    elif args.interactive:
        run_interactive_demo()
    else:
        run_full_demo()

if __name__ == "__main__":
    main()
