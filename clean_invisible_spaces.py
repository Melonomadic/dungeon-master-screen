# clean_invisible_spaces.py

import os
import shutil

def clean_file(path):
    """Removes non-breaking spaces and other invisible whitespace, with backup and summary."""
    if not os.path.exists(path):
        print(f"❌ File not found: {path}")
        return

    backup_path = path + ".bak"

    # --- Step 1: Create backup ---
    shutil.copy2(path, backup_path)
    print(f"📦 Backup created: {backup_path}")

    # --- Step 2: Read file ---
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # --- Step 3: Count invisible characters ---
    nb_spaces = content.count("\u00A0")
    zw_spaces = content.count("\u200B")
    boms = content.count("\uFEFF")
    total_removed = nb_spaces + zw_spaces + boms
    total_lines = content.count("\n") + 1

    # --- Step 4: Clean them out ---
    cleaned = (
        content
        .replace("\u00A0", " ")  # Non-breaking space
        .replace("\u200B", "")   # Zero-width space
        .replace("\uFEFF", "")   # Byte Order Mark
    )

    # --- Step 5: Write cleaned version back ---
    with open(path, "w", encoding="utf-8") as f:
        f.write(cleaned)

    # --- Step 6: Print summary ---
    print("\n✅ Cleanup complete!")
    print(f"📄 File: {path}")
    print(f"📏 Lines scanned: {total_lines}")
    print(f"🧹 Non-breaking spaces removed: {nb_spaces}")
    print(f"🕳️ Zero-width spaces removed:   {zw_spaces}")
    print(f"🧾 BOM characters removed:      {boms}")
    print(f"📊 Total invisible characters removed: {total_removed}")

    if total_removed == 0:
        print("✨ File was already clean.")
    else:
        print("✅ All invisible characters removed successfully!")

if __name__ == "__main__":
    target_file = "bot.py"
    print(f"🚀 Starting cleanup for {target_file}...\n")
    clean_file(target_file)
