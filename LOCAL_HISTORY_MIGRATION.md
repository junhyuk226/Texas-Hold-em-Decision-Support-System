# Local Hand-History Migration Note

The public release stores new hand history inside this project:

```text
data/hand_history/hands.json
```

Earlier personal builds may have stored history in a neighboring `poker_assistant_v8` folder. The public release intentionally does not read from or write to that sibling project.

If you want to carry those records forward on your own Mac:

1. Stop the running app.
2. Open Terminal in the `poker_assistant_v10` project directory.
3. Back up the old JSON file somewhere outside the Git repository.
4. Copy it into the new project-local data directory:

```bash
mkdir -p data/hand_history
cp -n ../poker_assistant_v8/data/hand_history/hands.json data/hand_history/hands.json
```

`cp -n` avoids overwriting an existing destination file. If the destination already exists, compare and merge the two JSON arrays deliberately rather than replacing either file blindly.

The entire `data/` directory is excluded by `.gitignore`. Do not commit personal hand history to a public repository.
