import os
from os import path
from datetime import datetime, timedelta
import discord
import pickle
import copy
import pytz
import time
from threading import Thread
from message_manager import ReactiveMessage, reactive_message_builder, BOT_TIME_ZONE, STRFTIME_FORMAT
from dotenv import load_dotenv

# day * hours * minutes * seconds
MAX_EVENT_TIME = 14 * 24 * 60 * 60 # 604800s

class PlayBot(discord.Client):

    bot_id = 1234567890
    my_id = 1234567890

    file = "./bot_stuff.p"
    timeout = 15
    permitted_roles = []
    role_format = "<@&{0}>"
    threshold = 3
    pinging = "someone"
    base_command = "!play "
    formated_prompt_str = "Who wants to join in and play in {0} days, {1}hrs and {2}m?\nWe need {3} or more people to react with {4} to make it happen!\n\n"
    formated_success_str = "Yo, <@&{0}>! Let's get some games going!"
    formated_failed_str = "Sorry! Looks like we didn't get enough players for this time."
    reaction_str = "⚽"
    running_msgs = []
    roles = []

    def __init__(self):
        super().__init__()
        load_dotenv()
        TOKEN = os.getenv('DISCORD_TOKEN')
        self.bot_id = os.getenv('BOT_ID')
        self.my_id = os.getenv('MY_ID')
        Thread(target=self.__save_loop).start()
        self.run(TOKEN)

    async def on_ready(self):
        self.try_loading()
        for guild in self.guilds:
            print(
                f'{self.user} is connected to the following guilds:\n'
                f'{guild.name}(id: {guild.id})'
                f'\nChannel list: {guild.text_channels}'
                f'\nRoles in order: {guild.roles}'
            )
            self.roles.extend(guild.roles)
        # Setting `Playing ` status
        # await Playbot.change_presence(self, activity=discord.Game(name="a game"))

        # # Setting `Streaming ` status
        # await Playbot.change_presence(self, activity=discord.Streaming(name="My Stream", url=my_twitch_url))

        # # Setting `Listening ` status
        await PlayBot.change_presence(self, activity=discord.Activity(type=discord.ActivityType.listening, name="The beautiful sound of DSL"))
        # # Setting `Watching ` status
        # await Playbot.change_presence(self, activity=discord.Activity(type=discord.ActivityType.watching, name="a movie"))


    async def on_message(self, message: discord.message.Message):
        cont = str(message.content)
        # Here begins a giant ugly list of command checking
        if message.author.id == self.bot_id or "!play" not in cont:
            return
        if cont.startswith(self.base_command + "help"):
            desc = (
                self.base_command +
                "ping [role id]\n"+
                "\tsets which role will be pinged\n\n"+
                self.base_command +
                "count [integer]\n"+
                "\tsets how many players will be needed to make a ping\n\n"+
                self.base_command +
                "permit [role id]\n"+
                "\tsets which roles can control my settings\n\n"+
                self.base_command +
                "remove [role id]\n"+
                "\tremoves which roles can control my settings\n\n"+
                self.base_command +
                "reaction [emoji]\n"+
                "\tsets which emoji will used\n\n"+
                self.base_command +
                "[hh:mm]\n"+
                "\tschedules an event 'hh:mm' time from now and if enough players wanna join in, it'll ping!\n\n"+
                self.base_command +
                "help\n"+
                "\tget the list of commands"
            )
            embed_var = discord.Embed(title="Commands", description=desc)
            await message.channel.send(embed=embed_var)
        elif cont.startswith(self.base_command + "ping "):
            if message.author.top_role.id in self.permitted_roles:
                try:
                    self.pinging = int(cont.replace(self.base_command + 'ping ', ''))
                    name = "them"
                    role = self.get_role(self.pinging)
                    if role:
                        name = role.name
                    await message.channel.send("I will ping " + name +" when the time comes :)")
                except Exception as e:
                    await message.channel.send("Sorry, I couldn't undersand that")
            else:
                await message.channel.send("Sorry, you do not have permission <@" + str(message.author.id) + ">")
        elif cont.startswith(self.base_command + "permit "):
            if message.author.id == int(self.my_id) or message.author.top_role.id in self.permitted_roles:
                try:
                    role_id = int(cont.replace(self.base_command + 'permit ', ''))
                    self.permitted_roles.append(role_id)
                    await message.channel.send("I will listen to the " + self.get_role(role_id).name +" role when they command me to :)")
                except Exception as e:
                    await message.channel.send("Sorry, I couldn't undersand that")
            else:
                await message.channel.send("Sorry, you do not have permission <@" + str(message.author.id) + ">")
        elif cont.startswith(self.base_command + "remove "):
            if message.author.id == int(self.my_id) or message.author.top_role.id in self.permitted_roles:
                try:
                    role_id = int(cont.replace(self.base_command + 'remove ', ''))
                    self.permitted_roles.pop(self.permitted_roles.index(role_id))
                    await message.channel.send("I will no longer listen to the " + self.get_role(role_id).name +" role")
                except Exception as e:
                    await message.channel.send("Sorry, I couldn't undersand that")
            else:
                await message.channel.send("Sorry, you do not have permission <@" + str(message.author.id) + ">")
        elif cont.startswith(self.base_command + 'count '):
            if message.author.top_role.id in self.permitted_roles:
                try:
                    self.threshold = int(cont.replace(self.base_command + 'count ', ''))
                    await message.channel.send("I will ping when I see " + str(self.threshold) + " or more players moving forward :)")
                except Exception as e:
                    await message.channel.send("Sorry I couldn't understand that :(")
            else:
                await message.channel.send("Sorry, you do not have permission <@" + str(message.author.id) + ">")
        elif cont.startswith(self.base_command + "reaction "):
            if message.author.top_role.id in self.permitted_roles:
                try:
                    temp = cont.replace(self.base_command + 'reaction ', '')
                    await message.add_reaction(temp)
                    self.reaction_str = temp
                except Exception as e:
                    await message.channel.send("I can't use that emoji :(")
            else:
                await message.channel.send("Sorry, you do not have permission <@" + str(message.author.id) + ">")
        elif cont.startswith(self.base_command):
            if len(cont.split(' ')) > 1:
                try:
                    time_str = cont.split(' ')[1]
                    time_split = time_str.split(':')
                    days = 0
                    hrs = int(time_split[0])
                    minutes = int(time_split[1])
                    if len(time_split) > 2:
                        days = int(time_split[0])
                        hrs = int(time_split[1])
                        minutes = int(time_split[2])
                    now = datetime.now(tz=pytz.timezone(BOT_TIME_ZONE))
                    delta = timedelta(days=days, hours=hrs, minutes=minutes)
                    now = now + delta
                    delay_seconds = int(delta.total_seconds())
                    if delay_seconds > MAX_EVENT_TIME:
                        await message.channel.send("Sorry that's too far into the future!\n")
                        return
                    embed_var = discord.Embed(
                        title="Let's Play!", 
                        description=self.formated_prompt_str.format(
                            delta.days, 
                            int(delta.seconds / (60 * 60)),
                            int(delta.seconds / 60) % 60,
                            self.threshold, 
                            self.reaction_str))
                    embed_var.add_field(name='Pacific Time', value=now.strftime("%A\n%d/%m/%Y\n%I:%M %p"))
                    now = now.astimezone(tz=pytz.timezone('US/Eastern'))
                    embed_var.add_field(name='Eastern Time', value=now.strftime("%A\n%d/%m/%Y\n%I:%M %p"))
                    now = now.astimezone(tz=pytz.timezone('Europe/Madrid'))
                    embed_var.add_field(name='Central European Time', value=now.strftime("%A\n%d/%m/%Y\n%I:%M %p"))

                    self.running_msgs.append(
                        ReactiveMessage(
                            message.channel, 
                            embed_var, 
                            self.reaction_str, 
                            self.formated_success_str.format(self.pinging), 
                            self.formated_failed_str, 
                            delay_seconds, 
                            self.threshold
                        )
                    )
                except Exception as e:
                    await message.channel.send(
                        "Sorry I couldn't understand that :(\n" +
                        "The defualt format is `" + self.base_command + "H:m` or `" + self.base_command + "D:H:m` and I will wait for D days, H hours and m minutes")
            else:
                await message.channel.send("<@" + str(message.author.id) + ">, there should be 2 arguments. EG: `!play 1:00` to play in 1hr")
        self.try_saving()

    async def on_reaction_add(self, reaction: discord.reaction.Reaction, user: discord.user.User):
        # Checking reactions
        message = reaction.message
        for rmsg in self.running_msgs:
            if rmsg.is_complete():
                self.running_msgs.pop(self.running_msgs.index(rmsg))
            elif (
                    message.id == rmsg.get_msg().id 
                    and user.id != self.bot_id
                    and rmsg.get_threshold() <= reaction.count
                ):
                await rmsg.send_success_msg()
                rmsg.passed_threshold()
                self.running_msgs.pop(self.running_msgs.index(rmsg))

    def try_loading(self):
        """
        Helper that loads in save file so that some previous commands are loaded
        """
        try:
            if path.exists(self.file):
                dictionary = pickle.load(open(self.file, 'rb'))
                self.permitted_roles = dictionary['permitted_roles']
                self.threshold = dictionary['threshold']
                self.base_command = dictionary['base_command']
                self.reaction_str = dictionary['reaction_str']
                self.pinging = dictionary['pinging']
                self.running_msgs = [reactive_message_builder(rmsg_dict, self.guilds) for rmsg_dict in dictionary['running_msgs']]
        except Exception as e:
            print("failed to load file :/")
            print(e)

    def try_saving(self):
        """
        Helper that saves a file so that some previous commands can be loaded
        """
        for rmsg in self.running_msgs:
            if rmsg.is_complete():
                self.running_msgs.pop(self.running_msgs.index(rmsg))
        dictionary = {}
        dictionary['permitted_roles'] = copy.deepcopy(self.permitted_roles)
        dictionary['threshold'] = copy.deepcopy(self.threshold)
        dictionary['base_command'] = copy.deepcopy(self.base_command)
        dictionary['reaction_str'] = copy.deepcopy(self.reaction_str)
        dictionary['pinging'] = copy.deepcopy(self.pinging)
        rmsg_dicts = [rmsg.to_dictionary() for rmsg in self.running_msgs]
        dictionary['running_msgs'] = copy.deepcopy(rmsg_dicts)
        pickle.dump(dictionary, open(self.file, 'wb'))

    def __save_loop(self):
        while True:
            time.sleep(15)
            self.try_saving()

    def get_role(self, id: int) -> discord.Role:
        """
        Helper function that gets discord role object from id

        Args:
            id (int): role ID

        Returns:
            discord.Role : discord role object
        """
        for role in self.roles:
            if role.id == id:
                return role
        return None
    
def main():
    bot = PlayBot()

if __name__ == "__main__":
    main()