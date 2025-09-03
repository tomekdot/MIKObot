MIKObot

Quick setup

1. Create a virtual environment and install dependencies:

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt

2. Put your Discord bot token in `token.txt` (first line).
3. (Optional) Put Supabase URL in `databaseurl.txt` and key in `databasekey.txt` to enable remote DB.
4. Run the bot:

   python main.py

Notes

- The project uses simple JSON files under `db_data/` as a fallback storage.
- `DataBaseCommands` will work without `supabase` installed; install supabase if you need remote DB sync.
