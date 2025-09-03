import json
import os
import sys
from datetime import datetime, timedelta
from contextlib import suppress
from typing import Union, Optional

from utils import ClassMeet

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    create_client = None
    Client = None
    SUPABASE_AVAILABLE = False

SupabaseClient: Optional[Client] = None # type: ignore

DATA_DIR = os.path.join(os.path.dirname(__file__), "db_data")
MEMBERS_FILE = os.path.join(DATA_DIR, "members.json")
CLASSES_FILE = os.path.join(DATA_DIR, "classes.json")
PROBLEMS_FILE = os.path.join(DATA_DIR, "problems.json")
POINTS_FILE = os.path.join(DATA_DIR, "points.json")


def _ensure_data_dir():
    """Ensures that the directory for local JSON database files exists."""
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(path: str) -> Union[list, dict]:
    """Loads data from a JSON file."""
    _ensure_data_dir()
    if not os.path.exists(path):
        return [] if path in (MEMBERS_FILE, CLASSES_FILE, PROBLEMS_FILE) else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading JSON from {path}: {e}", file=sys.stderr)
        return [] if path in (MEMBERS_FILE, CLASSES_FILE, PROBLEMS_FILE) else {}


def _save_json(path: str, data: Union[list, dict]):
    """Saves data to a JSON file."""
    _ensure_data_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def connect_database():
    """
    Attempts to connect to the Supabase database using credentials from files.
    If connection fails, the bot will use local JSON files as a fallback.
    """
    global SupabaseClient
    if not SUPABASE_AVAILABLE:
        print("Supabase client not installed. Using local JSON files for database.", file=sys.stderr)
        return

    try:
        with open('databaseurl.txt', 'r') as f:
            url = f.readline().strip()
        with open('databasekey.txt', 'r') as f:
            key = f.readline().strip()
        
        if url and key:
            SupabaseClient = create_client(url, key)
            print("Successfully connected to Supabase.")
        else:
            print("Supabase URL or key is missing. Using local JSON files.", file=sys.stderr)
    except FileNotFoundError:
        print("databaseurl.txt or databasekey.txt not found. Using local JSON files.", file=sys.stderr)
        SupabaseClient = None
    except Exception as e:
        print(f"Failed to connect to Supabase: {e}", file=sys.stderr)
        SupabaseClient = None


def sync_members(members):
    """
    Synchronizes the list of guild members with the local storage and Supabase.
    """
    stored_members = _load_json(MEMBERS_FILE)
    stored_ids = {str(m.get("id")) for m in stored_members}
    current_ids = {str(m.id) for m in members}

    # Add new members
    for member in members:
        if str(member.id) not in stored_ids:
            add_member(member)

    # Remove old members
    for member_id in stored_ids - current_ids:
        remove_member({"id": int(member_id)})

    if SupabaseClient:
        try:
            # This is a simple but potentially slow way to sync.
            # For larger servers, a more sophisticated approach would be needed.
            SupabaseClient.table('members').delete().neq('id', -1).execute()
            all_members_data = _load_json(MEMBERS_FILE)
            if all_members_data:
                SupabaseClient.table('members').insert(all_members_data).execute()
        except Exception as e:
            print(f"Supabase error during member sync: {e}", file=sys.stderr)


def add_class(class_meet: ClassMeet):
    """
    Adds a new class to the local storage and Supabase.
    """
    classes = _load_json(CLASSES_FILE)
    entry = {
        'type': class_meet.type,
        'type_str': class_meet.type_str,
        'date': class_meet.date,
        'time': class_meet.time,
        'host': class_meet.host,
        'description': class_meet.description,
        'created_at': datetime.utcnow().isoformat()
    }
    classes.append(entry)
    _save_json(CLASSES_FILE, classes)

    if SupabaseClient:
        try:
            SupabaseClient.table('classes').insert(entry).execute()
        except Exception as e:
            print(f"Supabase error in add_class: {e}", file=sys.stderr)


def get_class(days_limit: int = 14) -> list[ClassMeet]:
    """
    Returns a list of classes scheduled within a given number of days from now.
    """
    items = _load_json(CLASSES_FILE)
    now = datetime.utcnow().date()
    cutoff = now + timedelta(days=days_limit)
    results = []

    for item in items:
        date_str = item.get('date')
        if not date_str:
            continue
        
        try:
            class_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid date format '{date_str}' in classes.json, skipping.", file=sys.stderr)
            continue

        if now <= class_date <= cutoff:
            meet = ClassMeet()
            meet.load_from_discord(
                item.get('type', 0),
                item.get('date', ''),
                item.get('time', ''),
                item.get('host', ''),
                item.get('description', '')
            )
            results.append(meet)
            
    return results


def create_problem(content: str, solve: str, tags: str = "") -> int:
    """
    Adds a new problem to the local storage and Supabase. Returns the new problem's ID.
    """
    problems = _load_json(PROBLEMS_FILE)
    new_id = max([p.get('id', 0) for p in problems] + [0]) + 1
    
    entry = {
        'id': new_id,
        'content': content,
        'solve': solve,
        'tags': [tag.strip() for tag in tags.split() if tag.strip()],
        'created_at': datetime.utcnow().isoformat()
    }
    problems.append(entry)
    _save_json(PROBLEMS_FILE, problems)

    if SupabaseClient:
        try:
            SupabaseClient.table('problems').insert(entry).execute()
        except Exception as e:
            print(f"Supabase error in create_problem: {e}", file=sys.stderr)

    return new_id


def add_point(member, points: int):
    """
    Adds or subtracts points for a member.
    """
    member_id = None
    with suppress(AttributeError):
        member_id = str(member.id)
    if not member_id and isinstance(member, dict):
        member_id = str(member.get('id'))
    
    if not member_id:
        return

    points_store = _load_json(POINTS_FILE)
    if not isinstance(points_store, dict):
        points_store = {}

    current_points = points_store.get(member_id, 0)
    points_store[member_id] = current_points + points
    _save_json(POINTS_FILE, points_store)

    if SupabaseClient:
        try:
            SupabaseClient.table('points').upsert({'id': int(member_id), 'points': points_store[member_id]}).execute()
        except Exception as e:
            print(f"Supabase error in add_point: {e}", file=sys.stderr)


def add_member(member):
    """
    Adds a new member to the local storage and Supabase.
    """
    try:
        member_id = str(member.id)
        name = getattr(member, 'name', '')
        display_name = getattr(member, 'display_name', name)
    except AttributeError:
        if isinstance(member, dict):
            member_id = str(member.get('id'))
            name = member.get('name', '')
            display_name = member.get('display_name', name)
        else:
            return
    
    if not member_id:
        return

    members = _load_json(MEMBERS_FILE)
    if any(str(m.get('id')) == member_id for m in members):
        return  # Member already exists

    entry = {'id': int(member_id), 'name': name, 'display_name': display_name}
    members.append(entry)
    _save_json(MEMBERS_FILE, members)

    if SupabaseClient:
        try:
            SupabaseClient.table('members').insert(entry).execute()
        except Exception as e:
            print(f"Supabase error in add_member: {e}", file=sys.stderr)


def remove_member(member):
    """
    Removes a member from local storage and Supabase.
    """
    member_id = None
    with suppress(AttributeError):
        member_id = str(member.id)
    if not member_id and isinstance(member, dict):
        member_id = str(member.get('id'))

    if not member_id:
        return

    # Remove from members.json
    members = _load_json(MEMBERS_FILE)
    members_filtered = [m for m in members if str(m.get('id')) != member_id]
    if len(members_filtered) < len(members):
        _save_json(MEMBERS_FILE, members_filtered)

    # Remove from points.json
    points_store = _load_json(POINTS_FILE)
    if isinstance(points_store, dict) and member_id in points_store:
        del points_store[member_id]
        _save_json(POINTS_FILE, points_store)

    if SupabaseClient:
        try:
            SupabaseClient.table('members').delete().eq('id', int(member_id)).execute()
            SupabaseClient.table('points').delete().eq('id', int(member_id)).execute()
        except Exception as e:
            print(f"Supabase error in remove_member: {e}", file=sys.stderr)
