import os
import json
import discord
from discord import app_commands
from dotenv import load_dotenv
from typing import Optional, List, Tuple
import re # For dice rolling
import random # For dice rolling

# --- NEW: FIREBASE IMPORTS ---
import firebase_admin
from firebase_admin import credentials, firestore

# --- LOAD ENVIRONMENT VARIABLES ---
print("DEBUG: Script started. Loading .env...")
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')
OWNER_ID = os.getenv('OWNER_ID')

if GUILD_ID:
    MY_GUILD = discord.Object(id=GUILD_ID)
    print(f"DEBUG: Found GUILD_ID: {GUILD_ID}")
else:
    print("DEBUG: WARNING: GUILD_ID not found in .env. Syncing will be slow.")
    MY_GUILD = None  # This will make it sync globally

if not OWNER_ID:
    print("DEBUG: WARNING: OWNER_ID not found in .env. Manual sync/migrate commands will not work.")

# --- NEW: FIREBASE SETUP ---
try:
    # Use the service account key file to authenticate
    cred = credentials.Certificate('firebase-service-account.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("DEBUG: Successfully connected to Firestore.")
except Exception as e:
    print(f"DEBUG: CRITICAL ERROR: Failed to connect to Firestore: {e}")
    print("DEBUG: Make sure 'firebase-service-account.json' is in the same folder as bot.py")
    db = None

# --- CONSTANTS ---
# This is now just a legacy file for migration
LEGACY_CHAR_DATA_FILE = "characters.json"
SKILLS_LIST = [
    "Acrobatics (Dex)", "Animal Handling (Wis)", "Arcana (Int)", "Athletics (Str)",
    "Deception (Cha)", "History (Int)", "Insight (Wis)", "Intimidation (Cha)",
    "Investigation (Int)", "Medicine (Wis)", "Nature (Int)", "Perception (Wis)",
    "Performance (Cha)", "Persuasion (Cha)", "Religion (Int)", "Sleight of Hand (Dex)",
    "Stealth (Dex)", "Survival (Wis)"
]
SAVES_LIST = [
    "Strength Saving Throw", "Dexterity Saving Throw", "Constitution Saving Throw",
    "Intelligence Saving Throw", "Wisdom Saving Throw", "Charisma Saving Throw"
]
SPELL_LEVELS = [
    app_commands.Choice(name="Cantrip", value="cantrips"),
    app_commands.Choice(name="1st Level", value="1st_level"),
    app_commands.Choice(name="2nd Level", value="2nd_level"),
    app_commands.Choice(name="3rd Level", value="3rd_level"),
    app_commands.Choice(name="4th Level", value="4th_level"),
    app_commands.Choice(name="5th Level", value="5th_level"),
    app_commands.Choice(name="6th Level", value="6th_level"),
    app_commands.Choice(name="7th Level", value="7th_level"),
    app_commands.Choice(name="8th Level", value="8th_level"),
    app_commands.Choice(name="9th Level", value="9th_level"),
]


# --- HELPER FUNCTIONS ---

def calculate_modifier(score: int) -> int:
    """Calculates the D&D modifier for a given ability score."""
    return (score - 10) // 2

def get_ability_for_skill(skill_name: str) -> str:
    """Gets the ability score key (e.g., 'strength') for a skill."""
    skill_map = {
        "Acrobatics (Dex)": "dexterity", "Animal Handling (Wis)": "wisdom", "Arcana (Int)": "intelligence",
        "Athletics (Str)": "strength", "Deception (Cha)": "charisma", "History (Int)": "intelligence",
        "Insight (Wis)": "wisdom", "Intimidation (Cha)": "charisma", "Investigation (Int)": "intelligence",
        "Medicine (Wis)": "wisdom", "Nature (Int)": "intelligence", "Perception (Wis)": "wisdom",
        "Performance (Cha)": "charisma", "Persuasion (Cha)": "charisma", "Religion (Int)": "intelligence",
        "Sleight of Hand (Dex)": "dexterity", "Stealth (Dex)": "dexterity", "Survival (Wis)": "wisdom",
        "Strength Saving Throw": "strength", "Dexterity Saving Throw": "dexterity",
        "Constitution Saving Throw": "constitution", "Intelligence Saving Throw": "intelligence",
        "Wisdom Saving Throw": "wisdom", "Charisma Saving Throw": "charisma"
    }
    return skill_map.get(skill_name, "strength") # Default to strength if not found

# --- NEW: Truncate text to avoid 1024 char limit ---
def truncate_text(text: str, max_length: int = 1020) -> str:
    """Truncates text to fit in an embed field."""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text or "Not set" # Return "Not set" if text is empty

# --- NEW: ASYNC FIRESTORE DATA FUNCTIONS ---
# --- FIX: All firebase calls are now wrapped in loop.run_in_executor ---

async def get_character_data(user_id: str, char_name_key: str) -> Optional[dict]:
    """Fetches a specific character document from Firestore."""
    if db is None: return None
    try:
        doc_ref = db.collection('users').document(user_id).collection('characters').document(char_name_key)
        # Run the blocking .get() in an executor
        doc = await client.loop.run_in_executor(None, doc_ref.get)
        if doc.exists:
            return doc.to_dict()
        else:
            return None
    except Exception as e:
        print(f"Error getting character data: {e}")
        return None

async def save_character_data(user_id: str, char_name_key: str, data: dict):
    """Saves a specific character document to Firestore."""
    if db is None: return
    try:
        doc_ref = db.collection('users').document(user_id).collection('characters').document(char_name_key)
        # Run the blocking .set() in an executor
        await client.loop.run_in_executor(None, lambda: doc_ref.set(data))
    except Exception as e:
        print(f"Error saving character data: {e}")

async def delete_character_data(user_id: str, char_name_key: str):
    """Deletes a specific character document from Firestore."""
    if db is None: return
    try:
        doc_ref = db.collection('users').document(user_id).collection('characters').document(char_name_key)
        # Run the blocking .delete() in an executor
        await client.loop.run_in_executor(None, doc_ref.delete)
    except Exception as e:
        print(f"Error deleting character data: {e}")

async def get_all_user_characters(user_id: str) -> List[dict]:
    """Fetches all characters for a specific user for autocomplete."""
    if db is None: return []
    try:
        chars_ref = db.collection('users').document(user_id).collection('characters')
        # Run the blocking .get() in an executor
        docs = await client.loop.run_in_executor(None, chars_ref.get)
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"Error getting all user characters: {e}")
        return []

# --- NEW: DM HELPER FUNCTION (USING COLLECTION GROUP) ---
async def get_all_characters_in_db() -> List[Tuple[str, dict]]:
    """Fetches all characters from all users. Returns (user_id, char_data)."""
    if db is None: return []
    all_chars = []
    try:
        # --- FIX: Use a Collection Group query ---
        # This query finds *all* collections named 'characters'
        # This requires a Firestore Index! The error log will provide the link.
        chars_ref = db.collection_group('characters')
        char_docs = await client.loop.run_in_executor(None, chars_ref.get)
        
        for char_doc in char_docs:
            char_data = char_doc.to_dict()
            # The parent of a doc in a collection group is the document containing it
            user_id = char_doc.reference.parent.parent.id
            all_chars.append((user_id, char_data))
        
        print(f"DEBUG: get_all_characters_in_db found {len(all_chars)} characters total.")
        return all_chars
    except Exception as e:
        # This will print the error and the URL to create the index
        print(f"Error getting all DB characters (THIS MAY BE AN INDEXING ERROR): {e}") 
        return []
# --- END NEW FIRESTORE FUNCTIONS ---

def get_new_char_data(char_name: str, race: str, char_class: str, player_name: str):
    """Generates the data structure for a new character."""
    return {
        "name": char_name, "race": race, "class_level": f"{char_class} 1",
        "background": "", "player_name": player_name, "alignment": "", "experience_points": 0,
        "strength": 10, "dexterity": 10, "constitution": 10,
        "intelligence": 10, "wisdom": 10, "charisma": 10,
        "proficiency_bonus": 2, "proficiencies": [],
        "armor_class": 10, "max_hp": 10, "current_hp": 10, "temphp": 0, "speed": 30,
        "hitdice_total": 1, "hitdice_current": 1,
        "death_save_success": 0, "death_save_fail": 0,
        "inspiration": 0,
        "personality_trait": "", "ideals": "", "bonds": "", "flaws": "", "other_proficiencies": "",
        "features_traits": [], "attacks": [], "equipment": [], "treasure": "",
        "appearance": "", "allies_orgs": "", "backstory": "",
        "spellcasting_class": "", "spellcasting_ability": "", "spell_save_dc": 8, "spell_attack_bonus": 0,
        "spellbook": {
            "cantrips": [], "1st_level": [], "2nd_level": [], "3rd_level": [],
            "4th_level": [], "5th_level": [], "6th_level": [], "7th_level": [],
            "8th_level": [], "9th_level": []
        }
    }

async def character_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocompletes character names for the user from Firestore."""
    user_id = str(interaction.user.id)
    user_chars = await get_all_user_characters(user_id) # This will now work
    
    return [
        app_commands.Choice(name=char_data["name"], value=char_data["name"].lower())
        for char_data in user_chars
        if current.lower() in char_data["name"].lower()
    ]

# --- NEW: DM AUTOCOMPLETE ---
async def dm_character_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocompletes ALL character names for the DM."""
    print(f"DEBUG: dm_character_autocomplete triggered by User {interaction.user.id}")
    
    # Safety check: only owners should be able to see this
    if str(interaction.user.id) != OWNER_ID:
        print(f"DEBUG: User {interaction.user.id} is NOT owner. Returning empty list.")
        return []
    
    print("DEBUG: User is owner. Fetching all characters...")
    all_chars = await get_all_characters_in_db()
    
    choices = []
    for user_id, char_data in all_chars:
        # Safety check for corrupted data
        if "name" not in char_data:
            continue
            
        char_name = char_data["name"]
        char_key = char_name.lower()
        player_name = char_data.get("player_name", "Unknown")
        
        # Display as "Character Name (Player Name)"
        display_name = f"{char_name} ({player_name})"
        
        # The value MUST be a unique identifier for both user and char
        # We'll join them with a colon
        unique_value = f"{user_id}:{char_key}"
        
        if current.lower() in display_name.lower():
            choices.append(app_commands.Choice(name=display_name, value=unique_value))
    
    print(f"DEBUG: Found {len(choices)} matching choices for DM.")
    return choices[:25] # Discord limit of 25 choices


# --- DICE ROLLING ---
def roll_dice(formula: str) -> Tuple[int, str]:
    """Rolls dice based on a formula like 1d20+5 or 3d6."""
    parts = re.findall(r'(\d+)d(\d+)([+\-]\d+)?', formula)
    if not parts:
        raise ValueError("Invalid dice formula. Use format `1d20+5` or `3d6`.")
    
    rolls_str = []
    total = 0
    
    # This logic handles one roll, e.g. "1d20+5" or "3d6"
    part = parts[0]
    num_dice = int(part[0])
    die_size = int(part[1])
    modifier = int(part[2]) if part[2] else 0
    
    for _ in range(num_dice):
        roll = random.randint(1, die_size)
        rolls_str.append(str(roll))
        total += roll
        
    total += modifier
    
    # Build the pretty string: e.g., "[13, 5] + 5"
    result_str = f"[`{', '.join(rolls_str)}`]"
    if modifier > 0:
        result_str += f" + {modifier}"
    elif modifier < 0:
        result_str += f" - {abs(modifier)}"
        
    return total, result_str

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # We need this for the !sync command

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# --- DND COMMAND GROUP ---
dnd_group = app_commands.Group(name="dnd", description="Manage your D&D characters.")

# --- DND / CREATE ---
@dnd_group.command(name="create", description="Create a new D&D character.")
@app_commands.rename(char_class='class')
async def create(interaction: discord.Interaction, name: str, race: str, char_class: str):
    """Creates a new character and saves it."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char_name_key = name.lower() # Use lowercase name as the key

    # Check if character already exists
    existing_char = await get_character_data(user_id, char_name_key)
    if existing_char:
        await interaction.followup.send(f"Error: You already have a character named '{name}'.")
        return

    new_char = get_new_char_data(name, race, char_class, interaction.user.display_name)
    
    await save_character_data(user_id, char_name_key, new_char)

    await interaction.followup.send(f"Character '{name}' (Level 1 {race} {char_class}) has been created!")

# --- DND / DELETE ---
@dnd_group.command(name="delete", description="Delete one of your characters.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def delete(interaction: discord.Interaction, character: str):
    """Deletes a character."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return

    user_id = str(interaction.user.id)
    char_name_key = character # Autocomplete now sends the key
    
    char_data = await get_character_data(user_id, char_name_key)
    if not char_data:
        await interaction.followup.send(f"Error: Character not found.")
        return
        
    char_name = char_data["name"] # Get the pretty name before deleting
    await delete_character_data(user_id, char_name_key)
    
    await interaction.followup.send(f"Character '{char_name}' has been deleted.")

# --- DND / MIGRATEJSON ---
@dnd_group.command(name="migratejson", description="Owner-only: Upload characters from local JSON to Firestore.")
async def migratejson(interaction: discord.Interaction):
    """Migrates all data from characters.json to Firestore."""
    await interaction.response.defer(ephemeral=True)
    
    if str(interaction.user.id) != OWNER_ID:
        await interaction.followup.send("Error: This is an owner-only command.")
        return
        
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    if not os.path.exists(LEGACY_CHAR_DATA_FILE):
        await interaction.followup.send(f"Error: `characters.json` not found. Nothing to migrate.")
        return

    try:
        with open(LEGACY_CHAR_DATA_FILE, 'r') as f:
            local_data = json.load(f)
    except Exception as e:
        await interaction.followup.send(f"Error reading `characters.json`: {e}")
        return
        
    migrated_count = 0
    await interaction.followup.send(f"Starting migration of all data from `characters.json` to Firestore. This may take a moment...")
    
    # This template ensures all new fields are added during migration
    template_data = get_new_char_data("template", "", "", "")
    
    for user_id, chars in local_data.items():
        for char_key, char_data in chars.items():
            # Add any missing fields to the old data before uploading
            for key, default_value in template_data.items():
                if key not in char_data:
                    char_data[key] = default_value
            
            # Use the proper key (lowercase name)
            final_key = char_data["name"].lower()
            await save_character_data(user_id, final_key, char_data)
            migrated_count += 1
            
    await interaction.edit_original_response(content=f"**Migration complete!**\nSuccessfully migrated {migrated_count} character entries to Firestore.")

# --- DND / FIXDATA ---
@dnd_group.command(name="fixdata", description="Owner-only: Fixes data in Firestore (use migratejson first).")
async def fixdata(interaction: discord.Interaction):
    """Finds and updates all character docs in Firestore with new fields."""
    await interaction.response.defer(ephemeral=True)
    
    if str(interaction.user.id) != OWNER_ID:
        await interaction.followup.send("Error: This is an owner-only command.")
        return
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return

    await interaction.followup.send("Starting data integrity check across all users in Firestore. This may take a while...")
    
    template_data = get_new_char_data("template", "", "", "")
    fixed_count = 0
    
    try:
        users_ref = db.collection('users')
        # --- FIX: Use async .get() via executor ---
        user_docs = await client.loop.run_in_executor(None, users_ref.get)
        
        for user in user_docs:
            user_id = user.id
            chars_ref = user.reference.collection('characters')
            # --- FIX: Use async .get() via executor ---
            char_docs = await client.loop.run_in_executor(None, chars_ref.get)
            
            for char in char_docs:
                char_data = char.to_dict()
                updates = {}
                
                # Check for missing fields
                for key, default_value in template_data.items():
                    if key not in char_data:
                        updates[key] = default_value
                        fixed_count += 1
                
                if updates:
                    # Apply updates to Firestore
                    await client.loop.run_in_executor(None, lambda: char.reference.update(updates))

    except Exception as e:
        await interaction.edit_original_response(content=f"An error occurred during fixdata: {e}")
        return

    if fixed_count > 0:
        await interaction.edit_original_response(content=f"Successfully fixed/updated {fixed_count} data fields in Firestore.")
    else:
        await interaction.edit_original_response(content="All character data in Firestore is already up-to-date.")


# --- DND / VIEW GROUP ---
view_group = app_commands.Group(name="view", description="View your character sheet.", parent=dnd_group)

@view_group.command(name="main", description="View your main character stats.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def view_main(interaction: discord.Interaction, character: str):
    """Displays the main character sheet embed."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char_name_key = character # Autocomplete sends the key
    
    char = await get_character_data(user_id, char_name_key)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    # --- SAFETY FIX: Use .get() for all fields to prevent KeyErrors ---
    
    # Calculate modifiers
    str_mod = calculate_modifier(char.get('strength', 10))
    dex_mod = calculate_modifier(char.get('dexterity', 10))
    con_mod = calculate_modifier(char.get('constitution', 10))
    int_mod = calculate_modifier(char.get('intelligence', 10))
    wis_mod = calculate_modifier(char.get('wisdom', 10))
    cha_mod = calculate_modifier(char.get('charisma', 10))
    
    # Calculate Initiative
    initiative = dex_mod
    
    # Build embed
    embed = discord.Embed(
        title=f"{char.get('name', 'Unknown')} - {char.get('class_level', 'Level 1')}",
        description=f"{char.get('race', 'N/A')} | {char.get('background', 'N/A')} | {char.get('alignment', 'N/A')} | {char.get('experience_points', 0)} XP",
        color=discord.Color.blue()
    )
    embed.set_author(name=f"Player: {char.get('player_name', 'Unknown')}")

    # Ability Scores
    embed.add_field(
        name="Ability Scores",
        value=f"**STR:** {char.get('strength', 10)} (`{str_mod:+}`)\n"
              f"**DEX:** {char.get('dexterity', 10)} (`{dex_mod:+}`)\n"
              f"**CON:** {char.get('constitution', 10)} (`{con_mod:+}`)\n"
              f"**INT:** {char.get('intelligence', 10)} (`{int_mod:+}`)\n"
              f"**WIS:** {char.get('wisdom', 10)} (`{wis_mod:+}`)\n"
              f"**CHA:** {char.get('charisma', 10)} (`{cha_mod:+}`)",
        inline=True
    )
    
    # Combat
    hp_display = f"{char.get('current_hp', 10)}/{char.get('max_hp', 10)}"
    if char.get('temphp', 0) > 0:
        hp_display += f" (+{char.get('temphp', 0)} Temp)"
        
    ds_succ = "✅" * char.get('death_save_success', 0) + "❌" * (3 - char.get('death_save_success', 0))
    ds_fail = "✅" * char.get('death_save_fail', 0) + "❌" * (3 - char.get('death_save_fail', 0))

    embed.add_field(
        name="Combat",
        value=f"**Armor Class:** {char.get('armor_class', 10)}\n"
              f"**Hit Points:** {hp_display}\n"
              f"**Initiative:** `{initiative:+}`\n"
              f"**Speed:** {char.get('speed', 30)}ft\n"
              f"**Inspiration:** {'✅' if char.get('inspiration', 0) > 0 else '❌'}\n"
              f"**Hit Dice:** {char.get('hitdice_current', 1)}/{char.get('hitdice_total', 1)}\n"
              f"**Death Saves:** S {ds_succ} | F {ds_fail}",
        inline=True
    )
    
    # Saving Throws
    pb = char.get('proficiency_bonus', 2)
    saves_str = ""
    passive_perc = 10 + wis_mod # Base passive perception
    
    for save_name in SAVES_LIST:
        ability_key = get_ability_for_skill(save_name)
        mod = calculate_modifier(char.get(ability_key, 10))
        if save_name in char.get('proficiencies', []):
            bonus = mod + pb
            saves_str += f"`[x]` **{save_name.split(' ')[0]}:** `{bonus:+}`\n"
        else:
            bonus = mod
            saves_str += f"`[ ]` {save_name.split(' ')[0]}: `{bonus:+}`\n"
            
    embed.add_field(name="Saving Throws", value=saves_str, inline=True)
    
    # Skills
    skills_str = ""
    for skill_name in SKILLS_LIST:
        ability_key = get_ability_for_skill(skill_name)
        mod = calculate_modifier(char.get(ability_key, 10))
        
        if skill_name in char.get('proficiencies', []):
            bonus = mod + pb
            skills_str += f"`[x]` **{skill_name.split(' (')[0]}:** `{bonus:+}`\n"
            if skill_name == "Perception (Wis)":
                passive_perc = 10 + bonus # Add prof if proficient
        else:
            bonus = mod
            skills_str += f"`[ ]` {skill_name.split(' (')[0]}: `{bonus:+}`\n"
            if skill_name == "Perception (Wis)":
                passive_perc = 10 + bonus # Just the mod
                
    embed.add_field(name="Skills", value=skills_str, inline=True)
    embed.add_field(name="Passive Perception", value=f"`{passive_perc}`", inline=True)
    embed.add_field(name="Proficiency Bonus", value=f"`+{pb}`", inline=True)

    # Attacks
    attacks_str = ""
    if char.get('attacks', []):
        for atk in char.get('attacks', []):
            attacks_str += f"**{atk['name']}:** `{atk['bonus']}` | `{atk['damage']}`\n"
    embed.add_field(name="Attacks & Spellcasting", value=truncate_text(attacks_str, 1024) or "No attacks added.", inline=False)
    
    # Features
    features_str = ""
    if char.get('features_traits', []):
        for feat in char.get('features_traits', []):
            features_str += f"**{feat['name']}:** {feat['desc']}\n"
    # --- FIX: Truncate this field to prevent 1024 char error ---
    embed.add_field(name="Features & Traits", value=truncate_text(features_str, 1024) or "No features added.", inline=False)

    await interaction.followup.send(embed=embed)


@view_group.command(name="personality", description="View your character's personality and backstory.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def view_personality(interaction: discord.Interaction, character: str):
    """Displays the personality/backstory embed."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    embed = discord.Embed(
        title=f"{char.get('name', 'Unknown')} - Personality & Backstory",
        color=discord.Color.green()
    )
    embed.add_field(name="Personality Trait", value=truncate_text(char.get('personality_trait')), inline=False)
    embed.add_field(name="Ideals", value=truncate_text(char.get('ideals')), inline=False)
    embed.add_field(name="Bonds", value=truncate_text(char.get('bonds')), inline=False)
    embed.add_field(name="Flaws", value=truncate_text(char.get('flaws')), inline=False)
    embed.add_field(name="Backstory", value=truncate_text(char.get('backstory')), inline=False)
    
    await interaction.followup.send(embed=embed)

@view_group.command(name="extras", description="View your inventory and other notes.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def view_extras(interaction: discord.Interaction, character: str):
    """Displays the equipment/notes embed."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    embed = discord.Embed(
        title=f"{char.get('name', 'Unknown')} - Extras",
        color=discord.Color.orange()
    )
    
    # Equipment
    equip_str = ""
    if char.get('equipment', []):
        for item in char.get('equipment', []):
            equip_str += f"**{item['name']}** (x{item['qty']})\n"
    embed.add_field(name="Equipment", value=truncate_text(equip_str, 1024) or "Empty", inline=True)
    
    embed.add_field(name="Treasure", value=truncate_text(char.get('treasure'), 1024) or "Empty", inline=True)
    embed.add_field(name="Character Appearance", value=truncate_text(char.get('appearance')), inline=False)
    embed.add_field(name="Allies & Organizations", value=truncate_text(char.get('allies_orgs')), inline=False)
    embed.add_field(name="Other Proficiencies & Languages", value=truncate_text(char.get('other_proficiencies')), inline=False)

    await interaction.followup.send(embed=embed)


@view_group.command(name="spells", description="View your character's spellbook.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def view_spells(interaction: discord.Interaction, character: str):
    """Displays the spellbook embed."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    if not char.get('spellcasting_class', ''):
        await interaction.followup.send(f"Error: {char.get('name', 'Unknown')} does not have a spellcasting class set. Use `/dnd spell set-info`.")
        return
        
    embed = discord.Embed(
        title=f"{char.get('name', 'Unknown')} - Spellbook ({char.get('spellcasting_class')})",
        color=discord.Color.purple()
    )
    embed.add_field(name="Spellcasting Ability", value=char.get('spellcasting_ability', 'N/A'), inline=True)
    embed.add_field(name="Spell Save DC", value=char.get('spell_save_dc', 8), inline=True)
    embed.add_field(name="Spell Attack Bonus", value=char.get('spell_attack_bonus', 0), inline=True)
    
    spellbook = char.get('spellbook', {})
    for level_key, level_name in [(c.value, c.name) for c in SPELL_LEVELS]:
        spells = spellbook.get(level_key, [])
        if spells:
            embed.add_field(name=f"{level_name}s", value=truncate_text("\n".join(spells)), inline=False)
            
    await interaction.followup.send(embed=embed)

# --- NEW: DM-ONLY VIEW COMMAND ---
@dnd_group.command(name="dm-view", description="[Owner-Only] View any character sheet in the database.")
@app_commands.autocomplete(character=dm_character_autocomplete)
@app_commands.rename(character='character_and_owner')
async def dm_view(interaction: discord.Interaction, character: str):
    """Owner-only command to view any character. Character value is 'user_id:char_key'"""
    await interaction.response.defer(ephemeral=True)
    if str(interaction.user.id) != OWNER_ID:
        await interaction.followup.send("Error: This is an owner-only command.")
        return
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return

    try:
        # Split the unique value 'user_id:char_key'
        user_id, char_name_key = character.split(":", 1)
    except ValueError:
        await interaction.followup.send("Error: Invalid character selection. Please use the autocomplete.")
        return

    char = await get_character_data(user_id, char_name_key)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    # --- Re-using the exact same logic as view_main ---
    # --- SAFETY FIX: Use .get() for all fields ---
    str_mod = calculate_modifier(char.get('strength', 10))
    dex_mod = calculate_modifier(char.get('dexterity', 10))
    con_mod = calculate_modifier(char.get('constitution', 10))
    int_mod = calculate_modifier(char.get('intelligence', 10))
    wis_mod = calculate_modifier(char.get('wisdom', 10))
    cha_mod = calculate_modifier(char.get('charisma', 10))
    initiative = dex_mod
    
    embed = discord.Embed(
        title=f"{char.get('name', 'Unknown')} - {char.get('class_level', 'Level 1')}",
        description=f"{char.get('race', 'N/A')} | {char.get('background', 'N/A')} | {char.get('alignment', 'N/A')} | {char.get('experience_points', 0)} XP",
        color=discord.Color.red() # Red embed for DM view
    )
    embed.set_author(name=f"Player: {char.get('player_name', 'Unknown')} (User ID: {user_id})")

    embed.add_field(
        name="Ability Scores",
        value=f"**STR:** {char.get('strength', 10)} (`{str_mod:+}`)\n"
              f"**DEX:** {char.get('dexterity', 10)} (`{dex_mod:+}`)\n"
              f"**CON:** {char.get('constitution', 10)} (`{con_mod:+}`)\n"
              f"**INT:** {char.get('intelligence', 10)} (`{int_mod:+}`)\n"
              f"**WIS:** {char.get('wisdom', 10)} (`{wis_mod:+}`)\n"
              f"**CHA:** {char.get('charisma', 10)} (`{cha_mod:+}`)",
        inline=True
    )
    
    hp_display = f"{char.get('current_hp', 10)}/{char.get('max_hp', 10)}"
    if char.get('temphp', 0) > 0:
        hp_display += f" (+{char.get('temphp', 0)} Temp)"
    ds_succ = "✅" * char.get('death_save_success', 0) + "❌" * (3 - char.get('death_save_success', 0))
    ds_fail = "✅" * char.get('death_save_fail', 0) + "❌" * (3 - char.get('death_save_fail', 0))

    embed.add_field(
        name="Combat",
        value=f"**Armor Class:** {char.get('armor_class', 10)}\n"
              f"**Hit Points:** {hp_display}\n"
              f"**Initiative:** `{initiative:+}`\n"
              f"**Speed:** {char.get('speed', 30)}ft\n"
              f"**Inspiration:** {'✅' if char.get('inspiration', 0) > 0 else '❌'}\n"
              f"**Hit Dice:** {char.get('hitdice_current', 1)}/{char.get('hitdice_total', 1)}\n"
              f"**Death Saves:** S {ds_succ} | F {ds_fail}",
        inline=True
    )
    
    pb = char.get('proficiency_bonus', 2)
    saves_str = ""
    passive_perc = 10 + wis_mod
    
    for save_name in SAVES_LIST:
        ability_key = get_ability_for_skill(save_name)
        mod = calculate_modifier(char.get(ability_key, 10))
        if save_name in char.get('proficiencies', []):
            bonus = mod + pb
            saves_str += f"`[x]` **{save_name.split(' ')[0]}:** `{bonus:+}`\n"
        else:
            bonus = mod
            saves_str += f"`[ ]` {save_name.split(' ')[0]}: `{bonus:+}`\n"
    embed.add_field(name="Saving Throws", value=saves_str, inline=True)
    
    skills_str = ""
    for skill_name in SKILLS_LIST:
        ability_key = get_ability_for_skill(skill_name)
        mod = calculate_modifier(char.get(ability_key, 10))
        if skill_name in char.get('proficiencies', []):
            bonus = mod + pb
            skills_str += f"`[x]` **{skill_name.split(' (')[0]}:** `{bonus:+}`\n"
            if skill_name == "Perception (Wis)":
                passive_perc = 10 + bonus
        else:
            bonus = mod
            skills_str += f"`[ ]` {skill_name.split(' (')[0]}: `{bonus:+}`\n"
            if skill_name == "Perception (Wis)":
                passive_perc = 10 + bonus
    embed.add_field(name="Skills", value=skills_str, inline=True)
    embed.add_field(name="Passive Perception", value=f"`{passive_perc}`", inline=True)
    embed.add_field(name="Proficiency Bonus", value=f"`+{pb}`", inline=True)

    attacks_str = ""
    if char.get('attacks', []):
        for atk in char.get('attacks', []):
            attacks_str += f"**{atk['name']}:** `{atk['bonus']}` | `{atk['damage']}`\n"
    embed.add_field(name="Attacks & Spellcasting", value=truncate_text(attacks_str, 1024) or "No attacks added.", inline=False)
    
    features_str = ""
    if char.get('features_traits', []):
        for feat in char.get('features_traits', []):
            features_str += f"**{feat['name']}:** {feat['desc']}\n"
    embed.add_field(name="Features & Traits", value=truncate_text(features_str, 1024) or "No features added.", inline=False)

    await interaction.followup.send(embed=embed)


# --- DND / SET GROUP ---
set_group = app_commands.Group(name="set", description="Update your character's stats.", parent=dnd_group)

@set_group.command(name="scores", description="Set your character's ability scores.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name', str_score='str', dex_score='dex', con_score='con', int_score='int', wis_score='wis', cha_score='cha')
async def set_scores(interaction: discord.Interaction, character: str,
                     str_score: Optional[int] = None, dex_score: Optional[int] = None, con_score: Optional[int] = None,
                     int_score: Optional[int] = None, wis_score: Optional[int] = None, cha_score: Optional[int] = None):
    """Updates ability scores."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    # Update scores that were provided
    if str_score is not None: char['strength'] = str_score
    if dex_score is not None: char['dexterity'] = dex_score
    if con_score is not None: char['constitution'] = con_score
    if int_score is not None: char['intelligence'] = int_score
    if wis_score is not None: char['wisdom'] = wis_score
    if cha_score is not None: char['charisma'] = cha_score
    
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Ability scores for '{char['name']}' have been updated.")


@set_group.command(name="info", description="Set your character's basic info.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name', class_level='class', experience='xp', prof_bonus='pb')
async def set_info(interaction: discord.Interaction, character: str,
                   background: Optional[str] = None, alignment: Optional[str] = None,
                   experience: Optional[int] = None, class_level: Optional[str] = None,
                   prof_bonus: Optional[int] = None):
    """Updates basic character info."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    if background is not None: char['background'] = background
    if alignment is not None: char['alignment'] = alignment
    if experience is not None: char['experience_points'] = experience
    if class_level is not None: char['class_level'] = class_level
    if prof_bonus is not None: char['proficiency_bonus'] = prof_bonus
    
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Basic info for '{char['name']}' have been updated.")


@set_group.command(name="combat", description="Set your character's combat stats.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def set_combat(interaction: discord.Interaction, character: str,
                     ac: Optional[int] = None, max_hp: Optional[int] = None,
                     current_hp: Optional[int] = None, temphp: Optional[int] = None,
                     speed: Optional[int] = None, inspiration: Optional[int] = None):
    """Updates combat stats."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    if ac is not None: char['armor_class'] = ac
    if max_hp is not None: char['max_hp'] = max_hp
    if current_hp is not None: char['current_hp'] = current_hp
    if temphp is not None: char['temphp'] = temphp
    if speed is not None: char['speed'] = speed
    if inspiration is not None: char['inspiration'] = inspiration
    
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Combat stats for '{char['name']}' have been updated.")


@set_group.command(name="hitdice", description="Set your character's hit dice.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def set_hitdice(interaction: discord.Interaction, character: str,
                      total: Optional[int] = None, current: Optional[int] = None):
    """Updates hit dice."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    if total is not None: char['hitdice_total'] = total
    if current is not None: char['hitdice_current'] = current
    
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Hit dice for '{char['name']}' have been updated.")


@set_group.command(name="death_saves", description="Set your character's death saves.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def set_death_saves(interaction: discord.Interaction, character: str,
                          successes: Optional[int] = None, failures: Optional[int] = None):
    """Updates death saves."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    if successes is not None: char['death_save_success'] = successes
    if failures is not None: char['death_save_fail'] = failures
    
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Death saves for '{char['name']}' have been updated.")


@set_group.command(name="personality", description="Set your character's personality traits.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def set_personality(interaction: discord.Interaction, character: str,
                          trait: Optional[str] = None, ideal: Optional[str] = None,
                          bond: Optional[str] = None, flaw: Optional[str] = None):
    """Updates personality fields."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    if trait is not None: char['personality_trait'] = trait
    if ideal is not None: char['ideals'] = ideal
    if bond is not None: char['bonds'] = bond
    if flaw is not None: char['flaws'] = flaw
    
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Personality fields for '{char['name']}' have been updated.")


@set_group.command(name="other_profs", description="Set your 'Other Proficiencies & Languages'.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def set_other_profs(interaction: discord.Interaction, character: str, text: str):
    """Updates other proficiencies text block."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
        
    char['other_proficiencies'] = text
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Other proficiencies for '{char['name']}' have been updated.")


@set_group.command(name="appearance", description="Set your character's appearance.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def set_appearance(interaction: discord.Interaction, character: str, text: str):
    """Updates appearance text block."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
        
    char['appearance'] = text
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Appearance for '{char['name']}' have been updated.")


@set_group.command(name="allies", description="Set your character's allies & organizations.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def set_allies(interaction: discord.Interaction, character: str, text: str):
    """Updates allies text block."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
        
    char['allies_orgs'] = text
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Allies & orgs for '{char['name']}' have been updated.")


@set_group.command(name="backstory", description="Set your character's backstory.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def set_backstory(interaction: discord.Interaction, character: str, text: str):
    """Updates backstory text block."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
        
    char['backstory'] = text
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Backstory for '{char['name']}' have been updated.")


@set_group.command(name="treasure", description="Set your character's treasure.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name')
async def set_treasure(interaction: discord.Interaction, character: str, text: str):
    """Updates treasure text block."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
        
    char['treasure'] = text
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Treasure for '{char['name']}' have been updated.")


# --- DND / PROFICIENCY GROUP ---
prof_group = app_commands.Group(name="prof", description="Manage your proficiencies.", parent=dnd_group)

async def prof_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocompletes skills and saving throws."""
    all_profs = SKILLS_LIST + SAVES_LIST
    return [
        app_commands.Choice(name=prof_name, value=prof_name)
        for prof_name in all_profs if current.lower() in prof_name.lower()
    ]

@prof_group.command(name="add", description="Add a skill or saving throw proficiency.")
@app_commands.autocomplete(character=character_autocomplete, proficiency=prof_autocomplete)
@app_commands.rename(character='name')
async def prof_add(interaction: discord.Interaction, character: str, proficiency: str):
    """Adds a proficiency to your character."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    if proficiency not in (SKILLS_LIST + SAVES_LIST):
        await interaction.followup.send(f"Error: Invalid proficiency. Please choose from the list.")
        return
        
    if proficiency in char.get('proficiencies', []):
        await interaction.followup.send(f"'{char['name']}' already has proficiency in {proficiency}.")
        return
        
    if 'proficiencies' not in char: char['proficiencies'] = []
    char['proficiencies'].append(proficiency)
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Added proficiency in {proficiency} to '{char['name']}'.")


@prof_group.command(name="remove", description="Remove a skill or saving throw proficiency.")
@app_commands.autocomplete(character=character_autocomplete, proficiency=prof_autocomplete)
@app_commands.rename(character='name')
async def prof_remove(interaction: discord.Interaction, character: str, proficiency: str):
    """Removes a proficiency from your character."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    if proficiency not in char.get('proficiencies', []):
        await interaction.followup.send(f"'{char['name']}' does not have proficiency in {proficiency}.")
        return
        
    char['proficiencies'].remove(proficiency)
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Removed proficiency in {proficiency} from '{char['name']}'.")


# --- DND / FEATURE GROUP ---
feature_group = app_commands.Group(name="feature", description="Manage features & traits.", parent=dnd_group)

# --- AUTOCOMPLETE FIX: Use interaction.namespace ---
async def feature_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocompletes features for the user."""
    user_id = str(interaction.user.id)
    char_key = interaction.namespace.character # FIX: Get value from namespace
    
    if not char_key: # Handle case where character is not yet filled
        return []
        
    char = await get_character_data(user_id, char_key)
    if not char:
        return []
        
    return [
        app_commands.Choice(name=feat['name'], value=feat['name'])
        for feat in char.get('features_traits', [])
        if current.lower() in feat['name'].lower()
    ]

@feature_group.command(name="add", description="Add a new feature or trait.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name') # Only rename character
async def feature_add(interaction: discord.Interaction, character: str, feature_name: str, description: str):
    """Adds a feature/trait to your character."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    # Check if feature already exists
    if any(feat['name'].lower() == feature_name.lower() for feat in char.get('features_traits', [])):
        await interaction.followup.send(f"Error: A feature named '{feature_name}' already exists.")
        return
        
    if 'features_traits' not in char: char['features_traits'] = []
    char['features_traits'].append({"name": feature_name, "desc": description})
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Added feature '{feature_name}' to '{char['name']}'.")

@feature_group.command(name="remove", description="Remove a feature or trait.")
@app_commands.autocomplete(character=character_autocomplete, feature_name=feature_autocomplete) # 'feature_name' now correctly maps
@app_commands.rename(character='name') # Only rename character
async def feature_remove(interaction: discord.Interaction, character: str, feature_name: str):
    """Removes a feature/trait from your character."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    feature_to_remove = None
    for feat in char.get('features_traits', []):
        if feat['name'].lower() == feature_name.lower():
            feature_to_remove = feat
            break
            
    if feature_to_remove:
        char['features_traits'].remove(feature_to_remove)
        await save_character_data(user_id, character, char)
        await interaction.followup.send(f"Removed feature '{feature_name}' from '{char['name']}'.")
    else:
        await interaction.followup.send(f"Error: Feature '{feature_name}' not found.")


# --- DND / ATTACK GROUP ---
attack_group = app_commands.Group(name="attack", description="Manage attacks.", parent=dnd_group)

# --- AUTOCOMPLETE FIX: Use interaction.namespace ---
async def attack_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocompletes attacks for the user."""
    user_id = str(interaction.user.id)
    char_key = interaction.namespace.character # FIX: Get value from namespace
    
    if not char_key:
        return []
        
    char = await get_character_data(user_id, char_key)
    if not char:
        return []
        
    return [
        app_commands.Choice(name=atk['name'], value=atk['name'])
        for atk in char.get('attacks', [])
        if current.lower() in atk['name'].lower()
    ]

@attack_group.command(name="add", description="Add a new attack or spell.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name', atk_bonus='bonus', damage_type='damage')
async def attack_add(interaction: discord.Interaction, character: str, attack_name: str, atk_bonus: str, damage_type: str):
    """Adds an attack to your character."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    if any(atk['name'].lower() == attack_name.lower() for atk in char.get('attacks', [])):
        await interaction.followup.send(f"Error: An attack named '{attack_name}' already exists.")
        return
        
    if 'attacks' not in char: char['attacks'] = []
    char['attacks'].append({"name": attack_name, "bonus": atk_bonus, "damage": damage_type})
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Added attack '{attack_name}' to '{char['name']}'.")

@attack_group.command(name="remove", description="Remove an attack or spell.")
@app_commands.autocomplete(character=character_autocomplete, attack_name=attack_autocomplete)
@app_commands.rename(character='name')
async def attack_remove(interaction: discord.Interaction, character: str, attack_name: str):
    """Removes an attack from your character."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    attack_to_remove = None
    for atk in char.get('attacks', []):
        if atk['name'].lower() == attack_name.lower():
            attack_to_remove = atk
            break
            
    if attack_to_remove:
        char['attacks'].remove(attack_to_remove)
        await save_character_data(user_id, character, char)
        await interaction.followup.send(f"Removed attack '{attack_name}' from '{char['name']}'.")
    else:
        await interaction.followup.send(f"Error: Attack '{attack_name}' not found.")


# --- DND / ITEM GROUP ---
item_group = app_commands.Group(name="item", description="Manage equipment.", parent=dnd_group)

# --- AUTOCOMPLETE FIX: Use interaction.namespace ---
async def item_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocompletes items for the user."""
    user_id = str(interaction.user.id)
    char_key = interaction.namespace.character # FIX: Get value from namespace
    
    if not char_key:
        return []
        
    char = await get_character_data(user_id, char_key)
    if not char:
        return []
        
    return [
        app_commands.Choice(name=item['name'], value=item['name'])
        for item in char.get('equipment', [])
        if current.lower() in item['name'].lower()
    ]

@item_group.command(name="add", description="Add an item to your inventory.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name') # Only rename character
async def item_add(interaction: discord.Interaction, character: str, item_name: str, quantity: int):
    """Adds an item to your character."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    if 'equipment' not in char: char['equipment'] = []
    # Check if item exists to stack it
    for item in char['equipment']:
        if item['name'].lower() == item_name.lower():
            item['qty'] += quantity
            await save_character_data(user_id, character, char)
            await interaction.followup.send(f"Added {quantity} to '{item_name}', new total: {item['qty']}.")
            return
            
    # If not, add new item
    char['equipment'].append({"name": item_name, "qty": quantity})
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Added item '{item_name}' (x{quantity}) to '{char['name']}'.")

@item_group.command(name="remove", description="Remove an item from your inventory.")
@app_commands.autocomplete(character=character_autocomplete, item_name=item_autocomplete)
@app_commands.rename(character='name') # Only rename character
async def item_remove(interaction: discord.Interaction, character: str, item_name: str):
    """Removes an item from your character."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    item_to_remove = None
    for item in char.get('equipment', []):
        if item['name'].lower() == item_name.lower():
            item_to_remove = item
            break
            
    if item_to_remove:
        char['equipment'].remove(item_to_remove)
        await save_character_data(user_id, character, char)
        await interaction.followup.send(f"Removed item '{item_name}' from '{char['name']}'.")
    else:
        await interaction.followup.send(f"Error: Item '{item_name}' not found.")


# --- DND / SPELL GROUP ---
spell_group = app_commands.Group(name="spell", description="Manage spells.", parent=dnd_group)

@spell_group.command(name="set-info", description="Set your spellcasting class and stats.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.rename(character='name', casting_class='class', ability='ability', save_dc='dc', attack_bonus='bonus')
async def spell_set_info(interaction: discord.Interaction, character: str,
                         casting_class: str, ability: str,
                         save_dc: int, attack_bonus: int):
    """Sets the main spellcasting stats."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
        
    char['spellcasting_class'] = casting_class
    char['spellcasting_ability'] = ability
    char['spell_save_dc'] = save_dc
    char['spell_attack_bonus'] = attack_bonus
    
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Spellcasting info for '{char['name']}' has been updated.")


@spell_group.command(name="add", description="Add a spell to your spellbook.")
@app_commands.autocomplete(character=character_autocomplete)
@app_commands.choices(level=SPELL_LEVELS)
@app_commands.rename(character='name') #
async def spell_add(interaction: discord.Interaction, character: str, level: str, spell_name: str):
    """Adds a spell to your character's spellbook."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    if spell_name in char.get('spellbook', {}).get(level, []):
        await interaction.followup.send(f"Error: '{spell_name}' is already in your {level} list.")
        return
        
    if 'spellbook' not in char: char['spellbook'] = {}
    if level not in char['spellbook']: char['spellbook'][level] = []
    char['spellbook'][level].append(spell_name)
    await save_character_data(user_id, character, char)
    await interaction.followup.send(f"Added spell '{spell_name}' to '{char['name']}'s {level} list.")

# --- AUTOCOMPLETE FIX: Use interaction.namespace ---
async def spell_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocompletes spells for the user."""
    user_id = str(interaction.user.id)
    char_key = interaction.namespace.character # FIX: Get value from namespace
    
    if not char_key:
        return []
        
    char = await get_character_data(user_id, char_key)
    if not char:
        return []
        
    all_spells = []
    for level_spells in char.get('spellbook', {}).values():
        all_spells.extend(level_spells)
        
    return [
        app_commands.Choice(name=spell, value=spell)
        for spell in all_spells
        if current.lower() in spell.lower()
    ]

@spell_group.command(name="remove", description="Remove a spell from your spellbook.")
@app_commands.autocomplete(character=character_autocomplete, spell_name=spell_autocomplete)
@app_commands.rename(character='name') # Only rename character
async def spell_remove(interaction: discord.Interaction, character: str, spell_name: str):
    """Removes a spell from your character's spellbook."""
    await interaction.response.defer(ephemeral=True)
    if db is None:
        await interaction.followup.send("Error: Database connection is not established.")
        return
        
    user_id = str(interaction.user.id)
    char = await get_character_data(user_id, character)
    if not char:
        await interaction.followup.send(f"Error: Character not found.")
        return
    
    spell_found = False
    for level, spells in char.get('spellbook', {}).items():
        if spell_name in spells:
            spells.remove(spell_name)
            spell_found = True
            break
            
    if spell_found:
        await save_character_data(user_id, character, char)
        await interaction.followup.send(f"Removed spell '{spell_name}' from '{char['name']}'.")
    else:
        await interaction.followup.send(f"Error: Spell '{spell_name}' not found in your spellbook.")


# --- GLOBAL /ROLL COMMAND ---
@tree.command(name="roll", description="Rolls dice, e.g., 1d20+5 or 3d6")
async def roll(interaction: discord.Interaction, formula: str):
    """Rolls dice based on a formula."""
    try:
        total, result_str = roll_dice(formula)
        await interaction.response.send_message(
            f"{interaction.user.mention} rolls `{formula}`...\n"
            + f"**You rolled {total}!** {result_str}"
        )
    except ValueError as e:
        await interaction.response.send_message(
            f"Error: {e}", ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"An unexpected error occurred: {e}", ephemeral=True
        )

# --- ADD COMMANDS TO TREE ---
tree.add_command(dnd_group)

print("DEBUG: All command groups added to tree.")

# --- "BOT READY" EVENT ---
@client.event
async def on_ready():
    """This function runs when the bot successfully connects to Discord."""
    print("DEBUG: 'on_ready' event fired. Attempting to sync...")
    try:
        if MY_GUILD:
            # This is the magic line that fixed our sync issue.
            # It copies global commands (like /roll) to our guild AND
            # syncs guild-specific commands (like /dnd)
            tree.copy_global_to(guild=MY_GUILD)
            await tree.sync(guild=MY_GUILD)
            print(f"DEBUG: Commands synced to guild {GUILD_ID}.")
        else:
            await tree.sync()
            print("DEBUG: Commands synced globally.")

        print(f'Bot v2 is ONLINE and READY!')
        print(f'Logged in as: {client.user} (ID: {client.user.id})')

    except Exception as e:
        print(f"DEBUG: CRITICAL ERROR during sync: {e}")

# --- MANUAL SYNC COMMAND ---
@client.event
async def on_message(message):
    """Listens for messages to trigger a manual sync."""
    if message.author == client.user:
        return

    if str(message.author.id) == OWNER_ID and message.content == "!sync":
        print("DEBUG: Manual sync triggered by owner.")
        await message.channel.send("Attempting manual sync...")
        try:
            if MY_GUILD:
                tree.copy_global_to(guild=MY_GUILD)
                await tree.sync(guild=MY_GUILD)
                print(f"DEBUG: Commands synced to guild {GUILD_ID}.")
                await message.channel.send(f"Successfully synced commands to guild {GUILD_ID}.")
            else:
                await tree.sync()
                print("DEBUG: Commands synced globally.")
                await message.channel.send("Successfully synced commands globally.")
        except Exception as e:
            print(f"DEBUG: CRITICAL ERROR during manual sync: {e}")
            await message.channel.send(f"An error occurred during sync: {e}")

# --- RUN THE BOT ---
if __name__ == "__main__":
    print("DEBUG: Running bot...")
    if TOKEN is None:
        print("Error: DISCORD_TOKEN environment variable not found.")
    elif OWNER_ID is None:
        print("Error: OWNER_ID environment variable not found.")
    elif db is None:
        print("Error: Firestore database connection not found. Bot will not run.")
    else:
        try:
            client.run(TOKEN)
        except discord.errors.LoginFailure:
            print("Error: Invalid DISCORD_TOKEN.")
        except Exception as e:
            print(f"An error occurred while running the bot: {e}")