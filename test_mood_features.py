#!/usr/bin/env python3
"""
Test script for the new mood-based routine and todo list features.
This demonstrates the new functionality added to the MCP server.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the mcp-bearer-token directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'mcp-bearer-token'))

# Import classes from the MCP server file
try:
    from mcp_starter import RoutineGenerator, TodoManager, SongRecommendationEngine
except ImportError:
    print("⚠️  Could not import from mcp-starter.py")
    print("This test script demonstrates the functionality that's available in the MCP server.")
    print("Run the actual MCP server to use these features with the Puch AI platform.")
    sys.exit(1)

async def test_mood_detection():
    """Test mood detection functionality"""
    print("🧠 Testing Mood Detection:")
    print("-" * 40)
    
    test_texts = [
        "I'm feeling so happy and excited today!",
        "I'm really sad and down right now",
        "I'm so angry and frustrated with everything",
        "I'm pumped up and ready to take on the world!",
        "I'm feeling okay, just a normal day"
    ]
    
    for text in test_texts:
        mood = SongRecommendationEngine.analyze_mood(text)
        print(f"Text: '{text}'")
        print(f"Detected Mood: {mood}")
        print()

async def test_routine_generation():
    """Test mood-based routine generation"""
    print("📅 Testing Routine Generation:")
    print("-" * 40)
    
    moods = ["happy", "sad", "angry", "excited", "neutral"]
    
    for mood in moods:
        print(f"\n🌟 {mood.title()} Mood Routine:")
        routine = RoutineGenerator.generate_routine(mood, "morning")
        for i, activity in enumerate(routine, 1):
            priority_emoji = "❗" if activity['priority'] == 1 else "🔹" if activity['priority'] == 2 else "▪️"
            print(f"{priority_emoji} {i}. {activity['activity']} ({activity['duration']}min)")

async def test_todo_manager():
    """Test todo list functionality"""
    print("\n📝 Testing Todo List Manager:")
    print("-" * 40)
    
    # Create a todo manager instance
    todo_manager = TodoManager()
    
    # Add some todos
    print("Adding todos...")
    todo1 = todo_manager.add_todo("Complete project proposal", priority=1, due_date="2025-08-15")
    todo2 = todo_manager.add_todo("Call dentist for appointment", priority=2)
    todo3 = todo_manager.add_todo("Organize closet", priority=3, due_date="2025-08-20")
    
    print(f"Added: {todo1['task']} (ID: {todo1['id']})")
    print(f"Added: {todo2['task']} (ID: {todo2['id']})")
    print(f"Added: {todo3['task']} (ID: {todo3['id']})")
    
    # View todos
    print("\n📋 Current Todo List:")
    todos = todo_manager.get_todos()
    for todo in todos:
        priority_emoji = "❗" if todo['priority'] == 1 else "🔹" if todo['priority'] == 2 else "▪️"
        due_text = f" (Due: {todo['due_date']})" if todo['due_date'] else ""
        print(f"{priority_emoji} ID {todo['id']}: {todo['task']}{due_text}")
    
    # Complete a todo
    print(f"\nCompleting todo ID {todo2['id']}...")
    todo_manager.complete_todo(todo2['id'])
    
    # View high priority todos
    print("\n❗ High Priority Todos:")
    high_priority = todo_manager.get_todos_by_priority(1)
    for todo in high_priority:
        print(f"ID {todo['id']}: {todo['task']}")
    
    print("\n✅ Todo Manager test completed!")

async def demo_mood_routine_workflow():
    """Demonstrate a complete mood-to-routine workflow"""
    print("\n🚀 Complete Mood-Based Routine Workflow Demo:")
    print("=" * 50)
    
    # Simulate user input
    user_mood_text = "I'm feeling really excited and energetic today! I want to be productive!"
    
    print(f"User says: '{user_mood_text}'")
    
    # Detect mood
    detected_mood = SongRecommendationEngine.analyze_mood(user_mood_text)
    print(f"Detected mood: {detected_mood}")
    
    # Generate routine
    print(f"\n📅 Generated {detected_mood} routine:")
    routine = RoutineGenerator.generate_routine(detected_mood, "full_day")
    
    current_time = datetime.strptime("08:00", "%H:%M")
    for activity in routine[:6]:  # Show first 6 activities
        end_time = current_time + timedelta(minutes=activity['duration'])
        priority_emoji = "❗" if activity['priority'] == 1 else "🔹" if activity['priority'] == 2 else "▪️"
        print(f"{priority_emoji} {current_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} ({activity['duration']}min): {activity['activity']}")
        current_time = end_time + timedelta(minutes=5)
    
    # Get song recommendations
    print(f"\n🎵 Song recommendations for {detected_mood} mood:")
    songs = SongRecommendationEngine.get_recommendations(detected_mood, 3)
    for i, song in enumerate(songs, 1):
        print(f"{i}. {song['title']} by {song['artist']}")

if __name__ == "__main__":
    print("🔬 Testing Enhanced Schedule Generator Features")
    print("=" * 60)
    
    asyncio.run(test_mood_detection())
    asyncio.run(test_routine_generation())
    asyncio.run(test_todo_manager())
    asyncio.run(demo_mood_routine_workflow())
    
    print("\n🎉 All tests completed successfully!")
    print("\nNew features available in MCP server:")
    print("1. 🌟 generate_mood_routine - Creates mood-based daily routines")
    print("2. 📝 manage_todo_list - Full todo list management")
    print("3. 📅 Enhanced generate_schedule - Now includes mood integration")
    print("4. 🎵 recommend_songs - Already existed, works with mood detection")
