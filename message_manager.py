import discord
import asyncio

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
            threshold: int
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
        await asyncio.sleep(self.delay)
        msg = await self.channel.fetch_message(msg.id)
        if self.passed:
            return
        for reaction in msg.reactions:
            if reaction.emoji == self.reaction and reaction.count >= self.threshold:
                await msg.channel.send(self.success)
                return
        await msg.edit(embed=None, content=self.failed)
        self.passed = True
        
    def get_success_msg(self) -> str:
        return self.success

    def get_threshold(self) -> int:
        return self.threshold   

    def get_msg(self) -> discord.message.Message:
        return self.raw_msg
