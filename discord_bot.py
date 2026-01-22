import discord
from discord.ext import commands

import datetime
from datetime import datetime

import os
import sys
import sqlite3
import random
import asyncio
import requests




# "U:\Python\uzlabot\.venv\Scripts\python.exe" -m pip install requests --force-reinstall --upgrade --target U:\Python\uzlabot\.venv\Lib\site-packages


test_start_time = datetime.now()




# Nastavení záměrů (intents)
intents = discord.Intents.default()
intents.message_content = True

# Vytvoření bota
bot = commands.Bot(command_prefix="!", intents=intents)

# Připojení k databázi
conn = sqlite3.connect("currency.db")
c = conn.cursor()

# Vytvoření tabulek, pokud neexistují

c.execute('''CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                quantity TEXT,
                price INTEGER)''')

c.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                last_daily TEXT,
                last_weekly TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS settings (
                setting_name TEXT PRIMARY KEY,
                setting_value TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS settings (
                setting_name TEXT PRIMARY KEY,
                setting_value TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS suggested_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                count TEXT,
                price INTEGER)''')

c.execute('''CREATE TABLE IF NOT EXISTS shop (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                count INTEGER,
                price INTEGER)''')

c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_name TEXT,
                quantity INTEGER,
                bought_at TEXT,
                PRIMARY KEY (user_id, item_name))''')


conn.commit()

currency_name = "Coinu"
admin_id = 00000000000 # Změň na ID role admina
moderator_role_id = 0000000000 # Změň na ID role moderátora

bought_at = datetime.now().strftime("%Y-%m-%d %H:%M UTC") # Zjsiti kdy hrac koupil predmet

@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user} je online!')
    try:
        await bot.tree.sync()
        print(f'✅ Slash příkazy synchronizovány!')
    except Exception as e:
        print(f'❌ Chyba při synchronizaci: {e}')

# Funkce pro získání nebo vytvoření uživatele v databázi
def get_user(user_id):
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return (user_id, 0, None, None)
    return user

# Slash příkaz /datum
@bot.tree.command(name="datum", description="Zobrazí aktuální datum")
async def datum(interaction: discord.Interaction):
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    await interaction.response.send_message(f"📅 Dnešní datum je: **{today}**")

# Slash příkaz /inventory
@bot.tree.command(name="inventory", description="Zobrazí tvůj inventář")
async def inventory(interaction: discord.Interaction):
    # Nejprve zjistíme, jaké sloupce tabulka obsahuje
    c.execute("PRAGMA table_info(inventory)")
    columns = [column[1] for column in c.fetchall()]
    
    # Sestavíme SQL dotaz podle existujících sloupců
    if 'bought_at' in columns:
        c.execute("SELECT inventory.item_name, inventory.quantity, inventory.bought_at, shop.id FROM inventory LEFT JOIN shop ON inventory.item_name = shop.name WHERE inventory.user_id = ?", (interaction.user.id,))
    else:
        c.execute("SELECT inventory.item_name, inventory.quantity, NULL as bought_at, shop.id FROM inventory LEFT JOIN shop ON inventory.item_name = shop.name WHERE inventory.user_id = ?", (interaction.user.id,))
    
    items = c.fetchall()

    if not items:
        await interaction.response.send_message("📭 Tvůj inventář je prázdný.")
        return

    embed = discord.Embed(title="🎒 **Tvůj inventář**", color=discord.Color.orange())
    
    for index, item in enumerate(items, 1):
        item_name, quantity, bought_at, item_id = item
        
        # Pokud ID není nalezeno (item už není v obchodě)
        item_id_display = f"ID: {item_id}" if item_id else "ID: Nedostupné"
        
        # Vytvoření řádku pro položku s emoji
        item_display = f"**{index}.** 📦 **{item_name}** | {item_id_display}\n"
        item_display += f"└─ 🔢 Počet: **{quantity}** ks"
        
        if bought_at:
            item_display += f" | 📅 Zakoupeno: **{bought_at}**"
        
        embed.add_field(name=f"{'━' * 20}", value=item_display, inline=False)

    embed.set_footer(text=f"Celkem předmětů: {len(items)}")
    await interaction.response.send_message(embed=embed)

# Slash příkaz /sendmsg
@bot.tree.command(name="sendmsg", description="Pošle zprávu do určeného kanálu")
async def sendmsg(interaction: discord.Interaction, channel_id: str, message: str):
    # Kontrola admin oprávnění
    if interaction.user.id != admin_id:
        await interaction.response.send_message("❌ Tento příkaz může používat pouze oprávněný uživatel!", ephemeral=True)
        return
    
    try:
        # Převedení channel_id na integer
        channel_id_int = int(channel_id)
        
        # Najití kanálu podle ID
        target_channel = bot.get_channel(channel_id_int)
        
        if target_channel is None:
            await interaction.response.send_message(f"❌ Kanál s ID `{channel_id}` nebyl nalezen!", ephemeral=True)
            return
        
        # Odeslání zprávy do cílového kanálu
        await target_channel.send(message)
        
        # Potvrzení odeslání
        await interaction.response.send_message(f"✅ Zpráva byla úspěšně odeslána do kanálu `{target_channel.name}` (ID: `{channel_id}`)", ephemeral=True)
        
    except ValueError:
        await interaction.response.send_message("❌ Neplatné ID kanálu! Musí být číslo.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ Bot nemá oprávnění psát do tohoto kanálu!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Došlo k chybě: {str(e)}", ephemeral=True)


@bot.tree.command(name="mute", description="Udělí mute označenému členovy")
async def mute(interaction: discord.Interaction, member: discord.Member, time: int):
    if interaction.user.id != admin_id:
        await interaction.response.send_message("❌ Tento příkaz může používat pouze oprávněný uživatel!", ephemeral=True)
        return
    await interaction.mute({discord.Member})
    await interaction.response.send_message("Uživatel: {discord.Member} byl úspěšně umlčen!")
    

# Slash příkaz /suggestitem
@bot.tree.command(name="item_suggest", description="Navrhne přidání nové položky do shopu")
async def suggestitem(interaction: discord.Interaction, name: str, quantity: str, price: int):
    c.execute("INSERT INTO suggestions (user_id, name, quantity, price) VALUES (?, ?, ?, ?)", 
              (interaction.user.id, name, quantity, price))
    conn.commit()
    
    suggest_id = c.lastrowid
    
    embed = discord.Embed(title="📌 Nový návrh položky", color=discord.Color.orange())
    embed.add_field(name="🛍 Název", value=name, inline=False)
    embed.add_field(name="📦 Počet", value=quantity if quantity != "X" else "Nekonečno", inline=False)
    embed.add_field(name="💰 Cena", value=f"{price} {currency_name}", inline=False)
    embed.add_field(name="🆔 ID návrhu", value=str(suggest_id), inline=False)
    embed.set_footer(text=f"Navrhl: {interaction.user.display_name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
    
    await interaction.response.send_message(embed=embed)

#slash příkaz /itemaccept

@bot.tree.command(name="item_accept", description="Schválí návrh a přidá položku do shopu")
async def itemaccept(interaction: discord.Interaction, suggest_id: int):
    if interaction.user.id != admin_id:
        await interaction.response.send_message("❌ Tento příkaz může používat pouze oprávněný uživatel!", ephemeral=True)
        return
    
    c.execute("SELECT name, quantity, price FROM suggestions WHERE id = ?", (suggest_id,))
    suggestion = c.fetchone()
    
    if not suggestion:
        await interaction.response.send_message("❌ Tento návrh neexistuje!", ephemeral=True)
        return
    
    name, quantity, price = suggestion
    quantity = -1 if quantity == "X" else int(quantity)
    
    c.execute("INSERT INTO shop (name, count, price) VALUES (?, ?, ?)", (name, quantity, price))
    conn.commit()
    
    await interaction.response.send_message(f"✅ Položka **{name}** byla úspěšně přidána do shopu!")

# Slash příkaz /item_remove – pouze pro moderátory
@bot.tree.command(name="item_remove", description="Odstraní předmět z obchodu podle ID (pouze pro moderátory)")
async def item_remove(interaction: discord.Interaction, item_id: int):
    # Ověření oprávnění
    if interaction.user.id != admin_id:
        await interaction.response.send_message("❌ Tento příkaz může používat pouze oprávněný uživatel!", ephemeral=True)
        return

    # Zkontroluj, zda existuje položka s daným ID
    c.execute("SELECT name FROM shop WHERE id = ?", (item_id,))
    item = c.fetchone()

    if not item:
        await interaction.response.send_message(f"❌ Předmět s ID `{item_id}` neexistuje.", ephemeral=True)
        return

    # Odstraň předmět
    c.execute("DELETE FROM shop WHERE id = ?", (item_id,))
    conn.commit()

    await interaction.response.send_message(f"🗑️ Předmět `{item[0]}` (ID: `{item_id}`) byl úspěšně odstraněn z obchodu.")


# Slash příkaz /item_restock
@bot.tree.command(name="item_restock", description="Doplní počet kusů itemu v obchodě")
async def item_restock(interaction: discord.Interaction, name: str, count: int):
    if interaction.user.id != admin_id:
        await interaction.response.send_message("❌ Tento příkaz může používat pouze oprávněný uživatel!", ephemeral=True)
        return
    if count <= 0:
        await interaction.response.send_message("❌ Počet musí být větší než 0.", ephemeral=True)
        return

    # Opraveno: změna 'stock' na 'count'
    c.execute("SELECT count FROM shop WHERE name = ?", (name,))
    item = c.fetchone()

    if item:
        new_count = item[0] + count  # Změna proměnné z new_stock na new_count
        # Opraveno: změna 'stock' na 'count'
        c.execute("UPDATE shop SET count = ? WHERE name = ?", (new_count, name))
        conn.commit()
        await interaction.response.send_message(f"✅ Do obchodu bylo přidáno {count}× `{name}`. Celkem skladem: {new_count}")
    else:
        await interaction.response.send_message(f"❌ Item `{name}` neexistuje v obchodě.", ephemeral=True)


# Slash příkaz /shop
@bot.tree.command(name="item_shop", description="Zobrazí obchod")
async def shop(interaction: discord.Interaction, page: int = 1):
    items_per_page = 5
    offset = (page - 1) * items_per_page
    c.execute("SELECT id, name, count, price FROM shop ORDER BY id LIMIT ? OFFSET ?", (items_per_page, offset))
    items = c.fetchall()

    if not items:
        await interaction.response.send_message("❌ Žádné položky v obchodě!", ephemeral=True)
        return

    embed = discord.Embed(title="🛍️ **Obchod**", color=discord.Color.orange())
    for item in items:
        item_id, name, count, price = item

        # Emo ikonky pro lepší přehlednost
        id_line = f"🆔 ID: `{item_id}`"
        name_line = f"📦 Název: **{name}**"
        count_line = f"🔢 Počet: {'❌ Vyprodáno' if count == 0 else f'{count} ks'}"
        price_line = f"💰 Cena: `{price} {currency_name}`"

        description = f"{id_line}\n{name_line}\n{count_line}\n{price_line}"
        embed.add_field(name="━━━━━━━━━━━━", value=description, inline=False)

    embed.set_footer(text=f"📄 Strana {page}")
    await interaction.response.send_message(embed=embed)

# Slash příkaz /item_buy
@bot.tree.command(name="item_buy", description="Koupí item z obchodu")
async def item_buy(interaction: discord.Interaction, name: str, count: int = 1):
    c.execute("SELECT * FROM shop WHERE name = ?", (name,))
    item = c.fetchone()
    
    if not item:
        await interaction.response.send_message("❌ Tento item neexistuje v obchodě.", ephemeral=True)
        return

    price = item[1] * count

    c.execute("SELECT wallet FROM users WHERE user_id = ?", (interaction.user.id,))
    wallet = c.fetchone()
    
    if wallet is None or wallet[0] < price:
        await interaction.response.send_message("❌ Nemáš dostatek peněz!", ephemeral=True)
        return

    # Odečti peníze
    c.execute("UPDATE users SET wallet = wallet - ? WHERE user_id = ?", (price, interaction.user.id))

    # ✅ Přidej item do inventáře (tady vložujeme kód s bought_at)
    bought_at = datetime().strftime("%Y-%m-%d %H:%M UTC")

    c.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?", (interaction.user.id, name))
    existing = c.fetchone()
    if existing:
        new_quantity = existing[0] + count
        c.execute("UPDATE inventory SET quantity = ?, bought_at = ? WHERE user_id = ? AND item_name = ?",
                  (new_quantity, bought_at, interaction.user.id, name))
    else:
        c.execute("INSERT INTO inventory (user_id, item_name, quantity, bought_at) VALUES (?, ?, ?, ?)",
                  (interaction.user.id, name, count, bought_at))

    conn.commit()

    await interaction.response.send_message(f"✅ Koupil jsi {count}× `{name}` za 💰 {price}$")



# Slash příkaz /money remove
@bot.tree.command(name="money_remove", description="Odebere hráči měnu")
async def money_remove(interaction: discord.Interaction, member: discord.Member, amount: int):
    if interaction.user.id != admin_id:
        await interaction.response.send_message("❌ Tento příkaz může používat pouze oprávněný uživatel!", ephemeral=True)
        return
    user = get_user(member.id)
    if user[1] >= amount:
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, member.id))
        conn.commit()
        await interaction.response.send_message(f"✅ Odebráno {amount} {currency_name} uživateli {member.mention}")
    else:
        await interaction.response.send_message("❌ Uživatel nemá dostatek prostředků!")



# Slash příkaz /dice 
@bot.tree.command(name="dice", description="Hraj kostky proti botovi")
async def dice(interaction: discord.Interaction, bet_amount: int):
    user = get_user(interaction.user.id)
    if user[1] < bet_amount:
        await interaction.response.send_message("❌ Nemáš dostatek peněz na tuto sázku!")
        return
    
    # Hráč hodí dvě kostky
    player_dice = [random.randint(1, 6), random.randint(1, 6)]
    
    # Bot hodí dvě kostky
    bot_dice = [random.randint(1, 6), random.randint(1, 6)]
    
    # Spočítání součtu hodnot kostek
    player_total = sum(player_dice)
    bot_total = sum(bot_dice)
    
    # Zpráva pro výsledek
    result_message = f"🎲 **Hodil jsi:** {player_dice[0]}️⃣ a {player_dice[1]}️⃣\n"
    result_message += f"🤖 **Bot hodil:** {bot_dice[0]}️⃣ a {bot_dice[1]}️⃣\n"
    
    # Určení vítěze
    if player_total >= bot_total:
        new_balance = user[1] + bet_amount
        result_message += f"🎉 **Vyhrál jsi!** Přidáno {bet_amount} {currency_name}."
    else:
        new_balance = user[1] - bet_amount
        result_message += f"💀 **Prohrál jsi!** Odečteno {bet_amount} {currency_name}."
    
    # Aktualizace zůstatku hráče
    c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, interaction.user.id))
    conn.commit()

    # Odeslání zprávy s výsledkem
    await interaction.response.send_message(result_message)


# Slash příkaz /roulette
@bot.tree.command(name="roulette", description="Zahraj si ruletu")
async def roulette(interaction: discord.Interaction, bet_number: int, bet_amount: int):
    if bet_number < 0 or bet_number > 36:
        await interaction.channel.send("❌ Neplatné číslo! Sázej na čísla 0 až 36.")
        return

    user = get_user(interaction.user.id)
    if user[1] < bet_amount:
        await interaction.channel.send("❌ Nemáš dostatek peněz na tuto sázku!")
        return

    winning_number = random.randint(0, 36)
    color = "🔴 červená" if winning_number % 2 == 0 and winning_number != 0 else "⚫ černá" if winning_number % 2 == 1 else "🟢 zelená"

    winnings = 0
    if bet_number == winning_number:
        winnings = bet_amount * 35
    elif (bet_number % 2 == winning_number % 2) and winning_number != 0:
        winnings = bet_amount * 2

    new_balance = user[1] - bet_amount + winnings
    c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, interaction.user.id))
    conn.commit()

    await interaction.channel.send(f"🎰 Ruleta se točí... Výherní číslo: **{winning_number} ({color})**\n\n{interaction.user.mention}, nyní máš **{new_balance} {currency_name}**!")


# Slash příkaz /money add
@bot.tree.command(name="money_add", description="Přidá hráči měnu")
async def money_add(interaction: discord.Interaction, member: discord.Member, amount: int):
    if interaction.user.id != admin_id:
        await interaction.response.send_message("❌ Tento příkaz může používat pouze oprávněný uživatel!", ephemeral=True)
        return
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, member.id))
    conn.commit()
    await interaction.response.send_message(f"✅ Přidáno {amount} {currency_name} uživateli {member.mention}")

# Slash příkaz /leaderboard
@bot.tree.command(name="leaderboard", description="Zobrazí top 10 nejbohatších hráčů na serveru")
async def leaderboard(interaction: discord.Interaction):
    c.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
    top_users = c.fetchall()
    
    leaderboard_message = "🏆 **Top 10 nejbohatších hráčů:**\n"
    for index, (user_id, balance) in enumerate(top_users, start=1):
        member = interaction.guild.get_member(user_id)
        username = member.display_name if member else "Uživatel neznámý"
        leaderboard_message += f"{index}. {username} - {balance} {currency_name}\n"
    
    user_data = get_user(interaction.user.id)
    c.execute("SELECT COUNT(*) FROM users WHERE balance > ?", (user_data[1],))
    rank = c.fetchone()[0] + 1
    
    leaderboard_message += f"\n🔹 **Tvé umístění:** {rank}. {interaction.user.display_name} - {user_data[1]} {currency_name}"
    
    await interaction.response.send_message(leaderboard_message)

# Slash příkaz /balance
@bot.tree.command(name="balance", description="Zobrazí zůstatek označeného člověka")
async def balance(interaction: discord.Interaction, member: discord.Member):
    c.execute("SELECT balance FROM users WHERE user_id = ?", (member.id,))
    result = c.fetchone()
    balance = result[0] if result else 0
    await interaction.response.send_message(f"💰 {member.display_name} má {balance} {currency_name}.")


# Slash příkaz /info
@bot.tree.command(name="info", description="Zobrazí informace o označeném hráči (pouze pro admina)")
async def info(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != admin_id:
        await interaction.response.send_message("❌ Tento příkaz může používat pouze oprávněný uživatel!", ephemeral=True)
        return
    
    status_mapping = {
        discord.Status.online: "🟢 Online",
        discord.Status.offline: "⚫ Offline",
        discord.Status.idle: "🌙 Nečinný",
        discord.Status.dnd: "⛔ Nerušit"
    }
    status = status_mapping.get(member.status, "Neznámý")
    
    c.execute("SELECT balance FROM users WHERE user_id = ?", (member.id,))
    balance = c.fetchone()
    balance = balance[0] if balance else 0
    
    embed = discord.Embed(title=f"Informace o uživateli {member.display_name}", color=discord.Color.blue())
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="🔹 Stav", value=status, inline=False)
    embed.add_field(name="💰 Zůstatek", value=f"{balance} {currency_name}", inline=False)
    embed.add_field(name="📅 Připojil se", value=member.joined_at.strftime('%Y-%m-%d'), inline=False)
    embed.add_field(name="🔢 ID", value=str(member.id), inline=False)
    embed.set_footer(text=f"Vyžádal: {interaction.user.display_name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
    
    await interaction.response.send_message(embed=embed)

# Slash příkaz /whatismyip
@bot.tree.command(name="whatismyip", description="Zobrazí IP adresu uživatele, který zadal příkaz")
async def whatismyip(interaction: discord.Interaction):
    response = requests.get("https://api64.ipify.org?format=json")
    ip_address = response.json().get("ip", "Neznámá IP")
    await interaction.response.send_message(f"🖥 Vaše IP adresa: `{ip_address}`", ephemeral=True)

# Bot nasloucha jestli ho nekdo @pingnul a pak vypise seznam veci ktere umi
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user in message.mentions:
        embed = discord.Embed(
            title="📘 Pomocník bota – Seznam příkazů",
            description="Zde najdeš vše, co umím. Příkazy jsou rozděleny do kategorií:",
            color=discord.Color.orange()
        )

        # 🧍 Základní příkazy
        embed.add_field(name="🔹 # ZÁKLADNÍ PŘÍKAZY", value="\u200b", inline=False)
        commands_list = {
            "leaderboard": "🏆 Zobrazí top 10 nejbohatších hráčů",
            "balance": "💰 Zobrazí zůstatek označeného člověka",
            "datum": "📅 Zobrazí aktuální datum"
        }
        for cmd, desc in commands_list.items():
            embed.add_field(name=f"`/{cmd}`", value=desc, inline=False)

        # 🎁 Ekonomika
        embed.add_field(name="🔹 # EKONOMIKA", value="\u200b", inline=False)
        economy_commands = {
            "daily": "🎁 Získáš denní odměnu",
            "weekly": "📆 Získáš týdenní odměnu",
            "money_add": "➕ Přidá hráči měnu",
            "money_remove": "❌ Odebere hráči měnu"
        }
        for cmd, desc in economy_commands.items():
            embed.add_field(name=f"`/{cmd}`", value=desc, inline=False)

        # 🎲 Minihry
        embed.add_field(name="🔹 # MINIHRY", value="\u200b", inline=False)
        game_commands = {
            "roulette": "🎰 Zahraj si ruletu",
            "dice": "🎲 Hraj kostky proti botovi"
        }
        for cmd, desc in game_commands.items():
            embed.add_field(name=f"`/{cmd}`", value=desc, inline=False)

        # 🛒 SHOP příkazy
        embed.add_field(name="🔹 # SHOP PŘÍKAZY", value="\u200b", inline=False)
        shop_commands = {
            "item_suggest": "📝 Navrhni nový předmět do shopu",
            "item_accept": "✅ Schválit navržený předmět",
            "item_buy": "🛍️ Koupit předmět z obchodu"
        }
        for cmd, desc in shop_commands.items():
            embed.add_field(name=f"`/{cmd}`", value=desc, inline=False)

        # ⚙️ Admin příkazy
        if message.author.id == admin_id:
            embed.add_field(name="🔹 # ADMIN PŘÍKAZY", value="\u200b", inline=False)
            admin_commands = {
                "restart": "🔄 Restartuje bota",
                "stop": "🛑 Vypne bota",
                "stats": "📊 Zobrazí stav bota"
            }
            for cmd, desc in admin_commands.items():
                embed.add_field(name=f"`/{cmd}`", value=desc, inline=False)

        # Footer
        embed.set_footer(
            text=f"Používáno uživatelem: {message.author.display_name}",
            icon_url=message.author.avatar.url if message.author.avatar else None
        )

        await message.channel.send(embed=embed)

    await bot.process_commands(message)




# Slash příkaz /stats (jen pro administrátory)
@bot.tree.command(name="stats", description="Zobrazí stav bota")
async def stats(interaction: discord.Interaction):
    if interaction.user.id != admin_id:
        await interaction.response.send_message("❌ Tento příkaz může používat pouze oprávněný uživatel!", ephemeral=True)
        return

    process = psutil.Process(os.getpid())
    ram_usage = process.memory_info().rss / (1024 * 1024)  # MB
    total_ram = psutil.virtual_memory().total / (1024 * 1024)  # MB
    disk_usage = process.memory_info().vms / (1024 * 1024)  # MB
    uptime = datetime.datetime.now() - test_start_time
    latency = round(bot.latency * 1000, 2)
    server_count = len(bot.guilds)
    
    stats_message = (
        f"🖥 **Statistiky bota**\n"
        f"🔹 RAM: {ram_usage:.2f} MB / {total_ram:.2f} MB\n"
        f"💾 SSD: {disk_usage:.2f} MB\n"
        f"⏳ Poslední spuštění: {test_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"📶 Ping: {latency} ms\n"
        f"📊 Počet serverů: {server_count}"
    )
    await interaction.response.send_message(stats_message)

# Slash příkaz /stop
@bot.tree.command(name="stop", description="Vypne bota")
async def stop(interaction: discord.Interaction):
    if interaction.user.id != admin_id:
        await interaction.response.send_message("❌ Tento příkaz může používat pouze oprávněný uživatel!", ephemeral=True)
        return
    await interaction.response.send_message("🛑 Bot se vypíná...")
    await bot.close()

# Slash příkaz /restart
@bot.tree.command(name="restart", description="Restartuje bota")
async def restart(interaction: discord.Interaction):
    if interaction.user.id != admin_id:
        await interaction.response.send_message("❌ Tento příkaz může používat pouze oprávněný uživatel!", ephemeral=True)
        return
    await interaction.response.send_message("🔄 Bot se restartuje...")
    os.execv(sys.executable, ['python'] + sys.argv)


# Slash příkaz /daily
@bot.tree.command(name="daily", description="Získat 200 {currency_name} jednou denně")
async def daily(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    last_daily = user[2]
    today = datetime.datetime.now().date()

    if last_daily is None or datetime.datetime.strptime(last_daily, "%Y-%m-%d").date() < today:
        c.execute("UPDATE users SET balance = balance + 200, last_daily = ? WHERE user_id = ?", (today, interaction.user.id))
        conn.commit()
        await interaction.response.send_message(f"✅ Získal(a) jsi 200 {currency_name}!")
    else:
        await interaction.response.send_message("❌ Už jsi dneska použil(a) /daily. Můžeš to zkusit zítra!")

# Slash příkaz /weekly
@bot.tree.command(name="weekly", description="Získat 1000 {currency_name} jednou týdně")
async def weekly(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    last_weekly = user[3]
    today = datetime.datetime.now().date()

    if last_weekly is None or datetime.datetime.strptime(last_weekly, "%Y-%m-%d").date() < today - datetime.timedelta(weeks=1):
        c.execute("UPDATE users SET balance = balance + 1000, last_weekly = ? WHERE user_id = ?", (today, interaction.user.id))
        conn.commit()
        await interaction.response.send_message(f"✅ Získal(a) jsi 1000 {currency_name}!")
    else:
        await interaction.response.send_message("❌ Už jsi tento týden použil(a) /weekly. Můžeš to zkusit příští týden!")


# Spuštění bota
# bot.run('ZDE VLOZTE ID BOTA A ODKOMENTUJTE TENTO RADEK')


# MOJE ID NA DISCORDU: 931226652552343552