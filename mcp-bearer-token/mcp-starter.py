import asyncio
from typing import Annotated
import os
from dotenv import load_dotenv
import requests # Import for weather tool
from fastmcp.server import FastMCP # type: ignore
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair # type: ignore
from mcp import ErrorData, McpError
from mcp.server.auth.provider import AccessToken
from mcp.types import TextContent, ImageContent, INVALID_PARAMS, INTERNAL_ERROR
from pydantic import BaseModel, Field, AnyUrl
import tempfile
from datetime import datetime, timedelta
import re
from enum import Enum
import httpx

# --- Load environment variables ---
load_dotenv()

TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY") # ADDED

assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"

# --- Auth Provider ---
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(
                token=token,
                client_id="puch-client",
                scopes=["*"],
                expires_at=None,
            )
        return None

# --- Rich Tool Description model ---
class RichToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None = None

# --- MOOD-BASED ROUTINE AND TODO CLASSES ---
class Mood(Enum):
    HAPPY = "happy"
    SAD = "sad"
    NEUTRAL = "neutral"
    ANGRY = "angry"
    EXCITED = "excited"

class RoutineGenerator:
    """Generator for mood-based daily routines"""
    
    MOOD_ROUTINES = {
        "happy": {
            "morning": [
                {"activity": "Gratitude journaling", "duration": 10, "priority": 1},
                {"activity": "Energetic workout or dance", "duration": 30, "priority": 1},
                {"activity": "Healthy breakfast with favorite music", "duration": 20, "priority": 2},
                {"activity": "Plan exciting activities for the day", "duration": 15, "priority": 2}
            ],
            "afternoon": [
                {"activity": "Creative project or hobby", "duration": 60, "priority": 1},
                {"activity": "Social activity with friends/family", "duration": 45, "priority": 2},
                {"activity": "Outdoor walk or fresh air activity", "duration": 30, "priority": 2}
            ],
            "evening": [
                {"activity": "Share positive moments with others", "duration": 20, "priority": 1},
                {"activity": "Listen to upbeat music or watch comedy", "duration": 30, "priority": 2},
                {"activity": "Plan tomorrow's fun activities", "duration": 15, "priority": 3}
            ]
        },
        "sad": {
            "morning": [
                {"activity": "Gentle meditation or breathing exercises", "duration": 15, "priority": 1},
                {"activity": "Light stretching or gentle yoga", "duration": 20, "priority": 1},
                {"activity": "Nutritious comfort breakfast", "duration": 25, "priority": 2},
                {"activity": "Journal feelings or call a friend", "duration": 20, "priority": 2}
            ],
            "afternoon": [
                {"activity": "Self-care activity (bath, skincare, etc.)", "duration": 45, "priority": 1},
                {"activity": "Watch uplifting content or read", "duration": 60, "priority": 2},
                {"activity": "Nature walk or sit in sunlight", "duration": 30, "priority": 2}
            ],
            "evening": [
                {"activity": "Connect with supportive people", "duration": 30, "priority": 1},
                {"activity": "Gentle evening routine", "duration": 20, "priority": 2},
                {"activity": "Practice self-compassion exercises", "duration": 15, "priority": 1}
            ]
        },
        "angry": {
            "morning": [
                {"activity": "Intense physical exercise", "duration": 45, "priority": 1},
                {"activity": "Punching bag or stress relief activity", "duration": 20, "priority": 1},
                {"activity": "Cool down with protein-rich breakfast", "duration": 15, "priority": 2},
                {"activity": "Identify anger triggers in journal", "duration": 15, "priority": 2}
            ],
            "afternoon": [
                {"activity": "Problem-solving session for anger source", "duration": 30, "priority": 1},
                {"activity": "Physical activity or sports", "duration": 60, "priority": 2},
                {"activity": "Calming activity (art, music, etc.)", "duration": 30, "priority": 2}
            ],
            "evening": [
                {"activity": "Progressive muscle relaxation", "duration": 20, "priority": 1},
                {"activity": "Vent to trusted friend or therapist", "duration": 30, "priority": 2},
                {"activity": "Plan constructive actions for tomorrow", "duration": 20, "priority": 1}
            ]
        },
        "excited": {
            "morning": [
                {"activity": "High-energy workout", "duration": 45, "priority": 1},
                {"activity": "Plan exciting day activities", "duration": 20, "priority": 1},
                {"activity": "Quick energizing breakfast", "duration": 15, "priority": 2},
                {"activity": "Share excitement with others", "duration": 10, "priority": 2}
            ],
            "afternoon": [
                {"activity": "Start that project you've been wanting to do", "duration": 90, "priority": 1},
                {"activity": "Adventure or new experience", "duration": 60, "priority": 2},
                {"activity": "High-energy social activity", "duration": 45, "priority": 2}
            ],
            "evening": [
                {"activity": "Celebrate the day's achievements", "duration": 30, "priority": 1},
                {"activity": "Plan future exciting goals", "duration": 25, "priority": 2},
                {"activity": "Wind down with calming activity", "duration": 20, "priority": 2}
            ]
        },
        "neutral": {
            "morning": [
                {"activity": "Balanced morning routine", "duration": 30, "priority": 1},
                {"activity": "Moderate exercise", "duration": 30, "priority": 2},
                {"activity": "Healthy breakfast", "duration": 20, "priority": 2},
                {"activity": "Review daily goals", "duration": 15, "priority": 2}
            ],
            "afternoon": [
                {"activity": "Focus on important tasks", "duration": 90, "priority": 1},
                {"activity": "Take regular breaks", "duration": 15, "priority": 2},
                {"activity": "Connect with colleagues/friends", "duration": 30, "priority": 2}
            ],
            "evening": [
                {"activity": "Relaxing hobby or reading", "duration": 45, "priority": 1},
                {"activity": "Prepare for tomorrow", "duration": 20, "priority": 2},
                {"activity": "Evening wind-down routine", "duration": 30, "priority": 2}
            ]
        }
    }
    
    @classmethod
    def generate_routine(cls, mood: str, time_period: str = "full_day") -> list:
        """Generate a routine based on mood and time period"""
        mood_lower = mood.lower()
        if mood_lower not in cls.MOOD_ROUTINES:
            mood_lower = "neutral"
        
        if time_period == "morning":
            return cls.MOOD_ROUTINES[mood_lower]["morning"]
        elif time_period == "afternoon":
            return cls.MOOD_ROUTINES[mood_lower]["afternoon"]
        elif time_period == "evening":
            return cls.MOOD_ROUTINES[mood_lower]["evening"]
        else:
            # Return full day routine
            routine = []
            routine.extend(cls.MOOD_ROUTINES[mood_lower]["morning"])
            routine.extend(cls.MOOD_ROUTINES[mood_lower]["afternoon"])
            routine.extend(cls.MOOD_ROUTINES[mood_lower]["evening"])
            return routine

class TodoManager:
    """Simple todo list manager"""
    
    def __init__(self):
        self.todos = []
        self.next_id = 1
    
    def add_todo(self, task: str, priority: int = 2, due_date: str = None, due_time: str = None) -> dict:
        """Add a new todo item"""
        todo = {
            "id": self.next_id,
            "task": task,
            "priority": priority,
            "due_date": due_date,
            "due_time": due_time,
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self.todos.append(todo)
        self.next_id += 1
        return todo
    
    def complete_todo(self, todo_id: int) -> bool:
        """Mark a todo as completed"""
        for todo in self.todos:
            if todo["id"] == todo_id:
                todo["completed"] = True
                return True
        return False
    
    def remove_todo(self, todo_id: int) -> bool:
        """Remove a todo item"""
        for i, todo in enumerate(self.todos):
            if todo["id"] == todo_id:
                self.todos.pop(i)
                return True
        return False
    
    def get_todos(self, show_completed: bool = False) -> list:
        """Get all todos, optionally including completed ones"""
        if show_completed:
            return self.todos
        return [todo for todo in self.todos if not todo["completed"]]
    
    def get_todos_by_priority(self, priority: int) -> list:
        """Get todos by priority level"""
        return [todo for todo in self.todos if todo["priority"] == priority and not todo["completed"]]

# Create global todo manager instance
todo_manager = TodoManager()

class SongRecommendationEngine:
    """Engine for analyzing mood and recommending songs"""
    
    # Hardcoded curated playlists for each mood
    PLAYLISTS = {
        "happy": [
            {"title": "Happy", "artist": "Pharrell Williams", "spotify_url": "https://open.spotify.com/track/60nZcImufyMA1MKQY3dcCH"},
            {"title": "Can't Stop the Feeling!", "artist": "Justin Timberlake", "spotify_url": "https://open.spotify.com/track/20I6sIOMTCkB6w7ryavxtO"},
            {"title": "Good as Hell", "artist": "Lizzo", "spotify_url": "https://open.spotify.com/track/1PckUlxKqWQs3RlWXVBLw3"},
            {"title": "Uptown Funk", "artist": "Mark Ronson ft. Bruno Mars", "spotify_url": "https://open.spotify.com/track/32OlwWuMpZ6b0aN2RZOeMS"},
            {"title": "Walking on Sunshine", "artist": "Katrina and the Waves", "spotify_url": "https://open.spotify.com/track/05wIrZSwuaVWhcv5FfqeH0"},
            {"title": "Gallan Goodiyaan", "artist": "Dil Dhadakne Do", "spotify_url": "https://open.spotify.com/track/0hA7gS5Z1nYV9wT6FQn0fP"},
            {"title": "London Thumakda", "artist": "Queen", "spotify_url": "https://open.spotify.com/track/6Z8R6UsFuGXGtiIxiD8ISb"},
            {"title": "Badtameez Dil", "artist": "Yeh Jawaani Hai Deewani", "spotify_url": "https://open.spotify.com/track/5xrtzzzikpG3BLbo4q1Yul"},
            {"title": "Dil Dhadakne Do", "artist": "Zindagi Na Milegi Dobara", "spotify_url": "https://open.spotify.com/track/6ux8Z5EL3XgAhK04f6XhTQ"},
            {"title": "Senorita", "artist": "Zindagi Na Milegi Dobara", "spotify_url": "https://open.spotify.com/track/0yL7M9fWG1of5QVm7s0A6l"},
            {"title": "Desi Girl", "artist": "Dostana", "spotify_url": "https://open.spotify.com/track/1alW0sP3l41Z8nfdYizwDg"},
            {"title": "Sweety Tera Drama", "artist": "Bareilly Ki Barfi", "spotify_url": "https://open.spotify.com/track/3b69GskD94Z6L4ltVlmftW"},
            {"title": "Cutiepie", "artist": "Ae Dil Hai Mushkil", "spotify_url": "https://open.spotify.com/track/4Tq6ZOqKcW5mh3QmUF8k7P"},
            {"title": "Tamma Tamma Again", "artist": "Badrinath Ki Dulhania", "spotify_url": "https://open.spotify.com/track/5jU9nlfVw6lMtmn3H6kPBi"},
            {"title": "Bom Diggy Diggy", "artist": "Sonu Ke Titu Ki Sweety", "spotify_url": "https://open.spotify.com/track/3f6V3lC6tK2Xz8hZ5Y1C5D"},
            {"title": "Kar Gayi Chull", "artist": "Kapoor & Sons", "spotify_url": "https://open.spotify.com/track/6VUPAx5iygBFwbdb8j6lT2"},
            {"title": "Ban Ja Rani", "artist": "Tumhari Sulu", "spotify_url": "https://open.spotify.com/track/3dJ3NV1TGQYw3oG5xvsXoX"},
            {"title": "Dil Chori", "artist": "Sonu Ke Titu Ki Sweety", "spotify_url": "https://open.spotify.com/track/6HvPOZ8nW10JpDRpN7Vscw"},
            {"title": "Main Hoon Hero Tera", "artist": "Hero", "spotify_url": "https://open.spotify.com/track/7g0HDAnZVrQ4Fr5GZgL1VA"},
            {"title": "Morni Banke", "artist": "Badhaai Ho", "spotify_url": "https://open.spotify.com/track/4Rb2pwK3mXg2vYrA8bmc4C"}
        ],
        "sad": [
            {"title": "Someone Like You", "artist": "Adele", "spotify_url": "https://open.spotify.com/track/4bHsxqR3GMrXTxEPLuK5ue"},
            {"title": "Mad World", "artist": "Gary Jules", "spotify_url": "https://open.spotify.com/track/3JOVTQ5h8HGFnDdp4VT3MP"},
            {"title": "The Sound of Silence", "artist": "Simon & Garfunkel", "spotify_url": "https://open.spotify.com/track/7GElp5u1l2Xfgd5z8L8PaL"},
            {"title": "Hurt", "artist": "Johnny Cash", "spotify_url": "https://open.spotify.com/track/2o4H9vWfjkJWKlvr5wlZRX"},
            {"title": "Black", "artist": "Pearl Jam", "spotify_url": "https://open.spotify.com/track/4XblTJYZEn4y3SXWNx9JRt"},
            {"title": "Channa Mereya", "artist": "Ae Dil Hai Mushkil", "spotify_url": "https://open.spotify.com/track/0xZCuhNNG8M3p9lVf1hY1n"},
            {"title": "Kabira (Encore)", "artist": "Yeh Jawaani Hai Deewani", "spotify_url": "https://open.spotify.com/track/0CKa42Jqrc9fSFbDjePaXP"},
            {"title": "Agar Tum Saath Ho", "artist": "Tamasha", "spotify_url": "https://open.spotify.com/track/6GG2ZQ0ehX7a1ztQlBPm4M"},
            {"title": "Tujhe Kitna Chahne Lage", "artist": "Kabir Singh", "spotify_url": "https://open.spotify.com/track/4mRDTkY3MJltFIKQ6d1kDa"},
            {"title": "Kal Ho Naa Ho", "artist": "Kal Ho Naa Ho", "spotify_url": "https://open.spotify.com/track/5FpJYVqQZ2n7tJXhFhZLct"},
            {"title": "Tum Hi Ho", "artist": "Aashiqui 2", "spotify_url": "https://open.spotify.com/track/1k9WcUzZ4FfoT8q1yHn2kB"},
            {"title": "Phir Bhi Tumko Chaahunga", "artist": "Half Girlfriend", "spotify_url": "https://open.spotify.com/track/4kflIGfjdZJW4ot2ioixTB"},
            {"title": "Judaai", "artist": "Badlapur", "spotify_url": "https://open.spotify.com/track/3r8jhJtQUZPncJcfWc8McC"},
            {"title": "Ae Dil Hai Mushkil (Title Track)", "artist": "Ae Dil Hai Mushkil", "spotify_url": "https://open.spotify.com/track/6ggxLwEfdjwGstn2mafqy1"},
            {"title": "Hasi Ban Gaye", "artist": "Hamari Adhuri Kahani", "spotify_url": "https://open.spotify.com/track/4fek1TRV9dxHn1h3J3n6Lz"},
            {"title": "Khairiyat", "artist": "Chhichhore", "spotify_url": "https://open.spotify.com/track/7cfpLMsH3oGDmslEdOBYib"},
            {"title": "Tera Ban Jaunga", "artist": "Kabir Singh", "spotify_url": "https://open.spotify.com/track/7kQX9FqU8oUTgMy4QdTe6P"},
            {"title": "Pachtaoge", "artist": "Arijit Singh", "spotify_url": "https://open.spotify.com/track/4kROu4c2TStRmNsGhDpumX"},
            {"title": "Bekhayali", "artist": "Kabir Singh", "spotify_url": "https://open.spotify.com/track/6GzApXoBQiiAjak3tOQnFh"},
            {"title": "Tadap Tadap", "artist": "Hum Dil De Chuke Sanam", "spotify_url": "https://open.spotify.com/track/5Lk4I1R7HeFwwKogF4Zz3P"}
        ],
        "angry": [
            {"title": "Break Stuff", "artist": "Limp Bizkit", "spotify_url": "https://open.spotify.com/track/5bIgwJD4kWQ4LVgUhvnEQs"},
            {"title": "Bodies", "artist": "Drowning Pool", "spotify_url": "https://open.spotify.com/track/4KNMTEhkEKmjZhb2Dn6VHh"},
            {"title": "Killing in the Name", "artist": "Rage Against the Machine", "spotify_url": "https://open.spotify.com/track/59WN2psjkt1tyaxjspN8fp"},
            {"title": "Chop Suey!", "artist": "System of a Down", "spotify_url": "https://open.spotify.com/track/2DlHlPMa4M17kufBvI2lEN"},
            {"title": "In the End", "artist": "Linkin Park", "spotify_url": "https://open.spotify.com/track/60a0Rd6pjrkxjPbaKzXjfq"},
            {"title": "Malhari", "artist": "Bajirao Mastani", "spotify_url": "https://open.spotify.com/track/0lYXgsK9e1wZ3yS1x4Hivk"},
            {"title": "Zinda", "artist": "Bhaag Milkha Bhaag", "spotify_url": "https://open.spotify.com/track/1R6rTUkPGI2R3UfQnDyWHq"},
            {"title": "Sultan (Title Track)", "artist": "Sultan", "spotify_url": "https://open.spotify.com/track/3yUoQTPFwOZJkV5U5LJxkP"},
            {"title": "Sher Aaya Sher", "artist": "Gully Boy", "spotify_url": "https://open.spotify.com/track/1mSb5hFEPxZ1bJ5aRe4QFk"},
            {"title": "Apna Time Aayega", "artist": "Gully Boy", "spotify_url": "https://open.spotify.com/track/6Gf5L2ZgFJvWdoZnKCR3cK"},
            {"title": "Bhaag DK Bose", "artist": "Delhi Belly", "spotify_url": "https://open.spotify.com/track/7L10ZfM1U3d3W5lqG7uZtn"},
            {"title": "Ziddi Dil", "artist": "Mary Kom", "spotify_url": "https://open.spotify.com/track/4dd6tP6uEUkPCr6mjhRZ1g"},
            {"title": "Mukkala Muqabala", "artist": "Street Dancer 3D", "spotify_url": "https://open.spotify.com/track/2oYkwfNjFJZX4sO0e6D2W0"},
            {"title": "Dangal Title Track", "artist": "Dangal", "spotify_url": "https://open.spotify.com/track/0RkCukKw9p1Mz4sOGJbnfh"},
            {"title": "Dhakad", "artist": "Dangal", "spotify_url": "https://open.spotify.com/track/7kADdZJpFT9gLgoHndpCBF"},
            {"title": "Desi Kalakaar", "artist": "Yo Yo Honey Singh", "spotify_url": "https://open.spotify.com/track/0P3oVJBFOv3TDxS0hGxFZC"},
            {"title": "All Black", "artist": "Raftaar, Badshah", "spotify_url": "https://open.spotify.com/track/6iZ9EqXzPWnMAs1y8r9IJK"},
            {"title": "Bandook Meri Laila", "artist": "A Gentleman", "spotify_url": "https://open.spotify.com/track/3vMQV8HT5PaLMkZVZrcrNo"},
            {"title": "Swag Mera Desi", "artist": "Raftaar", "spotify_url": "https://open.spotify.com/track/7Kthn4zZbL3McZScCQe2Ew"},
            {"title": "Sher Ki Daawat", "artist": "Dishoom", "spotify_url": "https://open.spotify.com/track/4SwjUHQoVQyDUBFcGioJtr"}
        ],
        "excited": [
            {"title": "Thunder", "artist": "Imagine Dragons", "spotify_url": "https://open.spotify.com/track/0tBbt8CrmxbjRP0pueQkyU"},
            {"title": "Pump It", "artist": "The Black Eyed Peas", "spotify_url": "https://open.spotify.com/track/7Jh1bpe76CNTCgdgAdBw4Z"},
            {"title": "Eye of the Tiger", "artist": "Survivor", "spotify_url": "https://open.spotify.com/track/2KH16WveTQWT6KOG9Rg6e2"},
            {"title": "We Will Rock You", "artist": "Queen", "spotify_url": "https://open.spotify.com/track/4pbJqGIASGPr0ZpGpnWkDn"},
            {"title": "Don't Stop Believin'", "artist": "Journey", "spotify_url": "https://open.spotify.com/track/4bHsxqR3GMrXTxEPLuK5ue"},
            {"title": "Nashe Si Chadh Gayi", "artist": "Befikre", "spotify_url": "https://open.spotify.com/track/4S7xBBfB4f9z1pBDEWIslU"},
            {"title": "Kala Chashma", "artist": "Baar Baar Dekho", "spotify_url": "https://open.spotify.com/track/5QTxFnGygVM4jFQiBovmRo"},
            {"title": "Morni Banke", "artist": "Badhaai Ho", "spotify_url": "https://open.spotify.com/track/4Rb2pwK3mXg2vYrA8bmc4C"},
            {"title": "Abhi Toh Party Shuru Hui Hai", "artist": "Khoobsurat", "spotify_url": "https://open.spotify.com/track/5o4XqfJgYfOImU2Bj8MABJ"},
            {"title": "High Heels", "artist": "Ki & Ka", "spotify_url": "https://open.spotify.com/track/7qgX91X5QROqOPvkd7vC6Y"},
            {"title": "Kar Gayi Chull", "artist": "Kapoor & Sons", "spotify_url": "https://open.spotify.com/track/6VUPAx5iygBFwbdb8j6lT2"},
            {"title": "Dil Dhadakne Do", "artist": "Zindagi Na Milegi Dobara", "spotify_url": "https://open.spotify.com/track/6ux8Z5EL3XgAhK04f6XhTQ"},
            {"title": "Senorita", "artist": "Zindagi Na Milegi Dobara", "spotify_url": "https://open.spotify.com/track/0yL7M9fWG1of5QVm7s0A6l"},
            {"title": "Party All Night", "artist": "Boss", "spotify_url": "https://open.spotify.com/track/6ZzAwEdLRgG1X2TgkpMJHc"},
            {"title": "Selfie Le Le Re", "artist": "Bajrangi Bhaijaan", "spotify_url": "https://open.spotify.com/track/0yybapnYapD42QBM9RrFdn"},
            {"title": "Cutiepie", "artist": "Ae Dil Hai Mushkil", "spotify_url": "https://open.spotify.com/track/4Tq6ZOqKcW5mh3QmUF8k7P"},
            {"title": "Galti Se Mistake", "artist": "Jagga Jasoos", "spotify_url": "https://open.spotify.com/track/0flxjloW2aG7Gz9uvFG1DY"},
            {"title": "Hook Up Song", "artist": "Student of the Year 2", "spotify_url": "https://open.spotify.com/track/3Sxtox7brnG9rVt7lZnZqE"},
            {"title": "Slow Motion", "artist": "Bharat", "spotify_url": "https://open.spotify.com/track/3bQYZjIFlEbnZq6I0H0kHw"},
            {"title": "Proper Patola", "artist": "Namaste England", "spotify_url": "https://open.spotify.com/track/1ZuQzcdhwzZyFUDZpR9gOn"}
            ],
        "neutral": [
            {"title": "Shape of You", "artist": "Ed Sheeran", "spotify_url": "https://open.spotify.com/track/7qiZfU4dY1lWllzX7mPBI3"},
            {"title": "Blinding Lights", "artist": "The Weeknd", "spotify_url": "https://open.spotify.com/track/0VjIjW4GlULA0mG8km5iU8"},
            {"title": "Watermelon Sugar", "artist": "Harry Styles", "spotify_url": "https://open.spotify.com/track/6UelLqGlWMcVH1E5c4H7lY"},
            {"title": "Levitating", "artist": "Dua Lipa", "spotify_url": "https://open.spotify.com/track/463CkQjx2Zk1yXoBuierM9"},
            {"title": "Stay", "artist": "The Kid LAROI & Justin Bieber", "spotify_url": "https://open.spotify.com/track/5HCyWlXZPP0y6Gqq8TgA20"},
            {"title": "Raabta", "artist": "Agent Vinod", "spotify_url": "https://open.spotify.com/track/6j0vm6cwSGYJdLzD4FFKkD"},
            {"title": "Jeene Laga Hoon", "artist": "Ramaiya Vastavaiya", "spotify_url": "https://open.spotify.com/track/3m3cvFY8P1uKJuJs8YoO2M"},
            {"title": "Hawayein", "artist": "Jab Harry Met Sejal", "spotify_url": "https://open.spotify.com/track/1H4bnCw3J9Tz3LwFTQixNm"},
            {"title": "Kaise Hua", "artist": "Kabir Singh", "spotify_url": "https://open.spotify.com/track/0qlWcS66ohOIi0M8JZwPft"},
            {"title": "Tera Yaar Hoon Main", "artist": "Sonu Ke Titu Ki Sweety", "spotify_url": "https://open.spotify.com/track/1ZLrIVa8p0VaOS9uQ8vO0V"},
            {"title": "Kuch Kuch Hota Hai", "artist": "Kuch Kuch Hota Hai", "spotify_url": "https://open.spotify.com/track/5g7hUZ9kZyW0R0f6D0AzB5"},
            {"title": "Dil Diyan Gallan", "artist": "Tiger Zinda Hai", "spotify_url": "https://open.spotify.com/track/7okSUtN66ckbL5ItzKH5VJ"},
            {"title": "Pee Loon", "artist": "Once Upon A Time In Mumbaai", "spotify_url": "https://open.spotify.com/track/1hxYrbz4kDlVvfI9WKvBdv"},
            {"title": "Sooraj Dooba Hain", "artist": "Roy", "spotify_url": "https://open.spotify.com/track/1RJ9UdtD1U7L1EGHhGkP5Q"},
            {"title": "Tu Chale", "artist": "I", "spotify_url": "https://open.spotify.com/track/3LtnR1TzN8fKvbJyyagpsu"},
            {"title": "Kaun Tujhe", "artist": "M.S. Dhoni", "spotify_url": "https://open.spotify.com/track/6Fj2olT9XQBRkhrzXK7Cjp"},
            {"title": "Muskurane", "artist": "CityLights", "spotify_url": "https://open.spotify.com/track/4muPiHmZ7YDDz6DDjClVTe"},
            {"title": "Bol Do Na Zara", "artist": "Azhar", "spotify_url": "https://open.spotify.com/track/3S6tfHQsHDQ8gj2unXcTjv"},
            {"title": "Saibo", "artist": "Shor In The City", "spotify_url": "https://open.spotify.com/track/2bJz8IhECszPbgYGb4p4NB"},
            {"title": "Hasi", "artist": "Hamari Adhuri Kahani", "spotify_url": "https://open.spotify.com/track/4fek1TRV9dxHn1h3J3n6Lz"}
        ]
    }
    
    # Keywords for mood detection
    MOOD_KEYWORDS = {
        "happy": ["happy", "joy", "excited", "great", "amazing", "wonderful", "fantastic", "love", "good", "smile", "laugh", "cheerful"],
        "sad": ["sad", "depressed", "down", "upset", "hurt", "cry", "lonely", "heartbreak", "miss", "lost", "blue", "melancholy"],
        "angry": ["angry", "mad", "furious", "hate", "annoyed", "frustrated", "rage", "pissed", "irritated", "livid"],
        "excited": ["excited", "pumped", "hyped", "energy", "party", "celebration", "workout", "motivated", "adrenaline", "intense"],
        "neutral": ["okay", "fine", "normal", "regular", "whatever", "meh", "calm", "peaceful", "relaxed"]
    }
    
    @classmethod
    def analyze_mood(cls, text: str) -> str:
        """Analyze text and return the detected mood"""
        text_lower = text.lower()
        mood_scores = {mood: 0 for mood in cls.MOOD_KEYWORDS.keys()}
        
        # Count keyword matches for each mood
        for mood, keywords in cls.MOOD_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    mood_scores[mood] += 1
        
        # Return the mood with highest score, default to neutral
        detected_mood = max(mood_scores, key=mood_scores.get)
        if mood_scores[detected_mood] == 0:
            detected_mood = "neutral"
            
        return detected_mood
    
    @classmethod
    def get_recommendations(cls, mood: str, count: int = 5) -> list:
        """Get song recommendations for a specific mood"""
        return cls.PLAYLISTS.get(mood, cls.PLAYLISTS["neutral"])[:count]

# --- PDF Processing Class ---
class PDFProcessor:
    @staticmethod
    async def process_pdf(pdf_data: str) -> str:
        """Process PDF data and return extracted text"""
        import base64
        from PyPDF2 import PdfReader
        from PyPDF2.errors import PdfReadError
        import logging
        from io import BytesIO
        
        try:
            # Decode base64 data
            try:
                pdf_bytes = base64.b64decode(pdf_data)
            except Exception as e:
                return f"Error: Failed to decode PDF data - {str(e)}"
            
            # Create BytesIO object
            pdf_stream = BytesIO(pdf_bytes)
            
            # Extract text from PDF
            text = ""
            try:
                pdf_reader = PdfReader(pdf_stream)
                
                if len(pdf_reader.pages) == 0:
                    return "Error: PDF appears to be empty"
                
                # Extract text from all pages
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                    except Exception as page_error:
                        text += f"\n--- Page {page_num + 1} ---\n[Error extracting page: {str(page_error)}]\n"
                        continue
                        
            except Exception as e:
                return f"Error: Failed to read PDF - {str(e)}"
            
            if not text.strip():
                return "Error: No text could be extracted from the PDF. The PDF might be image-based or password protected."
            
            return text.strip()
            
        except Exception as e:
            logging.error(f"Unexpected error in process_pdf: {str(e)}")
            return f"Error: Failed to process PDF - {str(e)}"
    

# --- MCP Server Setup ---
mcp = FastMCP(
    "PDF Chat & Schedule Generator MCP Server",
    auth=SimpleBearerAuthProvider(TOKEN),
)

# --- Tool: validate (required by Puch) ---
@mcp.tool
async def validate() -> str:
    return MY_NUMBER

# --- Tool: extract_pdf_text ---
ExtractPDFTextDescription = RichToolDescription(
    description="Extract text content from PDF files for analysis and chat",
    use_when="User uploads a PDF file and wants to extract text content for further processing or chat",
    side_effects="Returns extracted text from all pages of the PDF"
)

@mcp.tool(description=ExtractPDFTextDescription.model_dump_json())
async def extract_pdf_text(
    puch_pdf_data: Annotated[str, Field(description="The file ID of the uploaded PDF provided by the platform")] = None,
) -> str:
    """
    Extract text from a PDF document. This text can then be used by Puch AI's LLM for chat.
    """
    if not puch_pdf_data:
        return "Error: No PDF file ID was provided. Please upload a PDF to extract its text."

    try:
        file_id = puch_pdf_data
        file_object = await mcp.get_file_by_id(file_id)

        if not file_object or not hasattr(file_object, 'data'):
            return "Error: Could not retrieve the file from the platform using the provided ID."

        pdf_base64_data = file_object.data

        pdf_text = await PDFProcessor.process_pdf(pdf_base64_data)
        if pdf_text.startswith("Error:"):
            return pdf_text

        word_count = len(pdf_text.split())
        char_count = len(pdf_text)
        result = ["📄 **PDF Text Extraction Complete**",
            "",
            f"📊 **Statistics:**",
            f"• Word count: {word_count:,}",
            f"• Character count: {char_count:,}",
            "",
            "📝 **Extracted Text:**",
            "=" * 50,
            pdf_text,
            "=" * 50,
            "",
            "✅ **Ready for Chat:** The text has been extracted successfully. You can now ask questions about this content!"
        ]
        return "\n".join(result)
    except Exception as e:
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"Failed to extract PDF text: {str(e)}"
        ))
# --- Tool: generate_mood_routine ---
MoodRoutineDescription = RichToolDescription(
    description="Generate a personalized daily routine based on current mood and emotional state",
    use_when="User wants a routine tailored to their current mood (happy, sad, angry, excited, neutral)",
    side_effects="Creates a time-structured routine with mood-appropriate activities"
)

@mcp.tool(description=MoodRoutineDescription.model_dump_json())
async def generate_mood_routine(
    mood_text: Annotated[str, Field(description="Text describing current mood or feelings")],
    mood_override: Annotated[str | None, Field(description="Manually specify mood (happy/sad/angry/excited/neutral)")] = None,
    time_period: Annotated[str, Field(description="Time period for routine (morning/afternoon/evening/full_day)")] = "full_day",
    start_time: Annotated[str, Field(description="Routine start time (HH:MM)")] = "08:00"
) -> str:
    """
    Generate a personalized routine based on mood analysis with specific activities and timing.
    """
    try:
        # Detect or use specified mood
        if mood_override and mood_override.lower() in ["happy", "sad", "angry", "excited", "neutral"]:
            detected_mood = mood_override.lower()
            mood_source = "manually specified"
        else:
            detected_mood = SongRecommendationEngine.analyze_mood(mood_text)
            mood_source = "detected from your message"
        
        # Generate routine activities
        routine_activities = RoutineGenerator.generate_routine(detected_mood, time_period)
        
        # Create schedule with timing
        current_time = datetime.strptime(start_time, "%H:%M")
        scheduled_activities = []
        
        for activity in routine_activities:
            end_time = current_time + timedelta(minutes=activity['duration'])
            scheduled_activities.append({
                'activity': activity['activity'],
                'start': current_time.strftime("%H:%M"),
                'end': end_time.strftime("%H:%M"),
                'duration': activity['duration'],
                'priority': activity['priority']
            })
            current_time = end_time + timedelta(minutes=5)  # 5-minute buffer between activities
        
        # Format the routine
        mood_emoji = {
            "happy": "😊",
            "sad": "😢", 
            "angry": "😠",
            "excited": "🚀",
            "neutral": "😐"
        }
        
        result = [
            f"🌟 **Mood-Based Routine Generated**",
            f"",
            f"**Your Mood:** {mood_emoji.get(detected_mood, '🎯')} {detected_mood.title()} ({mood_source})",
            f"**Your Message:** \"{mood_text}\"",
            f"**Time Period:** {time_period.replace('_', ' ').title()}",
            f"",
            f"📅 **Your Personalized Routine:**"
        ]
        
        for item in scheduled_activities:
            priority_emoji = "❗" if item['priority'] == 1 else "🔹" if item['priority'] == 2 else "▪️"
            result.append(
                f"{priority_emoji} {item['start']}-{item['end']} ({item['duration']}min): {item['activity']}"
            )
        
        result.extend([
            f"",
            f"💡 **Tips for your {detected_mood} mood:**"
        ])
        
        # Add mood-specific tips
        tips = {
            "happy": ["Keep the positive energy flowing!", "Share your happiness with others", "Use this energy for productive activities"],
            "sad": ["Be gentle with yourself", "Focus on self-care and comfort", "Reach out to supportive people"],
            "angry": ["Channel anger into physical activity", "Take time to cool down", "Address the source of anger constructively"],
            "excited": ["Use this energy for important projects", "Stay focused despite high energy", "Plan future exciting goals"],
            "neutral": ["Maintain balance and consistency", "Focus on important but routine tasks", "Build healthy habits"]
        }
        
        for tip in tips.get(detected_mood, tips["neutral"]):
            result.append(f"• {tip}")
        
        return "\n".join(result)
        
    except Exception as e:
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"Failed to generate mood routine: {str(e)}"
        ))

# --- Tool: manage_todo_list ---
TodoListDescription = RichToolDescription(
    description="Manage a personal todo list with add, complete, remove, and view operations",
    use_when="User wants to manage their tasks and todo items",
    side_effects="Modifies the todo list by adding, completing, or removing items"
)

class TodoAction(Enum):
    ADD = "add"
    COMPLETE = "complete"
    REMOVE = "remove"
    VIEW = "view"
    VIEW_BY_PRIORITY = "view_by_priority"

@mcp.tool(description=TodoListDescription.model_dump_json())
async def manage_todo_list(
    action: Annotated[TodoAction, Field(description="Action to perform on todo list")],
    task: Annotated[str | None, Field(description="Task description (required for 'add' action)")] = None,
    todo_id: Annotated[int | None, Field(description="Todo ID (required for 'complete' and 'remove' actions)")] = None,
    priority: Annotated[int, Field(description="Task priority: 1=high, 2=medium, 3=low", ge=1, le=3)] = 2,
    due_date: Annotated[str | None, Field(description="Due date for task (YYYY-MM-DD format)")] = None,
    time: Annotated[str | None, Field(description="Due time for task (HH:MM format)")] = None,
    show_completed: Annotated[bool, Field(description="Include completed todos in view")] = False,
    priority_filter: Annotated[int | None, Field(description="Filter by priority level (1-3)", ge=1, le=3)] = None
) -> str:
    """
    Manage your personal todo list with various operations.
    """
    try:
        if action == TodoAction.ADD:
            if not task:
                return "❌ Error: Task description is required for adding a todo."
            
            todo = todo_manager.add_todo(task, priority, due_date, time)
            priority_text = {1: "High", 2: "Medium", 3: "Low"}[priority]
            
            # Build due date/time text
            due_parts = []
            if due_date:
                due_parts.append(f"Date: {due_date}")
            if time:
                due_parts.append(f"Time: {time}")
            due_text = f" (Due: {', '.join(due_parts)})" if due_parts else ""
            
            return f"✅ **Todo Added Successfully!**\n\n📝 **Task:** {task}\n🔹 **Priority:** {priority_text}\n🆔 **ID:** {todo['id']}{due_text}\n📅 **Created:** {todo['created_at']}"
        
        elif action == TodoAction.COMPLETE:
            if todo_id is None:
                return "❌ Error: Todo ID is required for completing a task."
            
            if todo_manager.complete_todo(todo_id):
                return f"🎉 **Task Completed!**\n\nTodo ID {todo_id} has been marked as completed."
            else:
                return f"❌ Error: Todo with ID {todo_id} not found."
        
        elif action == TodoAction.REMOVE:
            if todo_id is None:
                return "❌ Error: Todo ID is required for removing a task."
            
            if todo_manager.remove_todo(todo_id):
                return f"🗑️ **Task Removed!**\n\nTodo ID {todo_id} has been permanently deleted."
            else:
                return f"❌ Error: Todo with ID {todo_id} not found."
        
        elif action == TodoAction.VIEW_BY_PRIORITY:
            if priority_filter is None:
                return "❌ Error: Priority level is required for viewing by priority."
            
            todos = todo_manager.get_todos_by_priority(priority_filter)
            priority_text = {1: "High", 2: "Medium", 3: "Low"}[priority_filter]
            
            if not todos:
                return f"📋 **{priority_text} Priority Todos**\n\nNo tasks found with {priority_text.lower()} priority."
            
            result = [f"📋 **{priority_text} Priority Todos** ({len(todos)} tasks)\n"]
            for todo in todos:
                # Build due date/time text
                due_parts = []
                if todo.get('due_date'):
                    due_parts.append(f"Date: {todo['due_date']}")
                if todo.get('due_time'):
                    due_parts.append(f"Time: {todo['due_time']}")
                due_text = f" 📅 Due: {', '.join(due_parts)}" if due_parts else ""
                result.append(f"🆔 {todo['id']} | {todo['task']}{due_text}")
            
            return "\n".join(result)
        
        else:  # VIEW action
            todos = todo_manager.get_todos(show_completed)
            
            if not todos:
                return "📋 **Your Todo List**\n\nNo todos found. Add some tasks to get started!"
            
            # Separate by completion status and priority
            pending_todos = [t for t in todos if not t['completed']]
            completed_todos = [t for t in todos if t['completed']]
            
            result = [f"📋 **Your Todo List** ({len(pending_todos)} pending, {len(completed_todos)} completed)\n"]
            
            if pending_todos:
                result.append("**🔄 Pending Tasks:**")
                # Sort by priority
                pending_todos.sort(key=lambda x: x['priority'])
                for todo in pending_todos:
                    priority_emoji = "❗" if todo['priority'] == 1 else "🔹" if todo['priority'] == 2 else "▪️"
                    # Build due date/time text
                    due_parts = []
                    if todo.get('due_date'):
                        due_parts.append(f"Date: {todo['due_date']}")
                    if todo.get('due_time'):
                        due_parts.append(f"Time: {todo['due_time']}")
                    due_text = f" 📅 Due: {', '.join(due_parts)}" if due_parts else ""
                    result.append(f"{priority_emoji} 🆔 {todo['id']} | {todo['task']}{due_text}")
                result.append("")
            
            if completed_todos and show_completed:
                result.append("**✅ Completed Tasks:**")
                for todo in completed_todos:
                    result.append(f"✅ 🆔 {todo['id']} | {todo['task']}")
            
            result.extend([
                "**💡 Quick Actions:**",
                "• Add task: specify action='add' and task description",
                "• Complete task: specify action='complete' and todo_id",
                "• Remove task: specify action='remove' and todo_id"
            ])
            
            return "\n".join(result)
        
    except Exception as e:
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"Failed to manage todo list: {str(e)}"
        ))
# --- Tool: generate_schedule ---
ScheduleGeneratorDescription = RichToolDescription(
    description="Generate a daily or weekly schedule based on tasks, priorities, and optionally mood",
    use_when="User needs help organizing their time with a structured schedule, optionally considering their mood",
    side_effects="Creates a time-blocked schedule with mood-appropriate suggestions"
)

class ScheduleItem(BaseModel):
    task: str
    duration_minutes: int
    priority: int = Field(ge=1, le=3, description="1=high, 2=medium, 3=low")

@mcp.tool(description=ScheduleGeneratorDescription.model_dump_json())
async def generate_schedule(
    tasks: Annotated[list[ScheduleItem], Field(description="List of tasks to schedule")],
    start_time: Annotated[str, Field(description="Schedule start time (HH:MM)")] = "08:00",
    end_time: Annotated[str, Field(description="Schedule end time (HH:MM)")] = "20:00",
    date: Annotated[str | None, Field(description="Date for schedule (YYYY-MM-DD)")] = None,
    mood_text: Annotated[str | None, Field(description="Optional: Text describing current mood for mood-based suggestions")] = None,
    include_mood_activities: Annotated[bool, Field(description="Whether to include mood-based activity suggestions")] = False,
) -> str:
    """
    Generate a time-blocked schedule based on provided tasks and time constraints.
    Optionally includes mood-based activity suggestions.
    """
    try:
        # Parse time inputs
        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt = datetime.strptime(end_time, "%H:%M")
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)  # Handle overnight schedules
        total_minutes = int((end_dt - start_dt).total_seconds() / 60)
        
        # Analyze mood if provided
        detected_mood = None
        if mood_text and include_mood_activities:
            detected_mood = SongRecommendationEngine.analyze_mood(mood_text)
        
        # Sort tasks by priority then duration
        sorted_tasks = sorted(tasks, key=lambda x: (x.priority, x.duration_minutes))
        
        # Schedule tasks
        current_time = start_dt
        schedule = []
        remaining_minutes = total_minutes
        
        for task in sorted_tasks:
            if task.duration_minutes <= remaining_minutes:
                end_time_task = current_time + timedelta(minutes=task.duration_minutes)
                schedule.append({
                    'task': task.task,
                    'start': current_time.strftime("%H:%M"),
                    'end': end_time_task.strftime("%H:%M"),
                    'duration': task.duration_minutes,
                    'priority': task.priority,
                    'type': 'user_task'
                })
                current_time = end_time_task
                remaining_minutes -= task.duration_minutes
            else:
                break  # Skip tasks that don't fit
        
        # Add mood-based suggestions if requested and there's remaining time
        if detected_mood and include_mood_activities and remaining_minutes > 30:
            mood_activities = RoutineGenerator.generate_routine(detected_mood, "full_day")
            suitable_activities = [
                act for act in mood_activities 
                if act['duration'] <= remaining_minutes and act['priority'] <= 2
            ][:3]  # Limit to 3 suggestions
            
            for activity in suitable_activities:
                if activity['duration'] <= remaining_minutes:
                    end_time_activity = current_time + timedelta(minutes=activity['duration'])
                    schedule.append({
                        'task': f"💭 {activity['activity']} (mood suggestion)",
                        'start': current_time.strftime("%H:%M"),
                        'end': end_time_activity.strftime("%H:%M"),
                        'duration': activity['duration'],
                        'priority': activity['priority'],
                        'type': 'mood_suggestion'
                    })
                    current_time = end_time_activity + timedelta(minutes=5)
                    remaining_minutes -= (activity['duration'] + 5)
        
        # Format the schedule
        date_str = f" for {date}" if date else ""
        mood_str = f" (optimized for {detected_mood} mood)" if detected_mood else ""
        
        result = [f"📅 Generated Schedule{date_str}{mood_str} ({start_time} - {end_dt.strftime('%H:%M')}):\n"]
        
        user_tasks = [item for item in schedule if item['type'] == 'user_task']
        mood_suggestions = [item for item in schedule if item['type'] == 'mood_suggestion']
        
        if user_tasks:
            result.append("**📝 Your Scheduled Tasks:**")
            for item in user_tasks:
                priority_emoji = "❗" if item['priority'] == 1 else "🔹" if item['priority'] == 2 else "▪️"
                result.append(
                    f"{priority_emoji} {item['start']}-{item['end']} ({item['duration']}min): {item['task']}"
                )
            result.append("")
        
        if mood_suggestions:
            result.append(f"**🌟 Mood-Based Suggestions ({detected_mood}):**")
            for item in mood_suggestions:
                priority_emoji = "❗" if item['priority'] == 1 else "🔹" if item['priority'] == 2 else "▪️"
                result.append(
                    f"{priority_emoji} {item['start']}-{item['end']} ({item['duration']}min): {item['task']}"
                )
            result.append("")
        
        if remaining_minutes > 0:
            result.append(f"⏳ Remaining free time: {remaining_minutes} minutes")
        
        if detected_mood:
            mood_emoji = {"happy": "😊", "sad": "😢", "angry": "😠", "excited": "🚀", "neutral": "😐"}
            result.append(f"\n🎯 **Mood detected:** {mood_emoji.get(detected_mood, '🎯')} {detected_mood.title()}")
        
        return "\n".join(result)
    
    except Exception as e:
        raise McpError(ErrorData(
            code=INVALID_PARAMS,
            message=f"Invalid schedule parameters: {str(e)}"
        ))

# --- Tool: Song Recommendations ---
SongRecommendationDescription = RichToolDescription(
    description="Analyze user's mood from text and recommend songs from curated Spotify playlists",
    use_when="User expresses emotions, asks for music recommendations, or mentions their current mood/feelings",
    side_effects="Returns personalized song recommendations with Spotify links based on detected or specified mood"
)

@mcp.tool(description=SongRecommendationDescription.model_dump_json())
async def recommend_songs(
    user_text: Annotated[str, Field(description="Text expressing the user's current mood, feelings, or music request")],
    mood_override: Annotated[str | None, Field(description="Manually specify mood (happy/sad/angry/excited/neutral)")] = None,
    count: Annotated[int, Field(description="Number of songs to recommend (1-5)", ge=1, le=5)] = 5,
) -> str:
    """
    Analyze user's mood from their text and recommend appropriate songs from curated playlists.
    """
    try:
        if mood_override and mood_override.lower() in ["happy", "sad", "angry", "excited", "neutral"]:
            detected_mood = mood_override.lower()
            mood_source = "manually specified"
        else:
            detected_mood = SongRecommendationEngine.analyze_mood(user_text)
            mood_source = "detected from your message"
        
        songs = SongRecommendationEngine.get_recommendations(detected_mood, count)
        
        mood_emoji = {"happy": "😊", "sad": "😢", "angry": "😠", "excited": "🚀", "neutral": "😐"}
        
        result = [
            f"🎵 **Song Recommendations Based on Your Mood**",
            f"",
            f"**Detected Mood:** {mood_emoji.get(detected_mood, '🎵')} {detected_mood.title()} ({mood_source})",
            f"**Your Message:** \"{user_text}\"",
            f"",
            f"**🎧 Recommended Songs:**"
        ]
        
        for i, song in enumerate(songs, 1):
            result.append(f"{i}. **{song['title']}** by {song['artist']}")
            result.append(f"   🔗 [Listen on Spotify]({song['spotify_url']})")
        
        result.extend([
            f"",
            f"💡 **Tip:** Click the Spotify links to listen to these tracks!",
            f"🔄 Want different recommendations? Try specifying a different mood!"
        ])
        
        return "\n".join(result)
        
    except Exception as e:
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"Failed to generate song recommendations: {str(e)}"
        ))

# --- Tool: Image Processing ---
MAKE_IMG_BLACK_AND_WHITE_DESCRIPTION = RichToolDescription(
    description="Convert an image to black and white and save it.",
    use_when="Use this tool when the user provides an image URL and requests it to be converted to black and white.",
    side_effects="The image will be processed and saved in a black and white format.",
)

@mcp.tool(description=MAKE_IMG_BLACK_AND_WHITE_DESCRIPTION.model_dump_json())
async def make_img_black_and_white(
    puch_image_data: Annotated[str, Field(description="Base64-encoded image data to convert to black and white")] = None,
) -> list[TextContent | ImageContent]:
    import base64
    import io
    from PIL import Image

    if not puch_image_data:
        return [TextContent(type="text", text="Error: No image data provided.")]

    try:
        image_bytes = base64.b64decode(puch_image_data)
        image = Image.open(io.BytesIO(image_bytes))

        bw_image = image.convert("L")

        buf = io.BytesIO()
        bw_image.save(buf, format="PNG")
        bw_bytes = buf.getvalue()
        bw_base64 = base64.b64encode(bw_bytes).decode("utf-8")

        return [ImageContent(type="image", mimeType="image/png", data=bw_base64)]
    except Exception as e:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))

# --- Tool: get_weather (ADDED) ---
WeatherToolDescription = RichToolDescription(
    description="Fetches the current weather for a specified city.",
    use_when="User asks about the weather, temperature, or climate in a particular location.",
    side_effects="Makes a real-time request to an external weather API."
)

@mcp.tool(description=WeatherToolDescription.model_dump_json())
async def get_weather(
    city: Annotated[str, Field(description="The city name to get the weather for, e.g., 'Kolkata' or 'London'")]
) -> str:
    """
    Fetches the current weather from the OpenWeatherMap API for a given city asynchronously.
    """
    if not OPENWEATHER_API_KEY:
        return "Error: OpenWeatherMap API key is not configured."

    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"  # For Celsius
    }
    
    try:
        # Use an async client to make the request without blocking the server
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        data = response.json()
        
        if data.get("cod") != 200:
            return f"Error: Could not retrieve weather for {city}. Reason: {data.get('message', 'Unknown error')}"

        main = data['main']
        weather_desc = data['weather'][0]['description']
        temp = main['temp']
        feels_like = main['feels_like']
        humidity = main['humidity']

        return (
            f"☀️ Weather in {data['name']}:\n"
            f"- Condition: {weather_desc.title()}\n"
            f"- Temperature: {temp}°C\n"
            f"- Feels Like: {feels_like}°C\n"
            f"- Humidity: {humidity}%"
        )

    except httpx.HTTPStatusError as http_err:
        if http_err.response.status_code == 404:
            return f"Error: The city '{city}' could not be found. Please check the spelling."
        return f"Error: An HTTP error occurred: {http_err}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

# --- Run MCP Server ---
async def main():
    # SOURCERY: Replaced loop with a more efficient and readable .join method
    port = int(os.environ.get("PORT", 8086))
    print(f"🚀 Starting MCP server on http://0.0.0.0:{port}")
    tools_list = [
        "🔍 validate - Required validation tool for Puch AI",
        "📄 extract_pdf_text - Extract text content from PDF files",
        "🌟 generate_mood_routine - Generate mood-based daily routines",
        "📝 manage_todo_list - Manage personal todo list",
        "📅 generate_schedule - Generate time-blocked schedules",
        "🎵 recommend_songs - Get mood-based song recommendations",
        "🖼️ make_img_black_and_white - Convert images to black and white",
        "☀️ get_weather - Get current weather information"
    ]
    print("\n📋 Available Tools:")
    print("=" * 50)
    print("\n".join(f"  {tool}" for tool in tools_list))
    print("=" * 50)
    print("✅ Server ready for connections!")
    # SOURCERY: Replaced redundant f-string
    print("💡 Connect using: /mcp connect https://your-domain/mcp your_auth_token")
    print("") # Replaced f""
    await mcp.run_async("streamable-http", host="0.0.0.0", port=port)

if __name__ == "__main__":
    asyncio.run(main())