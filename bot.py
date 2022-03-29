import discord, aiohttp, asyncio, random, string, json
from discord.ext import commands

# Change these variables
bot = commands.Bot(command_prefix=".", description="", help_command=None, case_insensitive=True)
token = "TOKEN HERE"

guild_id = None
role_id = None

@bot.event
async def on_ready():
	print("Bot ready")
	await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="accounts | .help"))

@bot.command()
async def verify(ctx, *, username: str):
	# No bot commands in general!!
	if not isinstance(ctx.channel, discord.channel.DMChannel):
		await embed_builder(ctx, "This is a DM only command.", "")
		return

	# Check if account is already verified
	with open("database.json") as file:
		data = json.loads(file.read())
	for x in data["verified"]:
		if x["discord"] == ctx.message.author.id:
			await embed_builder(ctx, "Your discord account is already verified", "To unverify use the `.unverify` command.")
			return

	# Check if username is valid
	async with aiohttp.ClientSession() as session:
		async with session.get(f"https://api.brick-hill.com/v1/user/id?username={username}") as response:
			if response.status == 200:
				json_data = json.loads(await response.text())
				account_id = json_data["id"]
			else:
				await embed_builder(ctx, "Your account could not be found. Please try again later.", "")
				return

	# Check if account has already been linked / verified
	for x in data["verified"]:
		if x["brickhill"] == account_id:
			await embed_builder(ctx, "This brickhill account is already verified", "To unverify use the `.unverify` command.")
			return	

	# Generate code
	code = ''.join(random.choice(string.ascii_letters) for i in range(16))
	await embed_builder(ctx, f"`{code}`", "Paste this code in your account description and type `Done`")

	# Wait for user to paste code
	def check(m): return m.content.casefold() == "done" and m.channel == ctx.channel
	await bot.wait_for('message', check=check)

	# Get description and username from profile
	async with aiohttp.ClientSession() as session:
		async with session.get(f"https://api.brick-hill.com/v1/user/profile?id={account_id}") as response:
			if response.status == 200:
				json_data = json.loads(await response.text())
				description = json_data["description"]
				username = json_data["username"]
			else:
				await embed_builder(ctx, "An error has occured while reaching the API", "Please try again later.")
				return

	# Check for code in description
	if code in description:

		# Give verified role and change nickname
		guild = bot.get_guild(guild_id)
		member = await guild.fetch_member(ctx.message.author.id)
		role = guild.get_role(role_id)

		await member.edit(nick=username)
		await member.add_roles(role)

		data = {"brickhill": account_id, "discord": ctx.message.author.id}
		with open("database.json", "r+") as file:
			json_data = json.load(file)
			json_data["verified"].append(data)
			file.seek(0)
			json.dump(json_data, file, ensure_ascii=False, indent=4)

		await embed_builder(ctx, f"Account verified! `{username}`", "")

	else: await embed_builder(ctx, "Code not found in description.", "")

@bot.command()
async def unverify(ctx):

	# No bot commands in general!!
	if not isinstance(ctx.channel, discord.channel.DMChannel):
		await embed_builder(ctx, "This is a DM only command.", "")
		return

	with open("database.json", "r") as file:
		json_data = json.loads(file.read())

	removed = False
	for x in json_data["verified"]:
		if x["discord"] == ctx.message.author.id:
			json_data["verified"].remove(x)
			removed = True

	if removed == True:

		guild = bot.get_guild(guild_id)
		member = await guild.fetch_member(ctx.message.author.id)
		role = guild.get_role(role_id)

		await member.edit(nick=None)
		await member.remove_roles(role)

		with open("database.json", "w") as file:
			json.dump(json_data, file, ensure_ascii=False, indent=4)

		await embed_builder(ctx, "Successfully unverified account", "")
	else: await embed_builder(ctx, "Your account has not been verified, so cannot be unverified", "") 

@bot.command()
async def help(ctx):
	await embed_builder(ctx, "Commands", "`.verify` - Link your Brick-hill account\n`.unverify` - Unlink your Brick-hill account")

@bot.event # General error handling
async def on_command_error(ctx, error: commands.CommandError):
	if isinstance(error, commands.CommandNotFound): return
	elif isinstance(error, discord.Forbidden): await embed_builder(ctx, "I do not have permission to verify you", "Please grant the change nickname and role permissions.")
	else: await embed_builder(ctx, "An error has occured while running this command.", f"> ```{error}```")

# Embed builder function
async def embed_builder(ctx, title, description):
	embed=discord.Embed(title=title, description=description, color=0x613583)
	embed.set_footer(text="Brick hill verifier")
	await ctx.send(embed=embed)

bot.run(token, bot=True, reconnect=True)