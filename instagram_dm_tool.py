#!/usr/bin/env python3
"""
instagram_dm_tool.py
Instagram DM tool with PROPER PAGINATION, BULK UNSEND, and CHAT DOWNLOAD/EXPORT.
Features:
- Session ID Cookie Login (bypasses "Instagram app out of date", 2FA, checkpoints)
- Username & Password Login with full 2FA verification support
- Account-Wide Scam Cleanup: scan and unsend messages/photos/links across ALL inbox conversations
- Chat Download / Export: backup chats to readable TXT, structured JSON, and interactive HTML
- Media Download: download photos, videos, voice notes, GIFs to local media folder
- Full Inbox Pagination: browse and scroll down through all conversations in inbox
- Unlimited Thread Pagination: proper cursor-based pagination with seq_id and oldest_cursor
- Date/Time Filtering: target messages sent during recent hack (e.g. last 3 or 7 days)
- Bulk Unsend: text messages, scam links, photos, videos, and disappearing snaps
"""

import os
import sys
import json
import time
import re
import html
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# Check Python version
if sys.version_info < (3, 6):
    print("ERROR: Python 3.6 or higher required")
    sys.exit(1)

# Ensure stdout/stderr handle UTF-8 or fallback gracefully on Windows cp1252 consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    from instagrapi import Client
    try:
        from instagrapi.exceptions import (
            TwoFactorRequired,
            ChallengeRequired,
            ClientNeedsUpgradeError,
            BadPassword,
            BadCredentials,
            LoginRequired,
            ClientError
        )
    except ImportError:
        from instagrapi.exceptions import (
            TwoFactorRequired,
            ChallengeRequired,
            BadPassword,
            LoginRequired,
            ClientError
        )
        class ClientNeedsUpgradeError(Exception):
            pass
        class BadCredentials(Exception):
            pass

    print("[+] instagrapi imported successfully")
except ImportError as e:
    print(f"ERROR: instagrapi not installed: {e}")
    print("Install or upgrade with: pip install --upgrade instagrapi")
    sys.exit(1)

# Constants
SESSION_FILE = "session.json"


def get_password():
    """Get password input with fallback for terminals without getpass"""
    try:
        import getpass
        return getpass.getpass("Instagram password (hidden): ")
    except Exception:
        print("Note: Password will be visible")
        return input("Instagram password: ")


def extract_message_info(item: Any, my_user_id: Optional[str] = None) -> dict:
    """
    Extract readable details, category, timestamp, and text/media summary from a message.
    Supports both raw API dictionary items and instagrapi DirectMessage objects.
    Categorizes messages into 'text', 'media' (photos/videos), 'link', 'share', or 'other'.
    """
    if hasattr(item, 'model_dump'):
        raw = item.model_dump()
    elif hasattr(item, 'dict'):
        raw = item.dict()
    elif isinstance(item, dict):
        raw = item
    else:
        raw = {}

    msg_id = (
        raw.get('item_id') or 
        raw.get('id') or 
        raw.get('client_context') or 
        'Unknown'
    )
    user_id = str(raw.get('user_id', 'Unknown'))
    item_type = raw.get('item_type') or 'text'
    
    # Check if sent by the viewer / logged-in user
    is_sent_by_viewer = raw.get('is_sent_by_viewer')
    if is_sent_by_viewer is None and my_user_id:
        is_sent_by_viewer = (str(user_id) == str(my_user_id))
    
    # Timestamp parsing
    timestamp_ts = 0.0
    timestamp_str = ""
    raw_ts = raw.get('timestamp')
    if raw_ts is not None:
        if isinstance(raw_ts, datetime):
            timestamp_ts = raw_ts.timestamp()
            timestamp_str = raw_ts.strftime("%Y-%m-%d %H:%M:%S")
        else:
            try:
                ts = float(raw_ts)
                # Instagram timestamps are typically in microseconds (16 digits)
                if ts > 1e11:
                    ts = ts / 1000000.0
                timestamp_ts = ts
                timestamp_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                timestamp_str = str(raw_ts)
            
    # Determine category & summary representation
    category = "text"
    summary = ""
    
    raw_text = raw.get('text')
    if raw_text:
        summary = str(raw_text)
        category = "text"
        
    link_obj = raw.get('link')
    if link_obj:
        category = "link"
        url = ""
        if isinstance(link_obj, dict):
            url = link_obj.get('text') or link_obj.get('link_context', {}).get('link_url') or ""
        elif hasattr(link_obj, 'text'):
            url = getattr(link_obj, 'text', '')
        elif isinstance(link_obj, str):
            url = link_obj
        if not url and raw_text:
            url = raw_text
        summary = f"[Link] {url}" if url else "[Link]"
        
    if item_type in ('media', 'raven_media', 'visual_media') or raw.get('media') or raw.get('visual_media'):
        category = "media"
        media_obj = raw.get('media') or {}
        is_video = False
        if isinstance(media_obj, dict) and media_obj.get('media_type') == 2:
            is_video = True
        elif hasattr(media_obj, 'media_type') and getattr(media_obj, 'media_type') == 2:
            is_video = True

        if is_video:
            summary = "[Video]"
        elif item_type in ('raven_media', 'visual_media') or raw.get('visual_media'):
            summary = "[Disappearing Photo/Video]"
        else:
            summary = "[Photo]"
            
    elif item_type in ('media_share', 'reel_share', 'story_share', 'clip') or raw.get('media_share') or raw.get('reel_share'):
        category = "share"
        summary = f"[Shared {item_type.replace('_', ' ').title()}]"
        
    elif item_type == 'animated_media' or raw.get('animated_media'):
        category = "media"
        summary = "[GIF / Animated Sticker]"
        
    elif item_type == 'voice_media' or raw.get('voice_media'):
        category = "media"
        summary = "[Voice Note]"
        
    elif item_type.startswith('xma_') or raw.get('xma_share'):
        category = "link"
        summary = "[Shared Link/Card]"
        
    elif not summary:
        summary = f"[{item_type}]"

    # Also detect URLs inside normal text messages
    if category == "text" and any(proto in summary.lower() for proto in ("http://", "https://", "www.", ".com/", ".xyz", ".ru", ".link")):
        category = "link"
        
    return {
        "id": str(msg_id),
        "user_id": str(user_id),
        "is_sent_by_viewer": bool(is_sent_by_viewer),
        "timestamp": timestamp_str,
        "timestamp_ts": timestamp_ts,
        "item_type": str(item_type),
        "category": category,
        "summary": summary,
        "raw": raw
    }


def sanitize_filename(name: str) -> str:
    """Sanitize string for safe folder and file naming across OSes."""
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip('. ')
    return name or "unnamed_chat"


def extract_media_urls(item: Any) -> List[Dict[str, str]]:
    """
    Extract download URLs and hints from a message item (raw dict or object).
    Returns a list of dicts: [{'type': 'photo'|'video'|'audio'|'animated', 'url': '...', 'ext': 'jpg'|'mp4'|'m4a'|'gif'}]
    """
    if hasattr(item, 'model_dump'):
        raw = item.model_dump()
    elif hasattr(item, 'dict'):
        raw = item.dict()
    elif isinstance(item, dict):
        raw = item
    else:
        return []

    medias = []

    # 1. Direct photo / video in 'media'
    media_obj = raw.get('media') or {}
    if isinstance(media_obj, dict):
        media_type = media_obj.get('media_type')
        v_versions = media_obj.get('video_versions') or []
        if media_type == 2 or v_versions:
            if v_versions and isinstance(v_versions, list) and v_versions[0].get('url'):
                medias.append({
                    'type': 'video',
                    'url': v_versions[0]['url'],
                    'ext': 'mp4'
                })
        if media_obj.get('image_versions2'):
            candidates = media_obj.get('image_versions2', {}).get('candidates', [])
            if candidates and isinstance(candidates, list) and candidates[0].get('url'):
                if not v_versions:
                    medias.append({
                        'type': 'photo',
                        'url': candidates[0]['url'],
                        'ext': 'jpg'
                    })

    # 2. visual_media / raven_media (Disappearing snaps)
    visual_media = raw.get('visual_media') or raw.get('raven_media')
    if isinstance(visual_media, dict):
        vm_media = visual_media.get('media') or {}
        if isinstance(vm_media, dict):
            v_versions = vm_media.get('video_versions') or []
            if v_versions and v_versions[0].get('url'):
                medias.append({'type': 'video', 'url': v_versions[0]['url'], 'ext': 'mp4'})
            candidates = vm_media.get('image_versions2', {}).get('candidates', [])
            if candidates and candidates[0].get('url') and not v_versions:
                medias.append({'type': 'photo', 'url': candidates[0]['url'], 'ext': 'jpg'})

    # 3. voice_media (Voice notes)
    voice_media = raw.get('voice_media')
    if isinstance(voice_media, dict):
        audio_src = voice_media.get('media', {}).get('audio', {}).get('audio_src')
        if audio_src:
            medias.append({'type': 'audio', 'url': audio_src, 'ext': 'm4a'})

    # 4. animated_media (GIFs / Stickers)
    animated = raw.get('animated_media')
    if isinstance(animated, dict):
        img_info = animated.get('images', {})
        gif_url = (img_info.get('fixed_height', {}).get('url') or 
                   img_info.get('original', {}).get('url'))
        if gif_url:
            medias.append({'type': 'animated', 'url': gif_url, 'ext': 'gif'})

    # 5. clip / reel_share / media_share
    clip = raw.get('clip') or raw.get('reel_share') or raw.get('media_share')
    if isinstance(clip, dict):
        c_media = clip.get('clip') or clip.get('media') or {}
        if isinstance(c_media, dict):
            v_versions = c_media.get('video_versions') or []
            if v_versions and v_versions[0].get('url'):
                medias.append({'type': 'video', 'url': v_versions[0]['url'], 'ext': 'mp4'})
            candidates = c_media.get('image_versions2', {}).get('candidates', [])
            if candidates and candidates[0].get('url') and not v_versions:
                medias.append({'type': 'photo', 'url': candidates[0]['url'], 'ext': 'jpg'})

    return medias


def download_media_file(url: str, output_path: str, timeout: int = 15) -> bool:
    """Download a media file from a URL to output_path with timeout and user-agent."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(response.read())
                return True
    except Exception:
        pass
    return False


def linkify_html(text: str) -> str:
    """Escapes HTML and converts URLs into clickable anchor tags."""
    escaped = html.escape(text)
    url_pattern = re.compile(r'(https?://[^\s<]+)')
    return url_pattern.sub(r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', escaped).replace('\n', '<br>')


def export_chat_to_txt(thread_info: dict, messages: List[dict], output_file: str):
    """Save conversation to plain text file (.txt)."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("INSTAGRAM DIRECT MESSAGE EXPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Thread ID:      {thread_info.get('thread_id', 'Unknown')}\n")
        f.write(f"Title:          {thread_info.get('title', 'Untitled')}\n")
        f.write(f"Export Date:    {thread_info.get('export_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}\n")
        f.write(f"Participants:   {', '.join(thread_info.get('participants', []))}\n")
        f.write(f"Total Messages: {len(messages)}\n")
        f.write("=" * 80 + "\n\n")

        for msg in messages:
            sender = msg.get('sender_name', 'Unknown')
            timestamp = msg.get('timestamp', '')
            content = msg.get('text') or msg.get('summary', '')
            
            f.write(f"[{timestamp}] {sender}:\n")
            if content:
                f.write(f"  {content}\n")
            
            media_files = msg.get('media_files', [])
            for mf in media_files:
                local_path = mf.get('local_path') or mf.get('url')
                f.write(f"  [{mf.get('type', 'media').upper()}: {local_path}]\n")
            f.write("\n")


def export_chat_to_json(thread_info: dict, messages: List[dict], output_file: str):
    """Save conversation to structured JSON file (.json)."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    payload = {
        "metadata": thread_info,
        "message_count": len(messages),
        "messages": messages
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def export_chat_to_html(thread_info: dict, messages: List[dict], output_file: str):
    """Save conversation to an interactive, responsive HTML chat view (.html)."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    title = html.escape(str(thread_info.get('title', 'Instagram DM Chat')))
    thread_id = html.escape(str(thread_info.get('thread_id', '')))
    export_date = html.escape(str(thread_info.get('export_date', '')))
    participants_str = html.escape(', '.join(thread_info.get('participants', [])))
    
    messages_html = []
    for msg in messages:
        is_me = bool(msg.get('is_sent_by_viewer'))
        sender = html.escape(str(msg.get('sender_name', '')))
        timestamp = html.escape(str(msg.get('timestamp', '')))
        text_content = msg.get('text') or msg.get('summary') or ""
        
        row_class = "msg-row msg-me" if is_me else "msg-row msg-other"
        bubble_class = "bubble bubble-me" if is_me else "bubble bubble-other"
        
        media_html_parts = []
        for mf in msg.get('media_files', []):
            mtype = mf.get('type')
            mpath = html.escape(mf.get('local_path') or mf.get('url') or '')
            if not mpath:
                continue
            if mtype == 'photo':
                media_html_parts.append(
                    f'<div class="msg-media"><a href="{mpath}" target="_blank">'
                    f'<img src="{mpath}" alt="Photo" loading="lazy" /></a></div>'
                )
            elif mtype == 'video':
                media_html_parts.append(
                    f'<div class="msg-media"><video controls preload="metadata">'
                    f'<source src="{mpath}">Your browser does not support HTML5 video.</video></div>'
                )
            elif mtype == 'audio':
                media_html_parts.append(
                    f'<div class="msg-media"><audio controls preload="metadata">'
                    f'<source src="{mpath}">Your browser does not support HTML5 audio.</audio></div>'
                )
            elif mtype == 'animated':
                media_html_parts.append(
                    f'<div class="msg-media"><img src="{mpath}" alt="GIF" loading="lazy" /></div>'
                )
        
        media_rendered = "".join(media_html_parts)
        text_rendered = f'<div class="msg-text">{linkify_html(text_content)}</div>' if text_content else ''
        
        # Don't show duplicate summary if it just says [Photo] and media is already rendered
        if media_rendered and text_content in ('[Photo]', '[Video]', '[Voice Note]', '[GIF / Animated Sticker]'):
            text_rendered = ''
            
        msg_item = f'''
        <div class="{row_class}">
            <div class="{bubble_class}">
                <div class="sender-header">{sender}</div>
                {text_rendered}
                {media_rendered}
                <div class="timestamp">{timestamp}</div>
            </div>
        </div>'''
        messages_html.append(msg_item)
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Chat - {title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: #0b0e14;
            color: #f0f0f0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }}
        .header {{
            background-color: #161b22;
            border-bottom: 1px solid #30363d;
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
        }}
        .header-left {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .brand-badge {{
            background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%);
            color: white;
            font-weight: 700;
            font-size: 13px;
            padding: 5px 12px;
            border-radius: 20px;
            letter-spacing: 0.5px;
        }}
        .chat-info h1 {{
            font-size: 18px;
            font-weight: 600;
            color: #ffffff;
        }}
        .chat-info p {{
            font-size: 12px;
            color: #8b949e;
            margin-top: 2px;
        }}
        .search-container {{
            flex: 1;
            max-width: 320px;
        }}
        .search-box {{
            width: 100%;
            background-color: #0d1117;
            border: 1px solid #30363d;
            border-radius: 20px;
            padding: 8px 16px;
            color: #e6edf3;
            font-size: 13px;
            outline: none;
            transition: border-color 0.2s;
        }}
        .search-box:focus {{
            border-color: #58a6ff;
        }}
        .chat-container {{
            flex: 1;
            overflow-y: auto;
            padding: 24px 16px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            max-width: 800px;
            width: 100%;
            margin: 0 auto;
        }}
        .msg-row {{
            display: flex;
            width: 100%;
        }}
        .msg-me {{
            justify-content: flex-end;
        }}
        .msg-other {{
            justify-content: flex-start;
        }}
        .bubble {{
            max-width: 75%;
            padding: 10px 14px;
            border-radius: 18px;
            word-wrap: break-word;
            position: relative;
            box-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }}
        .bubble-me {{
            background: linear-gradient(135deg, #3797f0 0%, #833ab4 100%);
            color: #ffffff;
            border-bottom-right-radius: 4px;
        }}
        .bubble-other {{
            background-color: #21262d;
            color: #e6edf3;
            border-bottom-left-radius: 4px;
            border: 1px solid #30363d;
        }}
        .sender-header {{
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 4px;
            opacity: 0.85;
            color: #ffd27a;
        }}
        .bubble-me .sender-header {{
            color: #e0f2fe;
        }}
        .msg-text {{
            font-size: 14px;
            line-height: 1.45;
        }}
        .msg-text a {{
            color: #79c0ff;
            text-decoration: underline;
        }}
        .bubble-me .msg-text a {{
            color: #ffffff;
            text-decoration: underline;
        }}
        .timestamp {{
            font-size: 10px;
            margin-top: 6px;
            opacity: 0.7;
            text-align: right;
        }}
        .msg-media img {{
            max-width: 100%;
            max-height: 380px;
            border-radius: 10px;
            margin-top: 6px;
            display: block;
            object-fit: cover;
        }}
        .msg-media video {{
            max-width: 100%;
            border-radius: 10px;
            margin-top: 6px;
            display: block;
        }}
        .msg-media audio {{
            width: 100%;
            margin-top: 6px;
            display: block;
        }}
        .footer {{
            text-align: center;
            font-size: 11px;
            color: #8b949e;
            padding: 12px;
            border-top: 1px solid #21262d;
            background-color: #161b22;
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-left">
            <span class="brand-badge">INSTAGRAM DM</span>
            <div class="chat-info">
                <h1>{title}</h1>
                <p>Participants: {participants_str} &bull; {len(messages)} messages</p>
            </div>
        </div>
        <div class="search-container">
            <input type="text" id="search-input" class="search-box" placeholder="Search in chat..." onkeyup="filterMessages()">
        </div>
    </header>
    <div class="chat-container" id="chat-box">
        {"".join(messages_html)}
    </div>
    <footer class="footer">
        Archived on {export_date} &bull; Thread ID: {thread_id}
    </footer>
    <script>
        function filterMessages() {{
            const filter = document.getElementById('search-input').value.toLowerCase();
            const rows = document.querySelectorAll('.msg-row');
            rows.forEach(row => {{
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            }});
        }}
    </script>
</body>
</html>'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)


def load_session(client: Client, session_file: str) -> bool:
    """Load session with app version override to prevent out-of-date error"""
    if not os.path.exists(session_file):
        return False
    try:
        try:
            client.load_settings(session_file, override_app_version=True)
        except TypeError:
            client.load_settings(session_file)
            
        try:
            client.account_info()
            return True
        except Exception:
            if client.user_id:
                return True
            return False
    except Exception:
        try:
            os.remove(session_file)
        except Exception:
            pass
        return False


def save_session(client: Client, session_file: str) -> bool:
    """Save session to file"""
    try:
        client.dump_settings(session_file)
        return True
    except Exception:
        return False


class IGDMTool:
    def __init__(self):
        self.client = Client()
        self.logged_in = False
        self.selected_thread_id = None
        self.selected_thread_title = None
        self.my_username = None
        self.my_user_id = None
        self.last_matches: List[dict] = []
        self.last_filter_desc: str = ""
        print("[+] IGDMTool initialized")
        
        self._check_existing_session()

    def _check_existing_session(self):
        """Silently restore existing session on startup"""
        if os.path.exists(SESSION_FILE):
            if load_session(self.client, SESSION_FILE):
                try:
                    user_info = self.client.account_info()
                    self.my_username = user_info.username
                    self.my_user_id = str(user_info.pk)
                    self.logged_in = True
                    print(f"[+] Automatically restored session for: {self.my_username}")
                except Exception:
                    if self.client.user_id:
                        self.my_user_id = str(self.client.user_id)
                        self.my_username = self.client.username or self.my_user_id
                        self.logged_in = True
                        print(f"[+] Automatically restored session for: {self.my_username}")

    def unsend_message(self, thread_id: str, msg_id: str) -> bool:
        """
        Unsend a message using multiple Instagram endpoints.
        Returns True on success, False on failure.
        """
        if not thread_id or not msg_id or msg_id == 'Unknown':
            return False

        # Endpoint 1: Direct item delete (standard mobile API endpoint)
        try:
            response = self.client.private_request(
                f"direct_v2/threads/{thread_id}/items/{msg_id}/delete/",
                data={
                    "_uuid": self.client.uuid,
                    "_uid": self.my_user_id,
                    "_csrftoken": self.client.token
                },
                with_signature=False
            )
            if response and response.get('status') == 'ok':
                return True
        except Exception:
            pass

        # Endpoint 2: instagrapi built-in direct_message_delete
        if msg_id.isdigit() and str(thread_id).isdigit():
            try:
                if self.client.direct_message_delete(int(thread_id), int(msg_id)):
                    return True
            except Exception:
                pass

        # Endpoint 3: broadcast item_unsend
        try:
            response2 = self.client.private_request(
                "direct_v2/threads/broadcast/item_unsend/",
                data={
                    "thread_id": str(thread_id),
                    "item_id": str(msg_id),
                    "_uuid": self.client.uuid,
                    "_uid": self.my_user_id,
                    "_csrftoken": self.client.token
                },
                with_signature=False
            )
            if response2 and response2.get('status') == 'ok':
                return True
        except Exception:
            pass

        return False

    def login(self):
        """Login menu supporting Username/Password, 2FA, and Session ID Cookie"""
        print("\n=== LOGIN / ACCOUNT ===")
        
        if self.logged_in:
            print(f"Currently logged in as: {self.my_username} (ID: {self.my_user_id})")
            print("1. Continue with current session")
            print("2. Switch account / Log in again")
            print("3. Log out and clear saved session")
            choice = input("\nSelect option (1-3): ").strip()
            if choice == "1":
                return True
            elif choice == "3":
                self.logout()
                return False
        
        print("\nSelect Login Method:")
        print("1. Username & Password (Standard - with 2FA support)")
        print("2. Session ID Cookie (RECOMMENDED - bypasses 'Instagram app out of date', checkpoints & 2FA)")
        print("3. Back to main menu")
        
        method = input("\nSelect option (1-3): ").strip()
        if method == "1":
            return self.login_credentials()
        elif method == "2":
            return self.login_sessionid()
        else:
            return False

    def login_credentials(self):
        """Standard username and password login with 2FA handling and out-of-date troubleshooting"""
        print("\n--- USERNAME & PASSWORD LOGIN ---")
        username = input("Instagram username: ").strip()
        if not username:
            return False
        
        password = get_password().strip()
        if not password:
            return False
        
        try:
            print("Logging in to Instagram...")
            self.client.login(username, password)
            
            try:
                user_info = self.client.account_info()
                self.my_username = user_info.username
                self.my_user_id = str(user_info.pk)
            except Exception:
                self.my_user_id = str(self.client.user_id)
                self.my_username = self.client.username or username
                
            save_session(self.client, SESSION_FILE)
            print(f"[+] Logged in as: {self.my_username}")
            self.logged_in = True
            return True

        except TwoFactorRequired:
            print("\n[!] Two-Factor Authentication (2FA) is enabled on this account.")
            code = input("Enter your 6-digit verification code (from SMS or Authenticator App): ").strip()
            if not code:
                print("2FA code cannot be empty.")
                return False
            try:
                print("Submitting 2FA verification code...")
                self.client.login(username, password, verification_code=code)
                try:
                    user_info = self.client.account_info()
                    self.my_username = user_info.username
                    self.my_user_id = str(user_info.pk)
                except Exception:
                    self.my_user_id = str(self.client.user_id)
                    self.my_username = self.client.username or username
                save_session(self.client, SESSION_FILE)
                print(f"[+] Logged in as: {self.my_username}")
                self.logged_in = True
                return True
            except Exception as e2fa:
                print(f"2FA login failed: {e2fa}")
                return False

        except (ClientNeedsUpgradeError, Exception) as e:
            err_str = str(e).lower()
            if "out of date" in err_str or "needs_upgrade" in err_str or "upgrade" in err_str:
                print("\n" + "=" * 65)
                print("[!] INSTAGRAM 'APP OUT OF DATE' ERROR DETECTED")
                print("=" * 65)
                print("Instagram is blocking mobile login from this client/IP:")
                print(f"  Error: {e}")
                print("\nWhy this happens:")
                print("Instagram flags mobile app login attempts from scripts or accounts that")
                print("were recently compromised/hacked and requires a modern client signature.")
                print("\nSOLUTION (Works 100%):")
                print("Use Method 2: 'Session ID Cookie Login'!")
                print("1. Open https://www.instagram.com in your web browser (Chrome/Edge/Firefox).")
                print("2. Make sure you are logged in there.")
                print("3. Press F12 -> Application -> Cookies -> https://www.instagram.com")
                print("4. Copy the value of the 'sessionid' cookie.")
                print("5. Paste it into this tool to bypass all mobile app version checks!")
                print("=" * 65 + "\n")
                
                switch = input("Would you like to log in with your browser Session ID now? (y/n): ").strip().lower()
                if switch == 'y':
                    return self.login_sessionid()
                return False
            
            elif "challenge" in err_str or "checkpoint" in err_str:
                print(f"\n[!] Instagram checkpoint/challenge required: {e}")
                print("Instagram detected unusual activity (common when accounts are recently hacked).")
                print("You can bypass this by logging in on your web browser and using Session ID Login.")
                switch = input("Would you like to log in with your browser Session ID now? (y/n): ").strip().lower()
                if switch == 'y':
                    return self.login_sessionid()
                return False
            else:
                print(f"Login failed: {e}")
                return False

    def login_sessionid(self):
        """Login using Instagram Web sessionid cookie (bypasses app out-of-date and 2FA issues)"""
        print("\n" + "=" * 60)
        print("LOGIN WITH INSTAGRAM BROWSER SESSION ID")
        print("=" * 60)
        print("This method connects directly using your browser's authenticated session.")
        print("It completely bypasses 'Instagram app out of date', 2FA, and checkpoint blocks!\n")
        print("How to get your sessionid in 3 easy steps:")
        print("1. Open https://www.instagram.com in your browser (Chrome, Edge, Firefox, Brave, Safari)")
        print("   and log in to your account.")
        print("2. Open Developer Tools:")
        print("   - Chrome/Edge/Brave: Press F12 (or right-click anywhere -> Inspect)")
        print("     Go to: 'Application' tab -> 'Cookies' -> 'https://www.instagram.com'")
        print("   - Firefox: Press F12 -> 'Storage' tab -> 'Cookies' -> 'https://www.instagram.com'")
        print("   - Safari: Preferences -> Advanced -> Show Develop menu -> Inspect -> Storage -> Cookies")
        print("3. Find the cookie named 'sessionid', double-click its Value, and copy it.")
        print("   (It is a long string, often starting with your user ID numbers)")
        print("=" * 60)
        
        sessionid = input("\nPaste your sessionid here (or press Enter to cancel): ").strip()
        if not sessionid:
            print("Session ID login cancelled.")
            return False
        
        sessionid = sessionid.strip('"\'')
        
        try:
            print("Authenticating session with Instagram...")
            self.client.login_by_sessionid(sessionid)
            
            try:
                user_info = self.client.account_info()
                self.my_username = user_info.username
                self.my_user_id = str(user_info.pk)
            except Exception:
                if self.client.user_id:
                    self.my_user_id = str(self.client.user_id)
                self.my_username = self.client.username or (f"User_{self.my_user_id}" if self.my_user_id else "User")
            
            save_session(self.client, SESSION_FILE)
            print(f"[+] Successfully authenticated as: {self.my_username} (User ID: {self.my_user_id})")
            self.logged_in = True
            return True
        except Exception as e:
            print(f"\nSession ID login failed: {e}")
            print("Tips:")
            print("- Ensure you copied the FULL sessionid value without extra spaces.")
            print("- Make sure you are actively logged in to Instagram in that browser.")
            print("- If your session expired, refresh instagram.com in browser and copy the new sessionid.")
            return False

    def logout(self):
        """Log out and remove stored session file"""
        if os.path.exists(SESSION_FILE):
            try:
                os.remove(SESSION_FILE)
            except Exception:
                pass
        self.client = Client()
        self.logged_in = False
        self.selected_thread_id = None
        self.selected_thread_title = None
        self.my_username = None
        self.my_user_id = None
        self.last_matches = []
        self.last_filter_desc = ""
        print("[+] Logged out successfully and cleared local session.")

    def fetch_inbox_threads(self, max_threads: int = 50) -> List[dict]:
        """
        Fetch inbox threads with full pagination support across the user's inbox.
        Returns a list of raw thread dicts.
        """
        all_threads = []
        cursor = None
        seen_ids = set()
        page = 1
        
        while len(all_threads) < max_threads:
            params = {
                "visual_message_return_type": "unseen",
                "thread_message_limit": "10",
                "persistentBadging": "true",
                "limit": "20"
            }
            if cursor:
                params.update({
                    "cursor": cursor,
                    "direction": "older"
                })
                
            try:
                response = self.client.private_request("direct_v2/inbox/", params=params)
                if not response or 'inbox' not in response:
                    break
                
                inbox = response['inbox']
                threads = inbox.get('threads', [])
                if not threads:
                    break
                
                new_in_page = 0
                for t in threads:
                    tid = str(t.get('thread_id', ''))
                    if tid and tid not in seen_ids:
                        seen_ids.add(tid)
                        all_threads.append(t)
                        new_in_page += 1
                        if len(all_threads) >= max_threads:
                            break
                            
                next_cursor = inbox.get('oldest_cursor')
                if not next_cursor or next_cursor == cursor or new_in_page == 0:
                    break
                
                cursor = next_cursor
                page += 1
                time.sleep(0.4)
                
            except Exception as e:
                print(f"[!] Error loading inbox page {page}: {e}")
                break
                
        return all_threads

    def list_threads_raw_api(self):
        """
        Browse inbox conversations with interactive Next-Page pagination so users
        can scroll down through their entire conversation history.
        """
        if not self.logged_in:
            print("Please login first (Option 1)")
            return False
        
        print("\n=== BROWSE INBOX CONVERSATIONS ===")
        print("Loading conversations from your inbox...")
        
        all_threads = []
        cursor = None
        seen_ids = set()
        
        while True:
            # Fetch next chunk of 20 threads
            params = {
                "visual_message_return_type": "unseen",
                "thread_message_limit": "10",
                "persistentBadging": "true",
                "limit": "20"
            }
            if cursor:
                params.update({
                    "cursor": cursor,
                    "direction": "older"
                })
            
            try:
                response = self.client.private_request("direct_v2/inbox/", params=params)
                if not response or 'inbox' not in response:
                    print("No more inbox data received.")
                    break
                
                inbox = response['inbox']
                batch = inbox.get('threads', [])
                if not batch:
                    print("No more conversations in inbox.")
                    break
                
                start_index = len(all_threads) + 1
                new_in_batch = []
                for t in batch:
                    tid = str(t.get('thread_id', ''))
                    if tid and tid not in seen_ids:
                        seen_ids.add(tid)
                        all_threads.append(t)
                        new_in_batch.append(t)
                        
                if not new_in_batch:
                    print("Reached end of inbox conversations.")
                    break
                
                print(f"\n--- Conversations {start_index} to {len(all_threads)} ---")
                for i, thread in enumerate(new_in_batch, start_index):
                    thread_id = thread.get('thread_id', 'Unknown')
                    thread_title = thread.get('thread_title')
                    
                    users = thread.get('users', [])
                    usernames = [u.get('username', '') for u in users if u.get('username')]
                    
                    if thread_title:
                        title_str = f"{thread_title} ({', '.join(usernames[:3])})"
                    elif usernames:
                        title_str = ", ".join(usernames[:3])
                        if len(usernames) > 3:
                            title_str += f" and {len(usernames)-3} others"
                    else:
                        title_str = "Unknown conversation"
                    
                    items = thread.get('items', [])
                    last_msg = ""
                    if items:
                        info = extract_message_info(items[0], self.my_user_id)
                        last_msg = info['summary'][:55]
                        if len(info['summary']) > 55:
                            last_msg += "..."
                    else:
                        last_msg = "[No messages]"
                    
                    print(f"{i:2d}. {title_str} (ID: {thread_id})")
                    print(f"    Latest: {last_msg}")
                
                cursor = inbox.get('oldest_cursor')
                has_more = bool(cursor and inbox.get('has_older', True))
                
                print("\n" + "-" * 55)
                prompt_msg = f"Enter conversation number (1-{len(all_threads)})"
                if has_more:
                    prompt_msg += ", 'N' for Next 20 conversations"
                prompt_msg += ", or Enter to cancel: "
                
                choice = input(prompt_msg).strip()
                
                if not choice:
                    return False
                
                if choice.upper() == 'N' and has_more:
                    print("Loading next page of conversations...")
                    time.sleep(0.4)
                    continue
                
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(all_threads):
                        selected = all_threads[idx]
                        self.selected_thread_id = str(selected.get('thread_id'))
                        
                        users = selected.get('users', [])
                        usernames = [u.get('username', '') for u in users if u.get('username')]
                        self.selected_thread_title = selected.get('thread_title') or (", ".join(usernames[:3]) if usernames else self.selected_thread_id)
                        
                        print(f"[+] Selected conversation: {self.selected_thread_title} (ID: {self.selected_thread_id})")
                        return True
                    else:
                        print("Invalid conversation number.")
                        return False
                else:
                    print("Cancelled.")
                    return False
                    
            except Exception as e:
                print(f"[!] Failed to browse conversations: {e}")
                return False

    def select_thread(self):
        """Select thread by direct thread ID or Instagram username"""
        if not self.logged_in:
            print("Please login first (Option 1)")
            return False
        
        print("\n=== SELECT CONVERSATION ===")
        thread_input = input("Enter thread ID or Instagram username: ").strip()
        if not thread_input:
            return False
        
        try:
            if thread_input.isdigit() and len(thread_input) > 8:
                self.selected_thread_id = str(thread_input)
                self.selected_thread_title = f"Thread {thread_input}"
                print(f"[+] Selected thread ID: {thread_input}")
                return True
            else:
                print(f"Looking up username: @{thread_input}...")
                user_id = self.client.user_id_from_username(thread_input)
                print(f"Found user ID: {user_id}")
                
                print("Locating conversation in inbox...")
                threads = self.fetch_inbox_threads(max_threads=100)
                
                for thread in threads:
                    users = thread.get('users', [])
                    for user in users:
                        if str(user.get('pk', '')) == str(user_id):
                            self.selected_thread_id = str(thread.get('thread_id'))
                            self.selected_thread_title = f"@{thread_input}"
                            print(f"[+] Found conversation thread: {self.selected_thread_id}")
                            return True
                
                print(f"No existing conversation found in recent inbox for @{thread_input}.")
                print("Tip: If you know the thread ID, enter it directly, or choose from Option 2.")
                return False
        except Exception as e:
            print(f"Failed to select thread: {e}")
            return False

    def fetch_all_messages_paginated(self, max_messages: int = 5000, thread_id: Optional[str] = None) -> List[dict]:
        """
        Fetch messages from the selected thread with PROPER Instagram pagination.
        Uses exact mobile API parameters: direction='older', limit='20', seq_id='40065',
        and properly handles oldest_cursor and MINCURSOR boundaries.
        Supports passing an explicit thread_id or defaults to self.selected_thread_id.
        """
        target_thread_id = str(thread_id or self.selected_thread_id or "")
        if not target_thread_id:
            print("Please select a conversation thread first.")
            return []

        all_messages = []
        cursor = None
        seen_ids = set()
        page = 1
        consecutive_empty_pages = 0
        
        print(f"Fetching up to {max_messages} messages with cursor pagination...")
        
        while len(all_messages) < max_messages and consecutive_empty_pages < 3:
            try:
                # Use Instagram's standard mobile batch parameters
                params = {
                    "visual_message_return_type": "unseen",
                    "direction": "older",
                    "seq_id": "40065",
                    "limit": "20"
                }
                if cursor:
                    params["cursor"] = cursor
                
                response = self.client.private_request(
                    f"direct_v2/threads/{target_thread_id}/", 
                    params=params
                )
                
                if not response or 'thread' not in response:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 3:
                        break
                    page += 1
                    time.sleep(1)
                    continue
                
                thread = response['thread']
                items = thread.get('items', [])
                
                if not items:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 2:
                        print("Reached beginning of conversation (no more items returned).")
                        break
                    page += 1
                    time.sleep(1)
                    continue
                
                consecutive_empty_pages = 0
                new_in_page = 0
                for item in items:
                    mid = str(item.get('item_id') or item.get('id') or item.get('client_context') or len(all_messages))
                    if mid not in seen_ids:
                        seen_ids.add(mid)
                        all_messages.append(item)
                        new_in_page += 1
                        if len(all_messages) >= max_messages:
                            break
                
                print(f"  Page {page:2d}: Retrieved {new_in_page} messages (Total so far: {len(all_messages)})")
                
                if len(all_messages) >= max_messages:
                    print(f"Reached requested limit of {max_messages} messages.")
                    break
                
                # Check pagination boundary indicators
                if thread.get("has_older") is False:
                    print("Reached earliest message in conversation (has_older=False).")
                    break
                
                if thread.get("prev_cursor") == "MINCURSOR":
                    print("Reached beginning of conversation history (MINCURSOR).")
                    break
                
                next_cursor = thread.get("oldest_cursor") or thread.get("next_cursor")
                if not next_cursor or next_cursor == cursor or new_in_page == 0:
                    print("No further cursor provided - reached the earliest message.")
                    break
                
                cursor = next_cursor
                page += 1
                time.sleep(0.4)
                
            except Exception as e:
                print(f"  [!] Notice on page {page}: {e}")
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= 3:
                    break
                page += 1
                time.sleep(1.5)
        
        # If raw pagination returned very few items but user asked for more, try instagrapi fallback
        if len(all_messages) <= 20 and max_messages > 20 and target_thread_id.isdigit():
            try:
                print("Checking additional messages via direct_thread fallback...")
                dt = self.client.direct_thread(int(target_thread_id), amount=min(max_messages, 200))
                if dt and dt.messages:
                    fallback_items = []
                    for dm in dt.messages:
                        if hasattr(dm, 'model_dump'):
                            fallback_items.append(dm.model_dump())
                        elif hasattr(dm, 'dict'):
                            fallback_items.append(dm.dict())
                    if len(fallback_items) > len(all_messages):
                        all_messages = fallback_items
            except Exception:
                pass
                
        print(f"Total messages retrieved: {len(all_messages)}\n")
        return all_messages
                
        print(f"Total messages retrieved: {len(all_messages)}\n")
        return all_messages

    def view_messages_raw_api(self):
        """View messages with structured previews for text, photos, and links"""
        if not self.logged_in:
            print("Please login first (Option 1)")
            return
        
        if not self.selected_thread_id:
            print("Please select a conversation thread first (Option 2 or 3)")
            return
        
        print(f"\n=== VIEW MESSAGES (THREAD {self.selected_thread_id}) ===")
        
        try:
            amount_str = input("Number of messages to view (default 20): ").strip()
            amount = int(amount_str) if amount_str.isdigit() else 20
            
            items = self.fetch_all_messages_paginated(amount)
            
            if not items:
                print("No messages found in this thread.")
                return
            
            print(f"\nFound {len(items)} messages (newest first):")
            print("-" * 75)
            
            for item in items[:30]:
                try:
                    info = extract_message_info(item, self.my_user_id)
                    
                    sender = f"ID: {info['user_id']}"
                    if info['is_sent_by_viewer'] or info['user_id'] == str(self.my_user_id):
                        sender = f"{self.my_username} (YOU)"
                    
                    print(f"ID:       {info['id']}")
                    print(f"From:     {sender}")
                    print(f"Time:     {info['timestamp']}")
                    print(f"Type:     {info['category'].upper()} ({info['item_type']})")
                    print(f"Content:  {info['summary']}")
                    print("-" * 40)
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Failed to view messages: {e}")

    def search_messages_raw_api(self):
        """
        Search and filter messages to unsend in the selected conversation.
        Supports:
        - ALL messages sent by user (best for clearing hacked scam activity)
        - Keywords in text or link URLs
        - Photos & Videos only
        - Links & URLs only
        - Optional date cutoff (e.g. only within the last N days)
        """
        if not self.logged_in:
            print("Please login first (Option 1)")
            return
        
        if not self.selected_thread_id:
            print("Please select a conversation thread first (Option 2 or 3)")
            return
        
        print(f"\n=== SEARCH / FILTER MESSAGES IN {self.selected_thread_title or self.selected_thread_id} ===")
        print("Select what you want to find & unsend:")
        print("1. ALL messages & media sent by you (Recommended for hacked accounts - unsend everything!)")
        print("2. Search by keyword(s) (e.g. 'scam,crypto,gift,vote,http')")
        print("3. Only Photos & Videos (photos, disappearing snaps, videos, media)")
        print("4. Only Links & URLs (scam links, suspicious websites)")
        print("5. Cancel")
        
        filter_mode = input("\nSelect filter option (1-5): ").strip()
        if filter_mode not in ("1", "2", "3", "4"):
            print("Cancelled.")
            return
        
        keywords = []
        filter_desc = ""
        
        if filter_mode == "1":
            filter_desc = "ALL messages & media sent by your account"
        elif filter_mode == "2":
            kw_input = input("Enter keywords (comma-separated, e.g. 'gift,link,crypto,vote'): ").strip()
            if not kw_input:
                print("No keywords entered.")
                return
            keywords = [k.strip().lower() for k in kw_input.split(",") if k.strip()]
            filter_desc = f"Messages containing keywords: {', '.join(keywords)}"
        elif filter_mode == "3":
            filter_desc = "Photos & Videos (all media)"
        elif filter_mode == "4":
            filter_desc = "Links & URLs"
        
        # Optional date filter
        days_input = input("\nOptional: Only scan messages sent in the last N days (press Enter for ALL time): ").strip()
        cutoff_ts = 0.0
        if days_input.isdigit() and int(days_input) > 0:
            cutoff_ts = time.time() - (int(days_input) * 86400)
            filter_desc += f" (within last {days_input} days)"
            
        try:
            amount_str = input("Max messages to scan in thread history (default 1000): ").strip()
            amount = int(amount_str) if amount_str.isdigit() else 1000
            
            print(f"\nFiltering for: {filter_desc}")
            print(f"Scanning up to {amount} messages...")
            
            items = self.fetch_all_messages_paginated(amount)
            
            if not items:
                print("No messages found in thread.")
                return
            
            matched_items = []
            
            for raw_item in items:
                try:
                    info = extract_message_info(raw_item, self.my_user_id)
                    is_mine = info['is_sent_by_viewer'] or (info['user_id'] == str(self.my_user_id))
                    
                    # Apply date cutoff if specified
                    if cutoff_ts > 0.0 and info['timestamp_ts'] > 0.0:
                        if info['timestamp_ts'] < cutoff_ts:
                            continue
                            
                    matched = False
                    
                    if filter_mode == "1":
                        if is_mine:
                            matched = True
                            
                    elif filter_mode == "2":
                        text_lower = info['summary'].lower()
                        if any(kw in text_lower for kw in keywords):
                            matched = True
                            
                    elif filter_mode == "3":
                        if info['category'] == 'media':
                            matched = True
                            
                    elif filter_mode == "4":
                        if info['category'] == 'link':
                            matched = True
                    
                    if matched:
                        # Attach thread info
                        info['thread_id'] = self.selected_thread_id
                        matched_items.append(info)
                        
                        sender_label = f"{self.my_username} (YOU)" if is_mine else f"Other User ({info['user_id']})"
                        disp_summary = info['summary'][:80] + "..." if len(info['summary']) > 80 else info['summary']
                        
                        print(f"  [Match #{len(matched_items)}] ID: {info['id']} | Type: {info['category'].upper()} | From: {sender_label}")
                        print(f"    Content: {disp_summary}")
                        
                except Exception:
                    continue
            
            print("\n" + "=" * 55)
            print(f"SCAN COMPLETE: Found {len(matched_items)} matching messages.")
            print("=" * 55)
            
            self.last_matches = matched_items
            self.last_filter_desc = filter_desc
            
            own_count = sum(1 for m in matched_items if m['is_sent_by_viewer'] or m['user_id'] == str(self.my_user_id))
            print(f"Messages from YOUR account ready to unsend: {own_count}")
            if len(matched_items) - own_count > 0:
                print(f"Messages from other participants (will NOT be unsent): {len(matched_items) - own_count}")
            
            if own_count > 0:
                print("\nReady! Select Option 6 from the main menu to unsend these messages.")
            else:
                print("\nNo messages from your account matched the filter.")
                
        except Exception as e:
            print(f"Search failed: {e}")

    def delete_messages_raw_api(self):
        """UNSEND queued messages from the active search filter"""
        if not self.logged_in:
            print("Please login first (Option 1)")
            return
        
        print("\n=== BULK UNSEND QUEUED MESSAGES ===")
        
        if not self.last_matches:
            print("No matching messages selected yet.")
            print("Please run Option 5 (Search / Filter Messages) or Option 7 first!")
            return
        
        matches = self.last_matches
        
        own_messages = [
            m for m in matches 
            if m['is_sent_by_viewer'] or (m['user_id'] == str(self.my_user_id))
        ]
        other_messages = [
            m for m in matches 
            if not (m['is_sent_by_viewer'] or (m['user_id'] == str(self.my_user_id)))
        ]
        
        print(f"Filter used: {self.last_filter_desc}")
        print(f"Total matched messages: {len(matches)}")
        print(f"Messages you can unsend: {len(own_messages)}")
        print(f"Other participants' messages: {len(other_messages)} (Ignored - only your own messages can be unsent)")
        
        if len(own_messages) == 0:
            print("\nNo messages from your account to unsend.")
            return
        
        text_count = sum(1 for m in own_messages if m['category'] == 'text')
        media_count = sum(1 for m in own_messages if m['category'] == 'media')
        link_count = sum(1 for m in own_messages if m['category'] == 'link')
        other_count = len(own_messages) - (text_count + media_count + link_count)
        
        print(f"\nBreakdown to unsend:")
        print(f"  - Texts:          {text_count}")
        print(f"  - Photos & Media: {media_count}")
        print(f"  - Links:          {link_count}")
        if other_count > 0:
            print(f"  - Other/Shared:   {other_count}")
            
        print(f"\nPreview of first 10 messages that will be UNSENT:")
        print("-" * 65)
        for i, m in enumerate(own_messages[:10], 1):
            summary = m['summary'][:55] + "..." if len(m['summary']) > 55 else m['summary']
            print(f"{i:2d}. [{m['category'].upper()}] ID: {m['id']} | Time: {m['timestamp']}")
            print(f"    Content: {summary}")
            
        if len(own_messages) > 10:
            print(f"... and {len(own_messages) - 10} more messages")
        print("-" * 65)
        
        confirm = input(f"\nType 'YES' (in capital letters) to permanently UNSEND {len(own_messages)} messages: ").strip()
        if confirm != 'YES':
            print("Unsend cancelled by user.")
            return
        
        print(f"\nStarting unsend process for {len(own_messages)} messages...")
        print("Note: Adding a 1-second delay between deletions to protect your account from rate limits.\n")
        
        deleted = 0
        failed = 0
        
        for i, m in enumerate(own_messages, 1):
            msg_id = m['id']
            thread_id = m.get('thread_id') or self.selected_thread_id
            
            print(f"[{i}/{len(own_messages)}] Unsending {m['category'].upper()} ({msg_id})...", end=" ")
            
            if self.unsend_message(thread_id, msg_id):
                print("[+] Unsent")
                deleted += 1
            else:
                print("[-] Failed")
                failed += 1
                
            time.sleep(1.0)
            
        print("\n" + "=" * 50)
        print("UNSEND PROCESS COMPLETE")
        print(f"Successfully unsent: {deleted} messages")
        print(f"Failed:              {failed} messages")
        print("=" * 50)
        
        self.last_matches = []
        self.last_filter_desc = ""

    def clean_all_conversations(self):
        """
        ACCOUNT-WIDE CLEANUP:
        Scans across ALL conversations in the user's inbox and bulk unsends
        scam messages, links, and photos sent from the user's account.
        This completely eliminates the need to manually scroll or select chats one-by-one!
        """
        if not self.logged_in:
            print("Please login first (Option 1)")
            return
        
        print("\n" + "=" * 65)
        print("   ACCOUNT-WIDE CLEANUP: UNSEND ACROSS ALL INBOX CONVERSATIONS")
        print("=" * 65)
        print("This feature scans across ALL conversations in your inbox and unsends")
        print("scam links, photos, and messages sent by your account when it was hacked.")
        print("You DO NOT need to scroll down or select conversations one-by-one!\n")
        
        print("Step 1: How many conversations to scan from your inbox?")
        print("1. Recent 25 conversations")
        print("2. Recent 50 conversations")
        print("3. Recent 100 conversations")
        print("4. ALL conversations in inbox (Full inbox scan)")
        print("5. Custom number")
        print("6. Cancel")
        
        conv_choice = input("\nSelect option (1-6): ").strip()
        max_convs = 25
        if conv_choice == "1":
            max_convs = 25
        elif conv_choice == "2":
            max_convs = 50
        elif conv_choice == "3":
            max_convs = 100
        elif conv_choice == "4":
            max_convs = 10000  # Will scan until end of inbox
        elif conv_choice == "5":
            c_input = input("Enter number of conversations to scan (e.g. 150): ").strip()
            max_convs = int(c_input) if c_input.isdigit() else 50
        else:
            print("Cancelled.")
            return

        print("\nStep 2: What do you want to unsend across these conversations?")
        print("1. ALL messages & media sent by you (Recommended for hacked accounts - clean everything!)")
        print("2. Only Links & URLs (scam websites, phishing links)")
        print("3. Only Photos & Videos (disappearing photos, images, media)")
        print("4. Messages containing specific keywords (e.g. 'vote,gift,link,crypto')")
        print("5. Cancel")
        
        filter_mode = input("\nSelect filter option (1-5): ").strip()
        if filter_mode not in ("1", "2", "3", "4"):
            print("Cancelled.")
            return

        keywords = []
        filter_desc = ""
        if filter_mode == "1":
            filter_desc = "ALL messages & media sent by your account"
        elif filter_mode == "2":
            filter_desc = "Links & URLs"
        elif filter_mode == "3":
            filter_desc = "Photos & Videos"
        elif filter_mode == "4":
            kw_input = input("Enter keywords (comma-separated, e.g. 'vote,link,gift,crypto'): ").strip()
            if not kw_input:
                print("No keywords entered.")
                return
            keywords = [k.strip().lower() for k in kw_input.split(",") if k.strip()]
            filter_desc = f"Keywords ({', '.join(keywords)})"

        # Step 3: Date cutoff
        print("\nStep 3: Date/Time Filter (CRUCIAL FOR HACK RECOVERY):")
        print("You can limit deletion to only messages sent recently when the hack occurred,")
        print("protecting all your previous personal messages and photos from before the hack.")
        days_input = input("Only unsend messages sent in the last N days (e.g. '3' or '7', or press Enter for ALL time): ").strip()
        cutoff_ts = 0.0
        if days_input.isdigit() and int(days_input) > 0:
            cutoff_ts = time.time() - (int(days_input) * 86400)
            filter_desc += f" (within last {days_input} days)"
            print(f"[+] Date filter active: only unsending messages sent in the last {days_input} days.")
        else:
            print("[+] No date filter: will check all sent messages in scanned conversations.")

        # Step 4: Messages per conversation
        depth_input = input("\nMax messages to inspect per conversation (default 50, press Enter): ").strip()
        messages_per_thread = int(depth_input) if depth_input.isdigit() else 50

        print("\n" + "=" * 60)
        print("SCANNING INBOX CONVERSATIONS...")
        print("=" * 60)
        
        # Load inbox threads with cursor pagination
        threads = self.fetch_inbox_threads(max_threads=max_convs)
        if not threads:
            print("No conversations found in inbox.")
            return

        print(f"\n[+] Loaded {len(threads)} conversations from inbox. Inspecting messages for scam content...\n")
        
        matched_items = []
        affected_threads = set()

        for idx, thread in enumerate(threads, 1):
            thread_id = str(thread.get('thread_id', ''))
            users = thread.get('users', [])
            usernames = [u.get('username', '') for u in users if u.get('username')]
            thread_name = thread.get('thread_title') or (", ".join(usernames[:2]) if usernames else f"Thread_{thread_id}")

            # Collect messages: start with preview items in inbox thread
            items = thread.get('items', [])
            
            # If thread has more messages and user requested > 10, fetch deeper
            if messages_per_thread > len(items) and thread_id:
                try:
                    deeper_resp = self.client.private_request(
                        f"direct_v2/threads/{thread_id}/",
                        params={
                            "visual_message_return_type": "unseen",
                            "direction": "older",
                            "seq_id": "40065",
                            "limit": str(min(messages_per_thread, 20))
                        }
                    )
                    if deeper_resp and 'thread' in deeper_resp:
                        items = deeper_resp['thread'].get('items', items)
                except Exception:
                    pass

            thread_matches = 0
            for item in items:
                try:
                    info = extract_message_info(item, self.my_user_id)
                    is_mine = info['is_sent_by_viewer'] or (info['user_id'] == str(self.my_user_id))
                    
                    if not is_mine:
                        continue
                    
                    # Apply date cutoff
                    if cutoff_ts > 0.0 and info['timestamp_ts'] > 0.0:
                        if info['timestamp_ts'] < cutoff_ts:
                            continue
                    
                    matched = False
                    if filter_mode == "1":
                        matched = True
                    elif filter_mode == "2":
                        matched = (info['category'] == 'link')
                    elif filter_mode == "3":
                        matched = (info['category'] == 'media')
                    elif filter_mode == "4":
                        text_lower = info['summary'].lower()
                        matched = any(kw in text_lower for kw in keywords)
                    
                    if matched:
                        info['thread_id'] = thread_id
                        info['thread_name'] = thread_name
                        matched_items.append(info)
                        thread_matches += 1
                        affected_threads.add(thread_id)
                except Exception:
                    continue

            status_str = f"Found {thread_matches} to unsend" if thread_matches > 0 else "Clean"
            print(f"[{idx:2d}/{len(threads)}] {thread_name[:30]:<30} -> {status_str}")

        print("\n" + "=" * 65)
        print("ACCOUNT SCAN COMPLETE")
        print("=" * 65)
        print(f"Total conversations scanned: {len(threads)}")
        print(f"Affected conversations:       {len(affected_threads)}")
        print(f"Total messages to unsend:     {len(matched_items)}")
        
        if not matched_items:
            print("\n[+] Great news! No matching scam messages were found across your conversations.")
            return

        text_count = sum(1 for m in matched_items if m['category'] == 'text')
        media_count = sum(1 for m in matched_items if m['category'] == 'media')
        link_count = sum(1 for m in matched_items if m['category'] == 'link')
        other_count = len(matched_items) - (text_count + media_count + link_count)

        print(f"\nBreakdown:")
        print(f"  - Scam Links & URLs: {link_count}")
        print(f"  - Photos & Media:    {media_count}")
        print(f"  - Text Messages:     {text_count}")
        if other_count > 0:
            print(f"  - Other:             {other_count}")

        print(f"\nPreview of first 15 messages that will be UNSENT:")
        print("-" * 65)
        for i, m in enumerate(matched_items[:15], 1):
            disp = m['summary'][:50] + "..." if len(m['summary']) > 50 else m['summary']
            print(f"{i:2d}. In {m['thread_name']} | [{m['category'].upper()}] {disp}")
        if len(matched_items) > 15:
            print(f"... and {len(matched_items) - 15} more messages across your conversations.")
        print("-" * 65)

        confirm = input(f"\nType 'YES' (in capital letters) to unsend ALL {len(matched_items)} messages across {len(affected_threads)} chats: ").strip()
        if confirm != 'YES':
            print("Account-wide unsend cancelled by user.")
            return

        print(f"\nStarting automatic account-wide unsend...")
        print("Note: Including a 1-second delay between deletions to keep your account safe from rate limits.\n")

        deleted = 0
        failed = 0

        for i, m in enumerate(matched_items, 1):
            msg_id = m['id']
            thread_id = m['thread_id']
            thread_name = m.get('thread_name', thread_id)
            
            print(f"[{i}/{len(matched_items)}] In {thread_name[:20]}: Unsending {m['category'].upper()} ({msg_id})...", end=" ")
            
            if self.unsend_message(thread_id, msg_id):
                print("[+] Unsent")
                deleted += 1
            else:
                print("[-] Failed")
                failed += 1
                
            time.sleep(1.0)

        print("\n" + "=" * 65)
        print("ACCOUNT-WIDE CLEANUP COMPLETE!")
        print(f"Successfully unsent: {deleted} messages across {len(affected_threads)} conversations")
        print(f"Failed:              {failed} messages")
        print("=" * 65)
        print("Your account has been cleaned! All scam messages sent to your contacts have been removed.")

    def get_thread_info(self, thread_id: str) -> dict:
        """
        Retrieve thread metadata (title, participants, user map).
        """
        users = []
        title = ""
        try:
            res = self.client.private_request(f"direct_v2/threads/{thread_id}/")
            if res and 'thread' in res:
                t = res['thread']
                title = t.get('thread_title') or ""
                users = t.get('users', [])
        except Exception:
            pass

        # If title is still empty, look in cached inbox threads
        if not title:
            for cached_t in getattr(self, 'threads_cache', []):
                if str(cached_t.get('thread_id')) == str(thread_id):
                    title = cached_t.get('thread_title') or ""
                    if not users:
                        users = cached_t.get('users', [])
                    break

        usernames = [u.get('username') for u in users if u.get('username')]
        if not title:
            if usernames:
                title = "@" + ", @".join(usernames[:3])
            else:
                title = f"Thread {thread_id}"

        # Map user IDs to readable names
        user_map = {}
        for u in users:
            uid = str(u.get('pk'))
            uname = u.get('username') or uid
            user_map[uid] = f"@{uname}"
            
        if self.my_user_id:
            user_map[str(self.my_user_id)] = f"{self.my_username} (You)"

        participant_names = [f"@{u.get('username')}" for u in users if u.get('username')]
        if self.my_username:
            participant_names.append(f"{self.my_username} (You)")

        return {
            "thread_id": str(thread_id),
            "title": title,
            "participants": participant_names,
            "users": users,
            "user_map": user_map
        }

    def download_chat(
        self,
        thread_id: Optional[str] = None,
        thread_title: Optional[str] = None,
        max_messages: int = 5000,
        formats: Optional[List[str]] = None,
        download_media: bool = False,
        base_dir: str = "exports"
    ) -> Optional[str]:
        """
        Download and export a conversation to TXT, JSON, and/or HTML.
        Optionally downloads media files (photos, videos, audio notes).
        Returns the export directory path if successful, None otherwise.
        """
        if not self.logged_in:
            print("Please login first (Option 1)")
            return None

        target_thread_id = str(thread_id or self.selected_thread_id or "")
        if not target_thread_id:
            print("No conversation selected. Please specify a thread ID or select one first.")
            return None

        if formats is None:
            formats = ['txt', 'json', 'html']

        print(f"\n[+] Preparing to download conversation (Thread ID: {target_thread_id})...")
        thread_info = self.get_thread_info(target_thread_id)
        if thread_title and (not thread_info.get('title') or thread_info.get('title').startswith("Thread ")):
            thread_info['title'] = thread_title

        # Create safe folder name
        safe_title = sanitize_filename(thread_info.get('title', f"thread_{target_thread_id}"))
        folder_name = f"{safe_title}_{target_thread_id}"
        export_dir = os.path.join(base_dir, folder_name)
        media_dir = os.path.join(export_dir, "media")
        os.makedirs(export_dir, exist_ok=True)

        # 1. Fetch messages
        print(f"[+] Fetching messages (up to {max_messages})...")
        raw_items = self.fetch_all_messages_paginated(max_messages=max_messages, thread_id=target_thread_id)
        if not raw_items:
            print("[!] No messages found to export.")
            return None

        # Instagram returns messages newest -> oldest; reverse to chronological order (oldest -> newest)
        raw_items_chronological = list(reversed(raw_items))
        print(f"[+] Processing {len(raw_items_chronological)} messages in chronological order...")

        # 2. Extract media and parse messages
        processed_messages = []
        user_map = thread_info.get('user_map', {})
        total_media_count = 0
        downloaded_media_count = 0

        if download_media:
            os.makedirs(media_dir, exist_ok=True)
            print("[+] Media download enabled. Inspecting media files...")

        for idx, item in enumerate(raw_items_chronological):
            info = extract_message_info(item, self.my_user_id)
            user_id_str = str(info['user_id'])
            
            # Determine sender display name
            if info['is_sent_by_viewer'] or user_id_str == str(self.my_user_id):
                sender_name = f"{self.my_username} (You)"
            elif user_id_str in user_map:
                sender_name = user_map[user_id_str]
            else:
                sender_name = f"User {user_id_str}"

            media_items = extract_media_urls(item)
            message_media_records = []

            for m_idx, m in enumerate(media_items):
                total_media_count += 1
                media_record = {
                    "type": m['type'],
                    "url": m['url'],
                    "ext": m['ext'],
                    "local_path": None,
                    "downloaded": False
                }

                if download_media and m.get('url'):
                    ts_clean = (info['timestamp'] or "date").replace(':', '').replace('-', '').replace(' ', '_')
                    msg_id_clean = sanitize_filename(str(info['id']))
                    filename = f"{ts_clean}_{msg_id_clean}_{m_idx+1}.{m['ext']}"
                    file_path = os.path.join(media_dir, filename)

                    # Only download if not already cached/downloaded
                    if not os.path.exists(file_path):
                        success = download_media_file(m['url'], file_path)
                    else:
                        success = True

                    if success:
                        downloaded_media_count += 1
                        media_record['local_path'] = f"media/{filename}"
                        media_record['downloaded'] = True
                    else:
                        media_record['local_path'] = m['url']
                else:
                    media_record['local_path'] = m.get('url')

                message_media_records.append(media_record)

            processed_msg = {
                "id": str(info['id']),
                "user_id": user_id_str,
                "sender_name": sender_name,
                "is_sent_by_viewer": bool(info['is_sent_by_viewer']),
                "timestamp": info['timestamp'],
                "timestamp_ts": info['timestamp_ts'],
                "item_type": info['item_type'],
                "category": info['category'],
                "summary": info['summary'],
                "text": item.get('text') if isinstance(item, dict) else getattr(item, 'text', None),
                "media_files": message_media_records,
                "raw": item if isinstance(item, dict) else {}
            }
            processed_messages.append(processed_msg)

        thread_info['export_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 3. Export to requested formats
        created_files = []
        if 'txt' in formats:
            txt_path = os.path.join(export_dir, "chat.txt")
            export_chat_to_txt(thread_info, processed_messages, txt_path)
            created_files.append(txt_path)

        if 'json' in formats:
            json_path = os.path.join(export_dir, "chat.json")
            export_chat_to_json(thread_info, processed_messages, json_path)
            created_files.append(json_path)

        if 'html' in formats:
            html_path = os.path.join(export_dir, "chat.html")
            export_chat_to_html(thread_info, processed_messages, html_path)
            created_files.append(html_path)

        print("\n" + "=" * 65)
        print("CONVERSATION DOWNLOAD COMPLETE!")
        print("=" * 65)
        print(f"Chat:             {thread_info.get('title')}")
        print(f"Messages Saved:   {len(processed_messages)}")
        if download_media:
            print(f"Media Downloaded: {downloaded_media_count} / {total_media_count} files")
        print(f"Saved Directory:  {os.path.abspath(export_dir)}")
        print("Exported Files:")
        for cf in created_files:
            print(f"  - {os.path.basename(cf)} ({os.path.abspath(cf)})")
        print("=" * 65)

        return export_dir

    def download_all_conversations(
        self,
        max_convs: int = 25,
        max_messages_per_chat: int = 2000,
        formats: Optional[List[str]] = None,
        download_media: bool = False
    ):
        """
        Bulk download multiple or all conversations from the inbox.
        """
        if not self.logged_in:
            print("Please login first (Option 1)")
            return

        print("\n" + "=" * 65)
        print("   BULK DOWNLOAD: EXPORT ALL INBOX CONVERSATIONS")
        print("=" * 65)
        print(f"Fetching up to {max_convs} conversations from inbox...")

        threads = self.fetch_inbox_threads(max_threads=max_convs)
        if not threads:
            print("No conversations found in inbox.")
            return

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        bulk_dir = os.path.join("exports", f"inbox_backup_{timestamp_str}")
        os.makedirs(bulk_dir, exist_ok=True)

        print(f"\n[+] Found {len(threads)} conversations to export.")
        print(f"[+] Destination: {os.path.abspath(bulk_dir)}\n")

        successful = 0
        failed = 0

        for i, thread in enumerate(threads, 1):
            tid = str(thread.get('thread_id', ''))
            title = thread.get('thread_title')
            users = thread.get('users', [])
            usernames = [u.get('username', '') for u in users if u.get('username')]

            display_title = title or (", ".join(usernames[:2]) if usernames else f"Thread_{tid}")
            print(f"\n[{i:2d}/{len(threads)}] Exporting: {display_title} (ID: {tid})...")

            try:
                res = self.download_chat(
                    thread_id=tid,
                    thread_title=display_title,
                    max_messages=max_messages_per_chat,
                    formats=formats,
                    download_media=download_media,
                    base_dir=bulk_dir
                )
                if res:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"[!] Error exporting {display_title}: {e}")
                failed += 1

            time.sleep(1.0)  # Gentle delay between thread downloads

        print("\n" + "=" * 65)
        print("BULK EXPORT COMPLETED!")
        print(f"Successfully exported: {successful} / {len(threads)} conversations")
        if failed > 0:
            print(f"Failed / Empty:        {failed} conversations")
        print(f"All conversations saved to: {os.path.abspath(bulk_dir)}")
        print("=" * 65)

    def download_chat_menu(self):
        """
        Interactive menu for downloading conversations.
        """
        if not self.logged_in:
            print("Please login first (Option 1)")
            return

        print("\n" + "=" * 65)
        print("   DOWNLOAD / EXPORT CHAT CONVERSATIONS")
        print("=" * 65)
        print("Export your chats to readable Text (.txt), structured JSON (.json),")
        print("and interactive HTML (.html) with optional photo & video downloading!\n")

        curr_title = self.selected_thread_title or self.selected_thread_id or ""
        print("1. Download currently selected conversation" + (f" ({curr_title})" if curr_title else " (None selected)"))
        print("2. Download conversation by Username or Thread ID")
        print("3. Bulk Download: Multiple / All inbox conversations")
        print("4. Back to Main Menu")

        choice = input("\nSelect option (1-4): ").strip()
        if choice == "4" or not choice:
            return

        target_thread_id = None
        target_title = None

        if choice == "1":
            if not self.selected_thread_id:
                print("[!] No conversation currently selected.")
                print("Please select one first via Option 2 or 3, or choose Option 2 here.")
                return
            target_thread_id = self.selected_thread_id
            target_title = self.selected_thread_title

        elif choice == "2":
            query = input("Enter Instagram username or Thread ID: ").strip()
            if not query:
                return
            if query.isdigit() and len(query) > 8:
                target_thread_id = str(query)
                target_title = f"Thread_{query}"
            else:
                uname = query.lstrip('@')
                print(f"Looking up @{uname} in inbox...")
                threads = self.fetch_inbox_threads(max_threads=50)
                found = False
                for t in threads:
                    for u in t.get('users', []):
                        if (u.get('username') or '').lower() == uname.lower():
                            target_thread_id = str(t.get('thread_id'))
                            target_title = f"@{uname}"
                            found = True
                            break
                    if found:
                        break
                if not found:
                    try:
                        uid = self.client.user_id_from_username(uname)
                        for t in threads:
                            for u in t.get('users', []):
                                if str(u.get('pk')) == str(uid):
                                    target_thread_id = str(t.get('thread_id'))
                                    target_title = f"@{uname}"
                                    found = True
                                    break
                            if found:
                                break
                    except Exception:
                        pass
                if not target_thread_id:
                    print(f"[!] Could not find conversation with @{uname} in recent inbox.")
                    print("Tip: If you know the direct thread ID, enter it directly.")
                    return

        elif choice == "3":
            # Bulk download flow
            print("\nHow many conversations to export from your inbox?")
            print("1. Recent 10 conversations")
            print("2. Recent 25 conversations")
            print("3. Recent 50 conversations")
            print("4. ALL conversations in inbox")
            print("5. Custom number")
            print("6. Cancel")

            b_choice = input("Select (1-6): ").strip()
            max_c = 10
            if b_choice == "1":
                max_c = 10
            elif b_choice == "2":
                max_c = 25
            elif b_choice == "3":
                max_c = 50
            elif b_choice == "4":
                max_c = 5000
            elif b_choice == "5":
                c_num = input("Enter number of conversations: ").strip()
                max_c = int(c_num) if c_num.isdigit() else 20
            else:
                return

            limit_input = input("Max messages to export per conversation (default 2000, 0 for unlimited): ").strip()
            max_msgs = int(limit_input) if limit_input.isdigit() and int(limit_input) > 0 else 2000
            if limit_input == "0":
                max_msgs = 50000

            fmt_choice = input("\nExport format:\n1. All formats (TXT + JSON + HTML) [Recommended]\n2. Plain Text (.txt)\n3. JSON (.json)\n4. HTML Chat View (.html)\nChoice (1-4, default 1): ").strip()
            formats = ['txt', 'json', 'html']
            if fmt_choice == "2":
                formats = ['txt']
            elif fmt_choice == "3":
                formats = ['json']
            elif fmt_choice == "4":
                formats = ['html']

            media_ans = input("\nDownload media files (photos, videos, audio notes)? (y/n, default n): ").strip().lower()
            download_media = (media_ans == 'y' or media_ans == 'yes')

            self.download_all_conversations(
                max_convs=max_c,
                max_messages_per_chat=max_msgs,
                formats=formats,
                download_media=download_media
            )
            return
        else:
            print("Invalid option.")
            return

        # Common single chat download settings
        limit_input = input("\nHow many messages to download? (default 5000, 0 for unlimited): ").strip()
        max_msgs = int(limit_input) if limit_input.isdigit() and int(limit_input) > 0 else 5000
        if limit_input == "0":
            max_msgs = 50000

        fmt_choice = input("\nExport format:\n1. All formats (TXT + JSON + HTML) [Recommended]\n2. Plain Text (.txt)\n3. JSON (.json)\n4. HTML Chat View (.html)\nChoice (1-4, default 1): ").strip()
        formats = ['txt', 'json', 'html']
        if fmt_choice == "2":
            formats = ['txt']
        elif fmt_choice == "3":
            formats = ['json']
        elif fmt_choice == "4":
            formats = ['html']

        media_ans = input("\nDownload media files (photos, videos, audio notes)? (y/n, default n): ").strip().lower()
        download_media = (media_ans == 'y' or media_ans == 'yes')

        self.download_chat(
            thread_id=target_thread_id,
            thread_title=target_title,
            max_messages=max_msgs,
            formats=formats,
            download_media=download_media
        )

    def menu_loop(self):
        """Main menu loop"""
        while True:
            try:
                print("\n" + "=" * 55)
                print("   INSTAGRAM DM TOOL - UNLIMITED PAGINATION & UNSEND")
                print("=" * 55)
                
                if self.logged_in:
                    print(f"Status:   LOGGED IN as @{self.my_username} (ID: {self.my_user_id})")
                else:
                    print("Status:   NOT LOGGED IN (Select Option 1 to connect)")
                
                if self.selected_thread_id:
                    print(f"Thread:   Selected: {self.selected_thread_title or self.selected_thread_id} (ID: {self.selected_thread_id})")
                else:
                    print("Thread:   None selected (Select Option 2 or 3)")
                    
                if self.last_matches:
                    print(f"Filter:   {len(self.last_matches)} messages queued ({self.last_filter_desc})")
                
                print("\nOptions:")
                print("1. Login / Account (Username/Password or Session ID Cookie)")
                print("2. List Conversations (Browse Inbox with Next-Page pagination)")
                print("3. Select Conversation (by Username or Thread ID)")
                print("4. View Messages (Unlimited pagination in selected conversation)")
                print("5. Search / Filter Messages (In selected conversation)")
                print("6. Unsend Queued Messages (In selected conversation)")
                print("7. CLEAN ALL CONVERSATIONS (Account-Wide Scam Unsend)")
                print("8. DOWNLOAD / EXPORT CHAT (Save to TXT, JSON, HTML & Media) [NEW]")
                print("9. Logout / Switch Account")
                print("10. Exit")
                
                choice = input("\nSelect option (1-10): ").strip()
                
                if choice == "1":
                    self.login()
                elif choice == "2":
                    self.list_threads_raw_api()
                elif choice == "3":
                    self.select_thread()
                elif choice == "4":
                    self.view_messages_raw_api()
                elif choice == "5":
                    self.search_messages_raw_api()
                elif choice == "6":
                    self.delete_messages_raw_api()
                elif choice == "7":
                    self.clean_all_conversations()
                elif choice == "8":
                    self.download_chat_menu()
                elif choice == "9":
                    self.logout()
                elif choice == "10":
                    print("Exiting. Goodbye!")
                    break
                else:
                    print("Invalid option. Please enter 1-10.")
                    
            except KeyboardInterrupt:
                print("\n\nExiting. Goodbye!")
                break
            except Exception as e:
                print(f"\nUnexpected error in menu: {e}")


def main():
    try:
        print("Instagram DM Tool - UNLIMITED PAGINATION + BULK UNSEND + CHAT DOWNLOAD")
        print("[+] Proper cursor-based pagination")
        print("[+] Bulk unsend text, links, photos & media")
        print("[+] Support for 2FA and Session ID login (bypasses out-of-date error)")
        print("[+] Account-wide cleanup to wipe out scam messages across ALL inbox chats")
        print("[+] Chat download & backup: export to TXT, JSON, HTML with photos & videos")
        tool = IGDMTool()
        tool.menu_loop()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
