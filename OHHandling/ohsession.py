import discord
from discord.ext import commands
from discord.utils import get as duget
from pathvalidate import sanitize_filename as sanitize
from json import dumps
from pytz import timezone

class OHSession:
    def __init__(self, handler, student):
        self._handler = handler
        self._student = student
        self._role = None
        self._category = None
        self._text = None
        self._voice = None
        self._is_open = False

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: open()
    :param: discord.Guild | guild
    :returns: void
    :access: public
    :preconditions: This OHSession has been instantiated.
    :postconditions: A role, a category, a text channel, and a voice channel
                     is created in a guild.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    async def open(self, guild) -> None:
        session_name = "Session for %s" % self._student.display_name

        # create a discord.Role object based off of the student's name
        self._role = await guild.create_role(name=session_name)

        # create a permission dictionary permissions for the category and it's channels
        perms = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self._role: discord.PermissionOverwrite(read_messages=True)
        }

        # create a new hidden category in a guild and set it to be at the top of
        # the server's channel list
        self._category = await guild.create_category(name=session_name, overwrites=perms)
        await self._category.edit(position=0)

        # create a text and voice channel for the category
        self._text = await guild.create_text_channel(
                        name="session-text",
                        category=self._category
                     )
        self._voice = await guild.create_voice_channel(
                        name="Session Voice",
                        category=self._category
                      )

        # add the session role to the handler and student
        await self._handler.add_roles(self._role)
        await self._student.add_roles(self._role)

        self._is_open = True

        # when the channel opens, send a message pinging the student and the handler
        student = self._student.mention
        handler = self._handler.mention
        return await self._text.send("Hello %s! Welcome to your session with %s!" % (student, handler))

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: close()
    :param: discord.TextChannel | channel
    :returns: void
    :access: public
    :preconditions: This OHSession has been opened.
    :postconditions: The existing discord.Role, discord.Category, discord.TextChannel,
                     and discord.VoiceChannel instances are deleted.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    async def close(self, channel) -> None:
        if not self._is_open:
            return await channel.send("There isn't a session open!")

        # using a lambda function to return a clean, usable filename from a string
        fileize = lambda string: sanitize(string.replace(' ', '_'))

        # gather and clean the student and handler names so they can be used
        # in a file name
        student_name = fileize(self._student.display_name)
        handler_name = fileize(self._handler.display_name)

        # convert the channel.created_at datetime instance's timezone to EST
        channel_est_converted = self._text.created_at.astimezone(timezone("EST"))

        # create a file in /sessionlogs/ that follows this naming format:
        # Student_name_Handler_name_MonthDayYear_HourMinute.txt
        file_name = "OHHandling/sessionlogs/%s_%s_%02d%02d%d_%02d%02d.txt" % (
                                student_name,
                                handler_name,
                                channel_est_converted.month,
                                channel_est_converted.day,
                                channel_est_converted.year,
                                channel_est_converted.hour,
                                channel_est_converted.minute
                            )

        # create and open the file named above
        with open(file_name, 'w') as file:
            messages = []

            # iterate through all messages in self._text and add them to the
            # messages list for dumping cleanly into a file
            async for message in self._text.history(limit=1000, oldest_first=True):

                # convert every message's datetime instance from utc to est for
                # proper timestamps in the message, which follows this format:
                # [Hour:Minute] Author Name: Content [[[NUM ATTACHMENTS]]]
                message_est_converted = message.created_at.astimezone(timezone("EST"))

                # if there is at least one file attached and this message has a
                # text body to it, display the text along with the number of files
                # attached
                if message.attachments and message.content:
                    messages.append("[%02d:%02d] %s: %s [[[%d ATTACHMENTS]]]" % (
                                        message_est_converted.hour,
                                        message_est_converted.minute,
                                        message.author.display_name,
                                        message.content,
                                        len(message.attachments)
                                    ))

                # if there is at least one attachment and no text body, just add
                # the number of files attached
                elif message.attachments and not message.content:
                    messages.append("[%02d:%02d] %s: [[[%d ATTACHMENTS]]]" % (
                                        message_est_converted.hour,
                                        message_est_converted.minute,
                                        message.author.display_name,
                                        len(message.attachments)
                                    ))

                # if there is just a body f text with no attachments, only display
                # that
                else:
                    messages.append("[%02d:%02d] %s: %s" % (
                                        message_est_converted.hour,
                                        message_est_converted.minute,
                                        message.author.display_name,
                                        message.content,
                                    ))

            # dump the entire history of the channel into the created file with
            # an indent of zero for readability
            file.write(dumps(messages, indent=0))

        # delete all data in a guild associated with this OHSession
        await self._role.delete()
        await self._voice.delete()
        await self._text.delete()
        await self._category.delete()

        return

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: get_members()
    :returns: {str: discord.Member, str: discord.Member}
    :access: public
    :preconditions: This OHSession has been instantiated.
    :postconditions: The handler and the student's discord.Member instances are
                     returned.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    def get_members(self) -> {str: discord.Member, str: discord.Member}:
        return {"handler": self._handler, "student": self._student}
