import discord
from discord.ext import commands
from discord.utils import get as duget
from OHHandling.ohsession import OHSession
from OHHandling.ohqueue import OHQueue
import OHHandling.ohexceptions as exceptions

class OHHandling(commands.Cog):
    def __init__(self, bot):
        self._bot = bot
        self._num_guilds_accepting = 0
        self._queues = {}
        self._open_sessions = {}
        self._handlers_on_duty = {}
        self._notify_channel = {}
        # i could use inheritance here instead of dictionaries... tempting
        # EDIT: yeah ima do it lol

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: on_ready()
    :returns: void
    :access: public
    :preconditions: Bot is running and this cog is loaded.
    :postconditions: All member dictionaries are initialized with discord.Guild.id keys.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self._bot.guilds:
            self._queues[guild.id] = OHQueue(self._bot)
            self._open_sessions[guild.id] = []
            self._handlers_on_duty[guild.id] = {}
            self._notify_channel[guild.id] = duget(guild.text_channels, name="queue-reasons")

            print("Member variables in <%s> initialized." % guild.name)

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: on_guild_join()
    :param: discord.Guild | guild
    :returns: void
    :access: public
    :preconditions: The bot client has joined a new server and is online.
    :postconditions: This discord.Guild.id is added as a key to all member dictionaries.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    @commands.Cog.listener()
    async def on_guild_join(self, guild) -> None:
        self._queues[guild.id] = OHQueue(self._bot)
        self._open_sessions[guild.id] = []
        self._handlers_on_duty[guild.id] = {}

        # when joining a guild, we can safely assume that it doesn't have the
        # required roles or channels for OHHandling to work, so we create them
        await self._create_reqs(guild)

        print("Added to <%s>: created roles and channel." % guild.name)

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: on_guild_remove()
    :param: discord.Guild | guild
    :returns: void
    :access: public
    :preconditions: The bot client has been kicked from, banned from, or has
                    otherwise been removed from a server and is online.
    :postconditions: The existing discord.Guild.id and all of it's data is removed
                     from all member dictionaries.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    @commands.Cog.listener()
    async def on_guild_remove(self, guild) -> None:
        del self._queues[guild.id]
        del self._open_sessions[guild.id]
        del self._handlers_on_duty[guild.id]
        del self._notify_channel[guild.id]

        print("Removed from <%s>, deleting it from member variables." % guild.name)

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: on_member_join()
    :param: discord.Member | member
    :returns: void
    :access: public
    :preconditions: A new discord.Member instance is added to a discord.Guild.
    :postconditions: A discord.Role instance of name "Queueable" is added to
                     the new discord.Member instance.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        queueable = duget(member.guild.roles, name="Queueable")
        await member.add_roles(queueable)

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: _enqueue()
    :param: discord.ext.commands.Context | ctx
    :param: str* | reason
    :returns: void
    :access: private
    :preconditions: At least one handler is on duty in this guild, the author has
                    the Queueable role, and the author isn't already queued.
    :postconditions: The author's discord.Member instance is appended to this
                     guild's queue.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    @commands.has_role("Queueable")
    @commands.command(name="enqueue", aliases=["queue", "request", "q"])
    @exceptions.enqueue()
    async def _enqueue(self, ctx, *reason) -> None:
        # attempt to enqueue the author into this guild's queue
        await self._queues[ctx.guild.id].enqueue(ctx.author)

        # create an embed with relevant information to send to this guild's handlers
        embed = discord.Embed(
                    title="A Person Queued",
                    color=discord.Color.blurple(),
                    timestamp=ctx.message.created_at
                )
        embed.add_field(name="For reason:", value=" ".join(reason), inline=False)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)

        # notify all of this guild's handlers on duty that a new person has queued
        msg = "%s Queued in <%s>." % (ctx.author.display_name, ctx.guild.name)
        await self._handler_notify(ctx.guild.id, msg)
        await self._embed_send(ctx, embed)

        return

    """
    :name: _kick()
    :param: discord.ext.commands.Context | ctx
    :param: int | position
    :returns: void
    :access: private
    :preconditions: The author has the Handler role and at least one discord.Member
                    object is queued in this guild.
    :postconditions: A discord.Member object is removed from this guild's queue.
    """
    @commands.has_role("On Duty")
    @commands.command(name="kick", aliases=["boot", "remove"])
    @exceptions.kick()
    async def _kick(self, ctx, position: int) -> None:
        # attempt to remove person in this guild's queue at the given position
        await self._queues[ctx.guild.id].remove(position=(position - 1))
        await ctx.send("Success.")

        return

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: _current_queue()
    :param: discord.ext.commands.Context | ctx
    :returns: void
    :access: private
    :preconditions: The author has either the Handler role or Queueable role
                    in this guild.
    :postconditions: The guild's current queue is sent.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    @commands.has_any_role("Handler", "Queueable")
    @commands.command(name="currqueue", aliases=["currq", "cq"])
    @exceptions.office_hours_exceptions()
    async def _current_queue(self, ctx) -> None:
        # make sure this isn't in a DM channel
        if ctx.message.channel is discord.DMChannel: raise exceptions.CommandInDM
        await ctx.send(embed=self._queues[ctx.guild.id].queue_emb())

        return

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: _dequeue()
    :param: discord.ext.commands.Context | ctx
    :returns: void
    :access: private
    :preconditions: At least one handler is on duty in this guild, the author
                    has the Queueable role, and the author is queued.
    :postconditions: The author's discord.Member instance is removed from this
                     guild's queue.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    @commands.has_role("Queueable")
    @commands.command(name="dequeue", aliases=["leave", "leavequeue"])
    @exceptions.dequeue()
    async def _dequeue(self, ctx) -> None:
        # remove the author from this guild's queue and notify all of this guild's
        # handlers on duty that the author has been removed
        await self._queues[ctx.guild.id].remove(student=ctx.author)
        await self._handler_notify(ctx.guild.id, "%s left the queue." % ctx.author.display_name)

        return

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: _accept()
    :param: discord.ext.commands.Context | ctx
    :returns: void
    :access: private
    :preconditions: The author is not currently handling a session, has the Handler
                    role, and has the On Duty role.
    :postconditions: A new instance of OHSession is created, opened, and is
                     appended to this guild's open_sessions.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    @commands.has_role("Handler")
    @commands.command(name="accept", aliases=["take", "yoink"])
    @exceptions.accept()
    async def _accept(self, ctx) -> None:
        # create a new OHSession, open it for use, then store it in the value
        # for this guild's open_sessions
        new_session = OHSession(ctx.author, await self._queues[ctx.guild.id].dequeue())
        await new_session.open(ctx.guild)
        self._open_sessions[ctx.guild.id].append(new_session)

        # send the current queue after a student's acceptance for other Handler's
        # reference
        await ctx.send(embed=self._queues[ctx.guild.id].queue_emb())

        return

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: _close()
    :param: discord.ext.commands.Context | ctx
    :returns: void
    :access: private
    :preconditions: The author is currently handling a session, has the Handler
                    role, and has the On Duty role.
    :postconditions: The OHSession instance that the handler has open in this guild is
                     closed and removed from this guild's open_sessions list.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    @commands.has_role("Handler")
    @commands.command(name="close", aliases=["finish", "finishup", "finished", "done"])
    @exceptions.close()
    async def _close(self, ctx) -> None:
        # iterate through all open sessions and find the one that the author is handling
        # once found, close the session and remove it from the open sessions
        for session in self._open_sessions[ctx.guild.id]:
            if session.get_members()["handler"] == ctx.author:
                await session.close(ctx)
                self._open_sessions[ctx.guild.id].remove(session)
                return

        return

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: _on_duty()
    :param: discord.ext.commands.Context | ctx
    :returns: void
    :access: private
    :preconditions: The author has the Handler role and is not On Duty in this guild.
    :postconditions: The author is given the On Duty role in this guild and their
                     discord.Member instance is added to this guild's handlers_on_duty.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    @commands.has_role("Handler")
    @commands.command(name="onduty", aliases=["on"])
    @exceptions.on_duty()
    async def _on_duty(self, ctx) -> None:
        duty_role = duget(ctx.guild.roles, name="On Duty")

        # add On Duty to the author and add their object to this guild's
        # handlers_on_duty.
        await ctx.author.add_roles(duty_role)
        self._handlers_on_duty[ctx.guild.id][ctx.author.id] = ctx.author

        # if no other handlers were on duty before this handler, add to the
        # num_guilds_accepting and change the client's presence
        # we will also set the queue's accepting bool to true in case students
        # are about to be wiped from it
        if len(self._handlers_on_duty[ctx.guild.id]) == 1:
            self._num_guilds_accepting += 1
            await self._pres_change()

            self._queues[ctx.guild.id].accepting(True)

        return

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: _off_duty()
    :param: discord.ext.commands.Context | ctx
    :returns: void
    :access: private
    :preconditions: The author has the Handler role and is On Duty in this guild.
    :postconditions: The On Duty role is removed from the author and their
                     discord.Member instance is removed from this guild's
                     handlers_on_duty.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    @commands.has_role("Handler")
    @commands.command(name="offduty", aliases=["off"])
    @exceptions.off_duty()
    async def _off_duty(self, ctx) -> None:
        # retrieve the On Duty role for checking and adding
        duty_role = duget(ctx.guild.roles, name="On Duty")

        # take the On Duty role from the author and remove their discord.Member
        # from instance from this guild's handlers_on_duty.
        await ctx.author.remove_roles(duty_role)
        del self._handlers_on_duty[ctx.guild.id][ctx.author.id]

        # if this handler is the last to go off duty, subtract from num_guilds_accepting
        # and change the client's presence
        # we will also remove the student in the queue after 15 minutes if no
        # handlers have gone back on duty
        if len(self._handlers_on_duty[ctx.guild.id]) == 0:
            self._num_guilds_accepting -= 1
            await self._pres_change()

            self._queues[ctx.guild.id].accepting(False)
            await self._queues[ctx.guild.id].end_oh()

        return

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: _handler_notify()
    :param: int | guild_id
    :param: str | msg
    :returns: void
    :access: private
    :preconditions: This guild has at least one discord.Member instance in it's
                    handlers_on_duty.
    :postconditions: All discord.Member instances in this guild's handlers_on_duty
                     are sent the passed str.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    async def _handler_notify(self, guild_id, msg) -> None:
        for key in self._handlers_on_duty[guild_id].keys():
            await self._handlers_on_duty[guild_id][key].send(msg)

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: _embed_send()
    :param: discord.ext.commands.Context | context
    :param: discord.Embed | embed
    :returns: void
    :access: private
    :preconditions: _enqueue() was successfully executed.
    :postconditions: The discord.Embed instance is sent to this guild's
                     #student-reasons channel.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    async def _embed_send(self, context, embed) -> None:
        channel = duget(context.guild.channels, name="queue-reasons")
        await channel.send(embed=embed)

        return

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: _pres_change()
    :returns: void
    :access: private
    :preconditions: _on_duty() or _off_duty() has successfully executed and the
                    len of a guild's handlers_on_duty is greater than 0.
    :postconditions: The client's custom status is updated to reflect the total
                     number of guilds actively ready to create OHSessions.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    async def _pres_change(self) -> None:
        plural = "queue." if self._num_guilds_accepting == 1 else "queues."
        new_pres = discord.Activity(name="%d %s" % (self._num_guilds_accepting, plural), type=discord.ActivityType.watching)
        await self._bot.change_presence(status=discord.Status.dnd, activity=new_pres)

        return

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: _create_reqs()
    :param: discord.Guild | guild
    :returns: void
    :access: private
    :preconditions: The bot client has joined a guild.
    :postconditions: The guild is populated with the necessary roles and channels
                     that are needed for office hours.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    async def _create_reqs(self, guild) -> None:
        # mass create all required roles for handling OHSessions
        handler = await guild.create_role(name="Handler")
        on_duty = await guild.create_role(name="On Duty")
        queueable = await guild.create_role(name="Queueable")

        # creating permissions for an Office Hours category
        perms = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            handler: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            on_duty: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # create the category and the queue-reasons channel for it at the top
        # of the channel list
        cat = await guild.create_category(name="Office Hours", overwrites=perms)
        await cat.edit(position=0)
        self._notify_channel[guild.id] = await guild.create_text_channel(name="queue-reasons", category=cat)

        return

def setup(bot):
    bot.add_cog(OHHandling(bot))
