import os
import json
import glob
import re

def main():
    # 1. Load Winners from the file committed by the tally script
    winners_file = "latest_winners.json"
    if not os.path.exists(winners_file):
        print("⚠️ No latest_winners.json found. Nothing to create.")
        return
        
    with open(winners_file, "r", encoding="utf-8") as f:
        winners = json.load(f)

    # 2. Identify the Week from the latest Planning CSV
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files:
        print("❌ No planning CSV found to determine week.")
        return
        
    latest_file = max(files, key=os.path.getmtime)
    # Check for WK_# or W# format
    match = re.search(r'([W]K?_?\d+)', os.path.basename(latest_file), re.IGNORECASE)
    week_folder = match.group(1).upper() if match else "WEEK_UNKNOWN"
    
    # Standardize to WK_XX format if it's just W17
    if re.match(r'^W\d+$', week_folder):
        week_folder = week_folder.replace("W", "WK_")
    
    base_dir = f"src/02_Content/{week_folder}"
    os.makedirs(base_dir, exist_ok=True)

    # 3. Create .vid files for winners
    # Using a set to avoid duplicates if the tally ran twice
    processed_titles = set()
    
    for winner in winners:
        title = winner['title']
        if title in processed_titles:
            continue
            
        type_code = winner['type'] # 'V' or 'S'
        rank = winner['rank']
        clean_title = re.sub(r'[^\w\s-]', '', title).strip().replace(" ", "_")
        
        filename = f"{type_code}{rank}_{clean_title}.vid"
        file_path = os.path.join(base_dir, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"--- CONTENT INFO ---\n")
            f.write(f"Title: {title}\n")
            f.write(f"Type: {'Long Video' if type_code == 'V' else 'Shorts'}\n")
            f.write(f"Rank: {rank}\n")
            
        print(f"✅ Created: {filename}")
        processed_titles.add(title)

    # 4. Clean up the JSON file after successful creation so it's fresh for next week
    os.remove(winners_file)

if __name__ == "__main__":
    main()
