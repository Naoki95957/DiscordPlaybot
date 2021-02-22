import discord
import asyncio
from datetime import datetime
import pytz

BOT_TIME_ZONE = 'America/Los_Angeles'
STRFTIME_FORMAT = "%d/%m/%y %H:%M:%S"

class ReactiveMessage:
    """
        Class to react and handle reactions after a delayed time
    """
    def __init__(
            self,
            channel: discord.channel.TextChannel,
            msg,
            reaction: str,
            success_msg: str,
            failed_msg: str,
            delay: int,
            threshold: int,
            builder=False,
            passed=False,
            guilds=None
        ):
        """
            Based on a posted message, it'll add a reaction and after a delayed time
            access reactions to that message
            
            Args:
                channel (discord.channel.TextChannel): text channel to msg in
                msg (str): message string
                reaction (str): single-char emoji string
                success_msg (str): message string for success
                failed_msg (str): message string for failure
                delay (int): integer in seconds
                threshold (int): integer that represents how many users are need to be successful
        """  
        if builder:
            self.msg = None
            self.success = success_msg
            self.failed = failed_msg
            self.channel = channel
            self.reaction = reaction
            self.delay = delay
            self.raw_msg = msg
            self.threshold = threshold
            self.passed = passed
            asyncio.get_event_loop().create_task(self.__start_from_builder(guilds))
            asyncio.get_event_loop().create_task(self.__check_message_reactions())
        else:
            self.msg = msg
            self.success = success_msg
            self.failed = failed_msg
            self.channel = channel
            self.reaction = reaction
            self.delay = delay
            self.raw_msg = None
            self.threshold = threshold + 1
            self.passed = False

            asyncio.get_event_loop().create_task(self.__access_after())

    async def __start_from_builder(self, guilds: list):
        """
        This helps get the actuall message from id's handed off from storage
        after serialization

        Args:
            guilds (list): list of guilds after 'on_ready' from the bot
        """
        for guild in guilds:
            if isinstance(guild, discord.Guild) and guild.id == self.raw_msg['guild_id']:
                self.channel = guild.get_channel(self.raw_msg['channel_id'])
                self.raw_msg = await self.channel.fetch_message(self.raw_msg['msg_id'])
                break
        await self.__wait_for_response()

    async def __wait_for_response(self):
        """
        This is the normal waiting call for when a reactive message is made
        """
        await self.__sleep_cycle()
        msg = await self.channel.fetch_message(self.raw_msg.id)
        if self.passed:
            return
        for reaction in msg.reactions:
            if reaction.emoji == self.reaction and reaction.count >= self.threshold:
                await self.send_success_msg()
                return
        await msg.edit(embed=None, content=self.failed)
        self.passed = True
    
    async def __check_message_reactions(self):
        """
        This function become necessary after being built from serialization

        This is because the 'on_reaction' no longer gets called if the bot is restarted
        """
        while not self.passed:
            if isinstance(self.raw_msg, discord.message.Message):
                msg = await self.channel.fetch_message(self.raw_msg.id)
                for reaction in msg.reactions:
                    if reaction.emoji == self.reaction and reaction.count >= self.threshold:
                        await self.send_success_msg()
            await asyncio.sleep(5)

    async def __access_after(self):
        """
        This will create the message and have a timer running,
        if the threshold passed prior, no follow up will occur
        """
        msg = None
        if isinstance(self.msg, discord.Embed):
            msg = await self.channel.send(embed=self.msg)
        else:
            msg = await self.channel.send(self.msg)
        self.raw_msg = msg
        await msg.add_reaction(self.reaction)
        await self.__wait_for_response()

    async def __sleep_cycle(self):
        """
        Helper funciton to sleep in 1 second intervals.
        This way we can 'save' the state in which it
        needs to continue sleeping
        """
        while(self.delay > 0):
            await asyncio.sleep(1)
            self.delay -= 1

    async def send_success_msg(self):
        """
        Sends a 'ping' message
        """
        mentions = discord.AllowedMentions(users=True, roles=True, replied_user=True)
        await self.raw_msg.channel.send(
            content=self.success,
            allowed_mentions=mentions,
            reference=self.raw_msg.to_reference())
        self.passed = True

    def is_complete(self) -> bool:
        """
        Lets you know when the job is done
        Returns:
            bool: true/false -> done/not-done
        """
        return self.passed

    def passed_threshold(self):
        """
        used to let the timer know after it wakes up to do nothing
        """
        self.passed = True

    def to_dictionary(self) -> dict:
        """
        Helper function for serialization
        
        Basically JSON but not 

        Instead of serializing the whole async and etc

        Serialize what we need to create a new object w/ 'equal' status

        Returns:
            dict: representation of this class
        """
        dictionary = {}
        dictionary['msg_id'] = self.raw_msg.id
        dictionary['channel_id'] = self.raw_msg.channel.id
        dictionary['guild_id'] = self.raw_msg.guild.id
        dictionary['reaction'] = self.reaction
        dictionary['success'] = self.success
        dictionary['failed'] = self.failed
        dictionary['delay'] = self.delay
        dictionary['offline_since'] = datetime.now(tz=pytz.timezone(BOT_TIME_ZONE)).strftime(STRFTIME_FORMAT)
        dictionary['threshold'] = self.threshold
        dictionary['passed'] = self.passed
        return dictionary

    def get_delay_remaining(self) -> str:
        return self.delay

    def get_reaction(self) -> str:
        return self.reaction

    def get_failed_msg(self) -> str:
        return self.failed

    def get_success_msg(self) -> str:
        return self.success

    def get_threshold(self) -> int:
        return self.threshold   

    def get_msg(self) -> discord.message.Message:
        return self.raw_msg

def reactive_message_builder(ref: dict, guilds: list) -> ReactiveMessage:
    """
    This is used for building ReactiveMessage after serialization

    Args:
        ref (ReactiveMessage): Must be of reactive message type
    """
    delta = (
        datetime.now() -
        datetime.strptime(ref['offline_since'], STRFTIME_FORMAT)
    )
    
    msg = {}
    msg['msg_id'] = ref['msg_id']
    msg['channel_id'] = ref['channel_id']
    msg['guild_id'] = ref['guild_id']
    return ReactiveMessage(
        channel=None,
        msg=msg,
        reaction=ref['reaction'],
        success_msg=ref['success'],
        failed_msg=ref['failed'],
        delay=ref['delay'] - delta.total_seconds(),
        threshold=ref['threshold'],
        builder=True,
        passed=ref['passed'],
        guilds=guilds
    )