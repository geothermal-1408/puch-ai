import re
from enum import Enum
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class Mood(Enum):
    HAPPY = "happy"
    SAD = "sad"
    NEUTRAL = "neutral"
    ANGRY = "angry"
    EXCITED = "excited"


class Song(BaseModel):
    """Song data model"""
    title: str
    artist: str
    spotify_url: str
    genre: str = ""
    
    
class SongRecommendationEngine:
    """Engine for analyzing mood and recommending songs"""
    
    # Hardcoded curated playlists for each mood
    PLAYLISTS = {
        "happy": [
            {
                "title": "Happy", 
                "artist": "Pharrell Williams", 
                "spotify_url": "https://open.spotify.com/track/60nZcImufyMA1MKQY3dcCH",
                "genre": "Pop"
            },
            {
                "title": "Can't Stop the Feeling!", 
                "artist": "Justin Timberlake", 
                "spotify_url": "https://open.spotify.com/track/20I6sIOMTCkB6w7ryavxtO",
                "genre": "Pop"
            },
            {
                "title": "Good as Hell", 
                "artist": "Lizzo", 
                "spotify_url": "https://open.spotify.com/track/1PckUlxKqWQs3RlWXVBLw3",
                "genre": "Pop/R&B"
            },
            {
                "title": "Uptown Funk", 
                "artist": "Mark Ronson ft. Bruno Mars", 
                "spotify_url": "https://open.spotify.com/track/32OlwWuMpZ6b0aN2RZOeMS",
                "genre": "Funk/Pop"
            },
            {
                "title": "Walking on Sunshine", 
                "artist": "Katrina and the Waves", 
                "spotify_url": "https://open.spotify.com/track/05wIrZSwuaVWhcv5FfqeH0",
                "genre": "Pop/Rock"
            }
        ],
        "sad": [
            {
                "title": "Someone Like You", 
                "artist": "Adele", 
                "spotify_url": "https://open.spotify.com/track/4bHsxqR3GMrXTxEPLuK5ue",
                "genre": "Soul/Pop"
            },
            {
                "title": "Mad World", 
                "artist": "Gary Jules", 
                "spotify_url": "https://open.spotify.com/track/3JOVTQ5h8HGFnDdp4VT3MP",
                "genre": "Alternative"
            },
            {
                "title": "The Sound of Silence", 
                "artist": "Simon & Garfunkel", 
                "spotify_url": "https://open.spotify.com/track/7GElp5u1l2Xfgd5z8L8PaL",
                "genre": "Folk Rock"
            },
            {
                "title": "Hurt", 
                "artist": "Johnny Cash", 
                "spotify_url": "https://open.spotify.com/track/2o4H9vWfjkJWKlvr5wlZRX",
                "genre": "Country/Alternative"
            },
            {
                "title": "Black", 
                "artist": "Pearl Jam", 
                "spotify_url": "https://open.spotify.com/track/4XblTJYZEn4y3SXWNx9JRt",
                "genre": "Grunge/Alternative"
            }
        ],
        "angry": [
            {
                "title": "Break Stuff", 
                "artist": "Limp Bizkit", 
                "spotify_url": "https://open.spotify.com/track/5bIgwJD4kWQ4LVgUhvnEQs",
                "genre": "Nu Metal"
            },
            {
                "title": "Bodies", 
                "artist": "Drowning Pool", 
                "spotify_url": "https://open.spotify.com/track/4KNMTEhkEKmjZhb2Dn6VHh",
                "genre": "Nu Metal"
            },
            {
                "title": "Killing in the Name", 
                "artist": "Rage Against the Machine", 
                "spotify_url": "https://open.spotify.com/track/59WN2psjkt1tyaxjspN8fp",
                "genre": "Alternative Metal"
            },
            {
                "title": "Chop Suey!", 
                "artist": "System of a Down", 
                "spotify_url": "https://open.spotify.com/track/2DlHlPMa4M17kufBvI2lEN",
                "genre": "Alternative Metal"
            },
            {
                "title": "In the End", 
                "artist": "Linkin Park", 
                "spotify_url": "https://open.spotify.com/track/60a0Rd6pjrkxjPbaKzXjfq",
                "genre": "Nu Metal"
            }
        ],
        "excited": [
            {
                "title": "Thunder", 
                "artist": "Imagine Dragons", 
                "spotify_url": "https://open.spotify.com/track/0tBbt8CrmxbjRP0pueQkyU",
                "genre": "Alternative Rock"
            },
            {
                "title": "Pump It", 
                "artist": "The Black Eyed Peas", 
                "spotify_url": "https://open.spotify.com/track/7Jh1bpe76CNTCgdgAdBw4Z",
                "genre": "Hip Hop/Pop"
            },
            {
                "title": "Eye of the Tiger", 
                "artist": "Survivor", 
                "spotify_url": "https://open.spotify.com/track/2KH16WveTQWT6KOG9Rg6e2",
                "genre": "Rock"
            },
            {
                "title": "We Will Rock You", 
                "artist": "Queen", 
                "spotify_url": "https://open.spotify.com/track/4pbJqGIASGPr0ZpGpnWkDn",
                "genre": "Rock"
            },
            {
                "title": "Don't Stop Believin'", 
                "artist": "Journey", 
                "spotify_url": "https://open.spotify.com/track/4bHsxqR3GMrXTxEPLuK5ue",
                "genre": "Rock"
            }
        ],
        "neutral": [
            {
                "title": "Shape of You", 
                "artist": "Ed Sheeran", 
                "spotify_url": "https://open.spotify.com/track/7qiZfU4dY1lWllzX7mPBI3",
                "genre": "Pop"
            },
            {
                "title": "Blinding Lights", 
                "artist": "The Weeknd", 
                "spotify_url": "https://open.spotify.com/track/0VjIjW4GlULA0mG8km5iU8",
                "genre": "Synthwave/Pop"
            },
            {
                "title": "Watermelon Sugar", 
                "artist": "Harry Styles", 
                "spotify_url": "https://open.spotify.com/track/6UelLqGlWMcVH1E5c4H7lY",
                "genre": "Pop Rock"
            },
            {
                "title": "Levitating", 
                "artist": "Dua Lipa", 
                "spotify_url": "https://open.spotify.com/track/463CkQjx2Zk1yXoBuierM9",
                "genre": "Disco Pop"
            },
            {
                "title": "Stay", 
                "artist": "The Kid LAROI & Justin Bieber", 
                "spotify_url": "https://open.spotify.com/track/5HCyWlXZPP0y6Gqq8TgA20",
                "genre": "Pop"
            }
        ]
    }
    
    MOOD_KEYWORDS = {
        "happy": {
            "strong": ["ecstatic", "overjoyed", "thrilled", "elated", "euphoric"],
            "medium": ["happy", "joy", "excited", "great", "amazing", "wonderful", "fantastic", "cheerful"],
            "weak": ["good", "nice", "okay", "fine", "smile", "laugh", "love"]
        },
        "sad": {
            "strong": ["devastated", "heartbroken", "miserable", "depressed", "hopeless"],
            "medium": ["sad", "upset", "hurt", "lonely", "melancholy", "blue", "down"],
            "weak": ["miss", "lost", "cry", "disappointed", "tired"]
        },
        "angry": {
            "strong": ["furious", "enraged", "livid", "outraged", "seething"],
            "medium": ["angry", "mad", "hate", "frustrated", "rage", "pissed", "irritated"],
            "weak": ["annoyed", "bothered", "upset", "disappointed"]
        },
        "excited": {
            "strong": ["pumped", "hyped", "energized", "electrified", "fired up"],
            "medium": ["excited", "motivated", "ready", "intense", "adrenaline"],
            "weak": ["party", "celebration", "workout", "energy", "active"]
        },
        "neutral": {
            "strong": ["peaceful", "serene", "balanced", "content"],
            "medium": ["calm", "relaxed", "normal", "regular", "steady"],
            "weak": ["okay", "fine", "whatever", "meh", "alright"]
        }
    }
    
    @classmethod
    def analyze_mood(cls, text: str) -> tuple[str, float]:
        """
        Analyze text and return detected mood with confidence score
        Returns: (mood, confidence_score)
        """
        text_lower = text.lower()
        mood_scores = {mood: 0.0 for mood in cls.MOOD_KEYWORDS.keys()}
        
        for mood, categories in cls.MOOD_KEYWORDS.items():
            for category, keywords in categories.items():
                weight = {"strong": 3.0, "medium": 2.0, "weak": 1.0}[category]
                for keyword in keywords:
                    if keyword in text_lower:
                        mood_scores[mood] += weight
        
        detected_mood = max(mood_scores, key=mood_scores.get)
        max_score = mood_scores[detected_mood]
        
        total_score = sum(mood_scores.values())
        confidence = (max_score / total_score) if total_score > 0 else 0.0
        if max_score == 0:
            detected_mood = "neutral"
            confidence = 0.5
            
        return detected_mood, confidence
    
    @classmethod
    def get_recommendations(cls, mood: str, count: int = 5) -> List[Dict[str, Any]]:
        """Get song recommendations for a specific mood"""
        playlist = cls.PLAYLISTS.get(mood, cls.PLAYLISTS["neutral"])
        return playlist[:min(count, len(playlist))]
    
    @classmethod
    def get_all_moods(cls) -> List[str]:
        """Get list of all available moods"""
        return list(cls.PLAYLISTS.keys())
    
    @classmethod
    def format_recommendations(cls, user_text: str, mood: str, confidence: float, songs: List[Dict[str, Any]]) -> str:
        """Format the song recommendations as a nice string"""
        mood_emoji = {
            "happy": "😊",
            "sad": "😢", 
            "angry": "😠",
            "excited": "🚀",
            "neutral": "😐"
        }
        
        confidence_text = "high" if confidence > 0.7 else "medium" if confidence > 0.4 else "low"
        
        result = [
            f"🎵 **Song Recommendations Based on Your Mood**",
            f"",
            f"**Detected Mood:** {mood_emoji.get(mood, '🎵')} {mood.title()} (confidence: {confidence_text})",
            f"**Your Message:** \"{user_text}\"",
            f"",
            f"**🎧 Recommended Songs:**"
        ]
        
        for i, song in enumerate(songs, 1):
            result.append(f"{i}. **{song['title']}** by {song['artist']}")
            result.append(f"   🎭 Genre: {song.get('genre', 'Unknown')}")
            result.append(f"   🔗 [Listen on Spotify]({song['spotify_url']})")
            result.append("")
        
        result.extend([
            f"💡 **Tip:** Click the Spotify links to listen to these tracks!",
            f"🔄 Want different recommendations? Try specifying a different mood: {', '.join(cls.get_all_moods())}"
        ])
        
        return "\n".join(result)


def recommend_songs_for_text(user_text: str, mood_override: str = None, count: int = 5) -> str:
    """Main function to get song recommendations"""
    engine = SongRecommendationEngine()
    
    if mood_override and mood_override.lower() in engine.get_all_moods():
        mood = mood_override.lower()
        confidence = 1.0  
    else:
        mood, confidence = engine.analyze_mood(user_text)
    
    songs = engine.get_recommendations(mood, count)
    return engine.format_recommendations(user_text, mood, confidence, songs)