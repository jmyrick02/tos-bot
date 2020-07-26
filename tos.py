import discord, datetime, asyncio, gspread
from discord.ext import tasks, commands
from oauth2client.service_account import ServiceAccountCredentials
from enum import Enum
 
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
sheets_client = gspread.authorize(creds) 
with open('sheet.txt') as file:
    sheet = sheets_client.open(file.read()).sheet1

with open('prefix.txt') as file:
    bot = commands.Bot(command_prefix=file.read())

games = {}

@tasks.loop(seconds=60)
async def update():
    time = datetime.datetime.utcnow()

    for guild_id in games:
        game = games[guild_id]
        if (game.automatic_time and game.in_progress and ((time.hour == game.transition_times[0][0] and time.minute == game.transition_times[0][1]) or (time.hour == game.transition_times[1][0] and time.minute == game.transition_times[1][1]))):
            await game.progress_time()

class SalemRole(Enum):
    INVESTIGATOR = 0
    LOOKOUT = 1
    PSYCHIC = 2
    SHERIFF = 3
    SPY = 4
    TRACKER = 5
    BODYGUARD = 6
    CRUSADER = 7
    DOCTOR = 8
    ESCORT = 9
    MAYOR = 10
    MEDIUM = 11
    TRANSPORTER = 12
    JAILOR = 13
    VETERAN = 14
    VIGILANTE = 15
    AMBUSHER = 16
    GODFATHER = 17
    MAFIOSO = 18
    BLACKMAILER = 19
    CONSIGLIERE = 20
    CONSORT = 21
    FRAMER = 22
    HYPNOTIST = 23
    JANITOR = 24
    EXECUTIONER = 25
    JESTER = 26
    WITCH = 27
    AMNESIAC = 28
    GUARDIAN_ANGEL = 29
    SURVIVOR = 30
    ARSONIST = 31
    JUGGERNAUT = 32
    PIRATE = 33
    SERIAL_KILLER = 34
    WEREWOLF = 35
    VAMPIRE_HUNTER = 36
    TRAPPER = 37
    RETRIBUTIONIST = 38
    DISGUISER = 39
    FORGER = 40
    PLAGUEBEARER = 41
    PESTILENCE = 42
    VAMPIRE = 43
    COVEN_LEADER = 44
    HEX_MASTER = 45
    MEDUSA = 46
    NECROMANCER = 47
    POISONER = 48
    POTION_MASTER = 49
    CUSTOM = 50
ROLES_WITH_TARGETS = [SalemRole.EXECUTIONER, SalemRole.GUARDIAN_ANGEL]

class Player:
    def __init__(self, user_id, personal_channel_id, role, role_display_name):
        self.user_id = user_id
        self.personal_channel_id = personal_channel_id
        self.role = role
        self.role_display_name = role_display_name
        self.apparent_role = role
        self.votable = True
        self.nomination = 0
        self.vote = 0 # 0 = abstain, 1 = inno, 2 = guilty
        self.alive = True
        self.doused = False
        self.infected = False
        self.fused = False
        self.jailed = False
        self.open_states = [None, None, None, None]       

class Game:
    def __init__(self, bot, guild_id, in_progress, game_channel_id, death_channel_id, voting_channel_id, jail_channel_id, player_role_id, dead_player_role_id, transition_times, players):
        self.day = .5  # 1 = day 1, 1.5 = night 1 etc.
        self.bot = bot
        self.game_channel_id = game_channel_id
        self.death_channel_id = death_channel_id
        self.voting_channel_id = voting_channel_id
        self.jail_channel_id = jail_channel_id
        self.evil_channel_ids = []
        self.guild_id = guild_id
        self.player_role_id = player_role_id
        self.dead_player_role_id = dead_player_role_id
        self.transition_times = transition_times
        self.players = sorted(players, key=lambda player: player.user_id)
        self.in_progress = in_progress
        self.automatic_time = True
        self.remaining_trials = 3
        self.current_voting_message_id = 0

    async def progress_time(self):
        self.day += 0.5
        if int(self.day) == self.day:  # day time
            message = await self.bot.get_channel(self.game_channel_id).send(f'**DAY {int(self.day)}**')
            await self.bot.get_channel(self.game_channel_id).set_permissions(self.bot.get_guild(self.guild_id).get_role(self.player_role_id), send_messages=True)
            self.remaining_trials = 3

            for jailor in self.players_from_role(SalemRole.JAILOR):
                if jailor.open_states[0] != 'None':
                    jailed_member = self.bot.get_guild(self.guild_id).get_member(int(jailor.open_states[0]))
                    jailed_player = self.player_from_id(int(jailor.open_states[0]))
                    jailed_player.jailed = False
                    jailor.open_states[0] = 'None'
                    save(self.guild_id)
                
                    jailed_channel = bot.get_channel(self.jail_channel_id)
                    await jailed_channel.set_permissions(jailed_member, read_messages=False, send_messages=False, manage_messages=False, read_message_history=False)

                    while True:
                        messages = await jailed_channel.history(limit=100).flatten()
                        if len(messages) == 0:
                            break

                        await jailed_channel.delete_messages(messages)
        else:
            await self.bot.get_channel(self.game_channel_id).set_permissions(self.bot.get_guild(self.guild_id).get_role(self.player_role_id), send_messages=False)
            message = await self.bot.get_channel(self.game_channel_id).send(f'**NIGHT {int(self.day)}**')
            if (self.day - 0.5) % 2 == 0:
                await self.bot.get_channel(self.game_channel_id).send(f'**There is a full moon out tonight.**')
                for werewolf in self.players_from_role(SalemRole.WEREWOLF):
                    if werewolf.alive:
                        await self.bot.get_channel(werewolf.personal_channel_id).send('**There is a full moon out tonight. Remember to use your role!**')
            await self.bot.get_channel(self.game_channel_id).send(f'{self.bot.get_guild(self.guild_id).get_role(self.player_role_id).mention} Remember to use your roles tonight and don\'t forget to have your will pinned.')

            for jailor in self.players_from_role(SalemRole.JAILOR):
                if jailor.open_states[0] != 'None':
                    jailed_member = self.bot.get_guild(self.guild_id).get_member(int(jailor.open_states[0]))
                    jailed_player = self.player_from_id(int(jailor.open_states[0]))
                    jailed_player.jailed = True
                    save(self.guild_id)
                
                    jailed_channel = bot.get_channel(self.jail_channel_id)
                    await jailed_channel.set_permissions(jailed_member, read_messages=True, send_messages=True, manage_messages=True, read_message_history=True)
                    await jailed_channel.send(jailed_member.mention + "**You have been jailed**\nAny messages sent here will be relayed to the jailor. Messages from the jailor will be relayed to you through this bot to preserve the jailor's secrecy of identity.")
        await message.pin()

        save(self.guild_id)

    def player_from_id(self, user_id):
        for player in self.players:
            if user_id == player.user_id:
                return player

    def players_from_role(self, role):
        return [player for player in self.players if player.role == role]
    
    def get_votable_players(self):
        return [player for player in self.players if player.alive and player.votable]

@bot.event
async def on_ready():
    print('Logged on as', bot.user)

    update.start()
    for guild in bot.guilds:
        load(guild.id)

@bot.event
async def on_message(message):
    if message.guild.id in games:
        game = games[message.guild.id]

        if message.channel.id == game.jail_channel_id and message.author.id != bot.user.id:
            for jailor in game.players_from_role(SalemRole.JAILOR):
                personal_channel = bot.get_channel(jailor.personal_channel_id)

                await personal_channel.send('**Your prisoner says** ' + message.content)
    
    await bot.process_commands(message)

@bot.event
async def on_raw_reaction_add(payload): # TODO on reaction add, delete all other reactions on the message by that user
    if payload.guild_id in games:
        game = games[payload.guild_id]
        message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        try:
            official_message = await bot.get_channel(game.voting_channel_id).fetch_message(game.current_voting_message_id)
        except:
            return

        if message.content == official_message.content:
            player = game.player_from_id(payload.user_id)
            if not player:
                if bot.get_user(payload.user_id) != bot.user:
                    await message.remove_reaction(payload.emoji, payload.member)
                return
            player_number = ord(payload.emoji.name) - ord('🇦')

            if player.alive:
                nomination = game.get_votable_players()[player_number]
                if nomination != player:
                    for i in range(0, len(game.get_votable_players())):
                        if i != player_number:
                            await message.remove_reaction(chr(ord('🇦') + i), payload.member)

                    player.nomination = game.get_votable_players()[player_number].user_id
                    save(message.guild.id)
                else:
                    await message.remove_reaction(payload.emoji, payload.member)
                    return
            else:
                await message.remove_reaction(payload.emoji, payload.member)
            
@bot.event
async def on_raw_reaction_remove(payload):
    if payload.guild_id in games:
        game = games[payload.guild_id]
        message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        try:
            official_message = await bot.get_channel(game.voting_channel_id).fetch_message(game.current_voting_message_id)
        except:
            return

        if message.content == official_message.content:
            player = game.player_from_id(payload.user_id)
            if not player:
                return

            if message.channel == bot.get_channel(game.voting_channel_id) and message.author == bot.user:
                if player.alive:
                    nomination = 0
                    player.nomination = nomination
                    save(message.guild.id)

@bot.command(brief='Sets up a game instance', aliases=['setup'])
@commands.has_permissions(administrator=True)
async def setup_game(ctx):
    def check_if_reply(message):
        return message.channel == ctx.channel and message.author == ctx.message.author

    if not ctx.guild.id in games:
        guild_id = ctx.guild.id
        
        await ctx.send('Mention the main game channel (ex. #game):')
        reply = await bot.wait_for('message', check=check_if_reply)
        game_channel_id = reply.channel_mentions[0].id

        await ctx.send('Mention the channel that deaths will be announced in (ex. #deaths):')
        reply = await bot.wait_for('message', check=check_if_reply)
        death_channel_id = reply.channel_mentions[0].id

        await ctx.send('Mention the voting channel (ex. #voting):')
        reply = await bot.wait_for('message', check=check_if_reply)
        voting_channel_id = reply.channel_mentions[0].id

        await ctx.send('Mention the jail channel (ex. #jail):')
        reply = await bot.wait_for('message', check=check_if_reply)
        jail_channel_id = reply.channel_mentions[0].id

        """await ctx.send('Mention the mafia channel(s) (ex. #mafia *or* #mafia #coven):')
        reply = await bot.wait_for('message', check=check_if_reply)
        evil_channel_ids = map(lambda channel: channel.id, reply.channel_mentions)"""

        await ctx.send('Mention the player role for use while alive (ex. @Player):')
        reply = await bot.wait_for('message', check=check_if_reply)
        player_role_id = reply.role_mentions[0].id

        await ctx.send('Mention the player role for use while dead (ex. @Dead)')
        reply = await bot.wait_for('message', check=check_if_reply)
        dead_player_role_id = reply.role_mentions[0].id

        await ctx.send('Enter the hour in UTC for the first transition time (ex. 0):')
        reply = await bot.wait_for('message', check=check_if_reply)
        hour1 = reply.content

        await ctx.send('Enter the minute in UTC for the first transition time (ex. 0):')
        reply = await bot.wait_for('message', check=check_if_reply)
        minute1 = reply.content

        await ctx.send('Enter the hour in UTC for the second transition time (ex. 12):')
        reply = await bot.wait_for('message', check=check_if_reply)
        hour2 = reply.content

        await ctx.send('Enter the minute in UTC for the second transition time (ex. 45):')
        reply = await bot.wait_for('message', check=check_if_reply)
        minute2 = reply.content

        transition_times = [(hour1, minute1), (hour2, minute2)]

        games[guild_id] = Game(bot, guild_id, False, game_channel_id, death_channel_id, voting_channel_id, jail_channel_id, player_role_id, dead_player_role_id, transition_times, [])
        save(guild_id)

        await ctx.send('The game instance is set up. Use the command "delete_game" to delete this game instance and to be able to restart. Finish set up using the command "add_players" in an admin channel. Use the command "game_info" to review info about this instance. Use the command "start_game" to begin this instance.')
    else:
        await ctx.send('A game instance already exists. Delete this instance with the command "delete_game" to be able to create a new one.')

@bot.command(brief='Adds multiple players and their associated info to the the game instance.', description='List of roles (ignore the numbers): https://drive.google.com/file/d/1u-WXqlYEe6hYk8PB3lO6oqk0sPhzXeAc/view?usp=sharing')
@commands.has_permissions(administrator=True)
async def add_players(ctx):
    def check_if_reply(message):
        return message.channel == ctx.channel and message.author == ctx.message.author
    
    def check_if_reaction(reaction, user):
        return user == ctx.message.author and reaction.message.channel == ctx.channel

    game = games[ctx.guild.id]

    adding_players = True
    while adding_players:
        await ctx.send('Enter the player name to be added (ex. Jamster):')
        reply = await bot.wait_for('message', check=check_if_reply)
        member = member_from_string(ctx, reply.content)
        if not member:
            await ctx.send('There are multiple/zero matches for the entered nickname. Please redo this command with their full discord name.')
    
        await ctx.send('Mention the personal channel they will use (ex. #pork):')
        reply = await bot.wait_for('message', check=check_if_reply)
        personal_channel = reply.channel_mentions[0]

        await ctx.send('Enter their role. Valid roles are found here: https://drive.google.com/file/d/1u-WXqlYEe6hYk8PB3lO6oqk0sPhzXeAc/view?usp=sharing')
        reply = await bot.wait_for('message', check=check_if_reply)
        role = SalemRole[reply.content.upper()]

        if role in ROLES_WITH_TARGETS:
            await ctx.send("Enter their target's name:")
            reply = await bot.wait_for('message', check=check_if_reply)
            member2 = member_from_string(ctx, reply.content)
            if not member2:
                await ctx.send('There are multiple/zero matches for the entered nickname. Please redo this command with their full discord name.')

        await ctx.send("Enter the role's display name: ")
        reply = await bot.wait_for('message', check=check_if_reply)
        role_display_name = reply.content

        player = Player(member.id, personal_channel.id, role, role_display_name)
        if role in ROLES_WITH_TARGETS:
            player.open_states[0] = str(member2.id)
        game.players.append(player)
        save(ctx.guild.id)

        await member.add_roles(ctx.guild.get_role(game.player_role_id))
        await personal_channel.set_permissions(member, read_messages=True, send_messages=True, manage_messages=True, read_message_history=True)
        await personal_channel.send(member.mention)
        embed = discord.Embed(title='Welcome!', description='This is your own private channel. This is where you are told what your role is, and where you tell the host how you use it as well. On top of that, this is where you store your will. **You must have the will pinned** (it must be the most recent pinned message), or it will not go through, in the case that you die. You have been given pin perms for this channel.', color=discord.Color.dark_green())
        embed.add_field(name='Game Schedule', value=f'The game will transition between day and night at **{time_tuple_to_string(game.transition_times[0])}** and **{time_tuple_to_string(game.transition_times[1])}**')
        await personal_channel.send(embed=embed)

        prompt = await ctx.send('Add another player? 👍 / 👎')
        await prompt.add_reaction('👍')
        await prompt.add_reaction('👎')
        reaction = (await bot.wait_for('reaction_add', check=check_if_reaction))[0]
        adding_players = True if reaction.emoji == '👍' else False
    await ctx.send('Adding players is finished. If you would like to start the game, use the command "start_game". If you would like to review game info, use the command "game_info"')

@bot.command(brief='Removes players from the game instance.')
@commands.has_permissions(administrator=True)
async def remove_players(ctx):
    def check_if_reply(message):
        return message.channel == ctx.channel and message.author == ctx.message.author

    prompt = None
    def check_if_reaction(reaction, user):
        return user == ctx.message.author and reaction.message.channel == ctx.channel

    game = games[ctx.guild.id]

    killing = True
    while killing:
        await ctx.send('Enter the name of the player to be killed:')
        reply = await bot.wait_for('message', check=check_if_reply)
        member = member_from_string(ctx, reply.content)
        if not member:
            await ctx.send('There are multiple/zero matches for the entered nickname. Please redo this command with their full discord name.')
        player = game.player_from_id(member.id)
        player.alive = False
        await member.remove_roles(ctx.guild.get_role(game.player_role_id))
        await member.add_roles(ctx.guild.get_role(game.dead_player_role_id))
        save(ctx.guild.id)

        prompt = await ctx.send('Would you like the bot to automatically post the death to the deaths channel? 👍 / 👎')
        await prompt.add_reaction('👍')
        await prompt.add_reaction('👎')
        reaction = (await bot.wait_for('reaction_add', check=check_if_reaction))[0]
        automatic = True if reaction.emoji == '👍' else False
        if automatic:
            await ctx.send('Enter the death reason:')
            reply = await bot.wait_for('message', check=check_if_reply)

            embed = discord.Embed(title=f'{ctx.guild.get_member(player.user_id).display_name} was found dead', description=reply.content, color=discord.Color.dark_red())

            pins = await bot.get_channel(player.personal_channel_id).pins()
            if len(pins) == 0:
                embed.add_field(name='Will', value='We found no last will.', inline=False)
            else:
                embed.add_field(name='Will', value=f'```{pins[0].content[:1018]}```', inline=False)
            embed.add_field(name='Role', value=player.role_display_name, inline=False)
        
            await bot.get_channel(game.death_channel_id).send(embed=embed)
    
        prompt = await ctx.send('Kill another player? 👍 / 👎')
        await prompt.add_reaction('👍')
        await prompt.add_reaction('👎')
        reaction = (await bot.wait_for('reaction_add', check=check_if_reaction))[0]
        killing = True if reaction.emoji == '👍' else False
    await ctx.send('Killing is finished. If you would like to begin voting, use the command "begin_voting".')

@bot.command(brief='Sets up voting')
@commands.has_permissions(administrator=True)
async def begin_voting(ctx):
    game = games[ctx.guild.id]

    embed = discord.Embed(title='Voting', description=f'There are {game.remaining_trials} possible trials remaining today.\nReact to vote up a player.', color=discord.Color.dark_red())
    player_list = ''
    i = 0
    for player in sorted(game.get_votable_players(), key=lambda player: player.user_id):
            player_list += ':regional_indicator_' + chr(i + 97) + ': ' + ctx.guild.get_member(player.user_id).display_name + '\n'
            i += 1
    embed.add_field(name='Players', value=player_list, inline=False)
    voting = await bot.get_channel(game.voting_channel_id).send(embed=embed)
    for num in range(0, i):
        await voting.add_reaction(chr(ord('🇦') + num))
    game.current_voting_message_id = voting.id
    save(ctx.guild.id)

@bot.command(brief='Starts the game instance')
@commands.has_permissions(administrator=True)
async def start_game(ctx):
    games[ctx.guild.id].in_progress = True
    await bot.get_channel(games[ctx.guild.id].game_channel_id).send('**-------------------------------------------------------------------------------------------------------------------------**')
    await games[ctx.guild.id].progress_time()

    await bot.get_channel(games[ctx.guild.id].game_channel_id).set_permissions(ctx.guild.get_role(games[ctx.guild.id].player_role_id), read_messages=True, read_message_history=True)

    for player in games[ctx.guild.id].players:
        await bot.get_channel(player.personal_channel_id).send(ctx.guild.get_member(player.user_id).mention)
        embed = discord.Embed(title='Game Info', description=f'The game has begun in {bot.get_channel(games[ctx.guild.id].game_channel_id).mention}', color=discord.Color.green())
        embed.add_field(name='Role', value=f'You are the **{player.role_display_name}**', inline=False)
        if player.role in ROLES_WITH_TARGETS:
            try:
                embed.add_field(name='Target', value=f'Your target is **{ctx.guild.get_member(int(player.open_states[0])).display_name}**', inline=False)
            except:
                pass
        embed.add_field(name='How to Play', value="This game is run primarily by the amazing hosts. Tell the hosts what you will be doing to use your role's abilities. If you have any specific questions, feel free to ask the hosts.", inline=False)
        embed.add_field(name=f'{bot.command_prefix}whisper <nick> <message>', value="This command, used in your personal channel, is used for whispering. It will send your message to the recipient's personal channel and announce who you whispered to in the main game chat. You and your recipient must be alive and it must be day but not the first day. If the recipient's name has a space in it, surround the name in quotes.", inline=False)
        embed.add_field(name=f'{bot.command_prefix}time', value="This command gives the current time in UTC.", inline=False)
        embed.add_field(name=f'{bot.command_prefix}list_players', value="This command gives a list of currently alive players in the game.", inline=False)
        if player.role == SalemRole.MAYOR:
            embed.add_field(name=f'{bot.command_prefix}reveal', value="This command reveals to town that you are mayor but prevents whispering to or from you. You also get 3 votes when revealed.", inline=False)
        if player.role == SalemRole.JAILOR:
            embed.add_field(name=f'{bot.command_prefix}jail <player>', value="This command sets a player to be jailed come night. Must be used during the day.", inline=False)
            embed.add_field(name=f'{bot.command_prefix}send_jail (message)', value="This command sends a message to the jail to preserve your anonymity.", inline=False)
        await bot.get_channel(player.personal_channel_id).send(embed=embed)

@bot.command(aliases=['utc'], brief='Gives the current time in UTC')
async def time(ctx):
    await ctx.send(f'The time is {str(datetime.datetime.utcnow().time())[:5]} UTC')

@bot.command(brief='Changes the transition times for the game instance')
@commands.has_permissions(administrator=True)
async def set_transition_times(ctx, hour1, minute1, hour2, minute2):
    games[ctx.guild.id].transition_times = [(int(hour1), int(minute1)), (int(hour2), int(minute2))]
    save(ctx.guild.id)
    await ctx.message.add_reaction('✅')

@bot.command(brief='Sets a players role to a new role')
@commands.has_permissions(administrator=True)
async def set_role(ctx, nick, role, role_display_name):
    def check_if_reply(message):
        return message.channel == ctx.channel and message.author == ctx.message.author
    
    game = games[ctx.guild.id]

    member = member_from_string(ctx, nick)
    if not member:
        await ctx.send('There are multiple matches for the entered nickname. Please redo this command with their full discord name or id.')

    player = game.player_from_id(member.id)
    player.role = SalemRole[role]
    player.role_display_name = role_display_name

    await bot.get_channel(player.personal_channel_id).send(f'{member.mention} Your role has been changed to {player.role_display_name}')

    if SalemRole[role] in ROLES_WITH_TARGETS:
        await ctx.send("Enter their target's name:")
        reply = await bot.wait_for('message', check=check_if_reply)
        member2 = member_from_string(ctx, reply.content)
        if not member2:
            await ctx.send('There are multiple/zero matches for the entered nickname. Please redo this command with their full discord name.')
        
        player.open_states[0] = str(member2.id)
        await bot.get_channel(player.personal_channel_id).send('Your target is ' + member2.display_name)

    save(ctx.guild.id)

    await ctx.message.add_reaction('✅')

@bot.command(aliases=['w', 'message', 'msg', 'pm', 'dm'], brief='Whispers to a player in the game and tells everyone in the game')
async def whisper(ctx, nick, *, message):
    recipient = discord.utils.get(ctx.guild.members, display_name=nick)

    recipient = member_from_string(ctx, nick)
    if not recipient:
        await ctx.send('There are no/multiple matches for the entered nickname. Please redo this command with their full discord name or id.')

    if ctx.guild.id in games and games[ctx.guild.id].day == int(games[ctx.guild.id].day) and recipient != ctx.author and games[ctx.guild.id].day >= 2 and games[ctx.guild.id].player_from_id(ctx.author.id).alive and games[ctx.guild.id].player_from_id(recipient.id).alive:
        game = games[ctx.guild.id]
        if (game.player_from_id(ctx.author.id).role == SalemRole.MAYOR and game.player_from_id(ctx.author.id).open_states[0] == "True") or (game.player_from_id(recipient.id).role == SalemRole.MAYOR and game.player_from_id(recipient.id).open_states[0] == "True"):
            return

        await bot.get_channel(games[ctx.guild.id].player_from_id(recipient.id).personal_channel_id).send(f'**{ctx.author.display_name}** whispers *{message}*')
        await bot.get_channel(games[ctx.guild.id].game_channel_id).send(f'**{ctx.author.display_name}** is whispering to **{recipient.display_name}**')

        for blackmailer in games[ctx.guild.id].players_from_role(SalemRole.BLACKMAILER):
            embed = discord.Embed(title=f'{ctx.author.display_name} is whispering to {recipient.display_name}', description=message, color=discord.Color.light_grey())
            await bot.get_channel(blackmailer.personal_channel_id).send(embed=embed)

        await ctx.message.add_reaction('✅')
    else:
        await ctx.send('This whisper is invalid. To whisper, you and your recipient must be alive in the game and it must be day time but not the first day. You also cannot whisper to yourself.')

@bot.command(aliases=['player_list', 'players_list', 'plist'], brief='Lists all players in the game.')
async def list_players(ctx):
    game = games[ctx.guild.id]

    player_list = ''
    for player in sorted(game.players, key=lambda player: player.user_id):
        if player.alive:
            try:
                player_list += f'{ctx.guild.get_member(player.user_id).mention}\n'
            except:
                pass

    embed = discord.Embed(title='Alive Players', description=player_list, color=discord.Color.light_grey())
    await ctx.send(embed=embed)

@bot.command(aliases=['ginfo', 'game_data', 'gdata', 'data'], brief='Lists info about the game')
@commands.has_permissions(administrator=True)
async def game_info(ctx):
    if ctx.guild.id in games:
        game = games[ctx.guild.id]
        
        embed = discord.Embed(title='Game Information', description='This game is currently in progress.' if game.in_progress else 'This game is not currently in progress.', color=discord.Color.light_grey())
        embed.add_field(name='Current Day', value=game.day)
        embed.add_field(name='Automatic Time Transition', value=str(game.automatic_time))
        embed.add_field(name='Transition Times', value=f'{time_tuple_to_string(game.transition_times[0])} and {time_tuple_to_string(game.transition_times[1])}')
        embed.add_field(name='Alive Player Role', value=ctx.guild.get_role(game.player_role_id).mention)
        embed.add_field(name='Dead Player Role', value=ctx.guild.get_role(game.dead_player_role_id).mention)
        embed.add_field(name='Game Channel', value=bot.get_channel(game.game_channel_id).mention)
        embed.add_field(name='Dead Channel', value=bot.get_channel(game.death_channel_id).mention)
        embed.add_field(name='Voting Channel', value=bot.get_channel(game.voting_channel_id).mention)
        embed.add_field(name='Game Channel', value=bot.get_channel(game.jail_channel_id).mention)
        
        alive_player_list = 'Alive:\n'
        dead_player_list = 'Dead:\n'
        for player in sorted(game.players, key=lambda player: player.user_id):
            try:
                target_string = f'<{ctx.guild.get_member(int(player.open_states[0])).display_name}>' if player.role in ROLES_WITH_TARGETS else ''
                string = f'{ctx.guild.get_member(player.user_id).mention} - {player.role_display_name} ({player.role.name}) {target_string} {bot.get_channel(player.personal_channel_id).mention}\n'

                if player.alive:
                    alive_player_list += string
                else:
                    dead_player_list += string
            except:
                continue
        embed.add_field(name='Alive Players', value=alive_player_list, inline=False)
        embed.add_field(name='Dead Players', value=dead_player_list, inline=False)

        await ctx.send(embed=embed)
    else:
        await ctx.send('There is no game instance. Use the command "setup_game" to create one.')

def save(guild_id):
    game = games[guild_id]

    evil_channel_ids_string = ''
    for evil_channel_id in game.evil_channel_ids:
        evil_channel_ids_string += str(evil_channel_id) + ' '

    data = [str(guild_id), str(game.in_progress), str(game.game_channel_id), str(game.death_channel_id), str(game.voting_channel_id), str(game.jail_channel_id), evil_channel_ids_string, str(game.player_role_id), str(game.dead_player_role_id), str(game.transition_times[0][0]), str(game.transition_times[0][1]), str(game.transition_times[1][0]), str(game.transition_times[1][1]), str(game.day), str(game.automatic_time), str(game.remaining_trials), str(game.current_voting_message_id)]

    for player in game.players:
        data.append(str(player.user_id))
        data.append(str(player.personal_channel_id))
        data.append(str(player.role.name))
        data.append(str(player.role_display_name))
        data.append(str(player.apparent_role.name))
        data.append(str(player.votable))
        data.append(str(player.nomination))
        data.append(str(player.vote))
        data.append(str(player.alive))
        data.append(str(player.doused))
        data.append(str(player.infected))
        data.append(str(player.fused))
        data.append(str(player.jailed))
        for state in player.open_states:
            data.append(str(state))

    guild_ids = sheet.col_values(1)
    row = len(guild_ids) + 1
    if str(guild_id) in guild_ids:
        row = guild_ids.index(str(guild_id)) + 1
        sheet.delete_rows(row)

    sheet.insert_row(data, row)

def load(guild_id):
    data = sheet.col_values(1)

    guild_ids = sheet.col_values(1)
    try:
        row = guild_ids.index(str(guild_id)) + 1
        data = sheet.row_values(row)

        in_progress = bool(data[1])
        game_channel_id = int(data[2])
        death_channel_id = int(data[3])
        voting_channel_id = int(data[4])
        jail_channel_id = int(data[5])
        # evil_channel_ids_string = data[6]
        player_role_id = int(data[7])
        dead_player_role_id = int(data[8])
        transition_times = [(int(data[9]), int(data[10])), (int(data[11]), int(data[12]))]
        day = float(data[13])
        automatic_time = bool(data[14])
        remaining_trials = int(data[15])
        current_voting_message_id = int(data[16])

        players = []
        for i in range(17, len(data) - 1, 17):
            user_id = int(data[i])
            personal_channel_id = int(data[i + 1])
            role_name = data[i + 2]
            role_display_name = data[i + 3]
            apparent_role_name = data[i + 4]
            votable = bool(data[i + 5])
            nomination = int(data[i + 6])
            vote = int(data[i + 7])
            alive = bool(data[i + 8])
            doused = bool(data[i + 9])
            infected = bool(data[i + 10])
            fused = bool(data[i + 11])
            jailed = bool(data[i + 12])
            open_states = [data[i + 13], data[i + 14], data[i + 15], data[i + 16]]

            player = Player(user_id, personal_channel_id, SalemRole[role_name], role_display_name)
            player.apparent_role = SalemRole[apparent_role_name]
            player.votable = votable
            player.nomination = nomination
            player.vote = vote
            player.alive = alive
            player.doused = doused
            player.infected = infected
            player.fused = fused
            player.jailed = jailed
            player.open_states = open_states
            players.append(player)

        games[guild_id] = Game(bot, guild_id, in_progress, game_channel_id, death_channel_id, voting_channel_id, jail_channel_id, player_role_id, dead_player_role_id, transition_times, players)
        games[guild_id].day = day
        games[guild_id].automatic_time = automatic_time
        games[guild_id].remaining_trials = remaining_trials
        games[guild_id].current_voting_message_id = current_voting_message_id
        print('Loaded game of guild_id:', guild_id)
    except:
        print(f'Data for {guild_id} does not exist. Game instance not created.')

def time_tuple_to_string(time_tuple):
    def zeroify(num):
        if len(str(num)) == 1:
            return f'0{str(num)}'
        else:
            return str(num)

    return f'{zeroify(time_tuple[0])}:{zeroify(time_tuple[1])} UTC'

def member_from_string(ctx, string):
    members = [member for member in ctx.guild.members if string == member.display_name or string == str(member.id) or string == member.name or string == str(member)]
    if len(members) == 1:
        return members[0]
    else:
        return None

@bot.command(brief='Progress time manually. Only use if necessary.')
@commands.has_permissions(administrator=True)
async def progress_time(ctx):
    if ctx.guild.id in games:
        await games[ctx.guild.id].progress_time()
        await ctx.message.add_reaction('✅')
    else:
        await ctx.send('There is no game instance. Use the command "setup_game" to create one.')

@bot.command(brief='Disables/enables automatic progression of time.')
@commands.has_permissions(administrator=True)
async def toggle_time(ctx):
    if ctx.guild.id in games:
        game = games[ctx.guild.id]

        game.automatic_time = not game.automatic_time
        save(ctx.guild.id)
        await ctx.send(f'Automatic progression of time is now set to {game.automatic_time}')
    else:
        await ctx.send('There is no game instance. Use the command "setup_game" to create one.')

@bot.command(brief='Deletes the current game instance.')
@commands.has_permissions(administrator=True)
async def delete_game(ctx):
    if ctx.guild.id in games:
        game = games[ctx.guild.id]

        try:
            pinned_messages = await bot.get_channel(game.game_channel_id).pins()
            for pin in pinned_messages:
                if pin.author == bot.user:
                    await pin.unpin()
        except:
            pass

        for player in game.players:
            try:
                pinned_messages = await bot.get_channel(player.personal_channel_id).pins()
                for pin in pinned_messages:
                    await pin.unpin()

                await bot.get_channel(game.game_channel_id).set_permissions(ctx.guild.get_member(player.user_id), send_messages=False)
                await ctx.guild.get_member(player.user_id).remove_roles(ctx.guild.get_role(game.player_role_id), ctx.guild.get_role(game.dead_player_role_id))
            except:
                continue

        del games[ctx.guild.id]

        guild_ids = sheet.col_values(1)
        row = guild_ids.index(str(ctx.guild.id)) + 1
        sheet.delete_rows(row)

        await ctx.message.add_reaction('✅')
    else:
        await ctx.send('There is no game instance. Use the command "setup_game" to create one.')

@bot.command(brief='Reveals as mayor')
@commands.check(lambda ctx: ctx.guild.id in games and games[ctx.guild.id].in_progress and games[ctx.guild.id].player_from_id(ctx.author.id).role == SalemRole.MAYOR and games[ctx.guild.id].player_from_id(ctx.author.id).open_states[0] != "True")
async def reveal(ctx):
    game = games[ctx.guild.id]
    player = game.player_from_id(ctx.author.id)
        
    player.open_states[0] = "True"
    save(ctx.guild.id)
    reveal_message = await bot.get_channel(game.game_channel_id).send(f'**{ctx.author.display_name}** has revealed themselves as **MAYOR**')
    await reveal_message.pin()

@bot.command(brief='Jails a player')
@commands.check(lambda ctx: ctx.guild.id in games and games[ctx.guild.id].in_progress and games[ctx.guild.id].player_from_id(ctx.author.id).role == SalemRole.JAILOR and games[ctx.guild.id].day == int(games[ctx.guild.id].day))
async def jail(ctx, name):
    game = games[ctx.guild.id]
    player = game.player_from_id(ctx.author.id)
    
    member = member_from_string(ctx, name)
    if not member:
        return
    
    player.open_states[0] = str(member.id)
    save(ctx.guild.id)
    await ctx.message.add_reaction('✅')

@bot.command(brief='Sends a message to the jail', aliases=['jail_send', 'sjail', 'jsend'])
@commands.check(lambda ctx: ctx.guild.id in games and games[ctx.guild.id].in_progress and games[ctx.guild.id].player_from_id(ctx.author.id).role == SalemRole.JAILOR)
async def send_jail(ctx, *, message):
    game = games[ctx.guild.id]

    await bot.get_channel(game.jail_channel_id).send(f'**{game.player_from_id(ctx.author.id).role_display_name}:** {message}')
    await ctx.message.add_reaction('✅')

with open('token.txt', 'r') as file:
    bot.run(file.read())
