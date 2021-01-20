import discord
import OHHandling.ohexceptions as exceptions
from asyncio import sleep as asy_sleep

class OHQueue:
    def __init__(self, bot):
        self._bot = bot
        self._queue = []
        self._accepting = False

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: enqueue()
    :param: discord.Member | student
    :access: public
    :preconditions: At least one handler is on duty in the guild this is called in.
    :postconditions: A discord.Member instance is added to a guild's queue if
                     the member isn't already in the queue.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    async def enqueue(self, student) -> None:
        # if the student is already queued in the guild, raise exception
        if student in self._queue: raise exceptions.ExistsInQueue

        self._queue.append(student)
        await student.send("Successfully entered queue at position %d!" % len(self._queue))

        return

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: dequeue()
    :returns: discord.Member.
    :access: public
    :preconditions: At least one discord.Member instance is in the queue for a guild.
    :postconditions: The first discord.Member instance in the queue for a guild
                     is removed from the queue and returned.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    async def dequeue(self) -> discord.Member:
        if len(self._queue) == 0: return None

        # if the queue only has one student, don't recreate the list
        if len(self._queue) == 1: return self._queue.pop()

        # if the queue for a guild has more than one person in it,
        # move the rest of it's queue forward and return the discord.Member instance
        # at index 0
        student = self._queue[0]
        self._queue = self._queue[1:len(self._queue)]

        # notify other students in that guild's queue that their position has changed
        for i in range(len(self._queue)):
            await self._queue[i].send("Your new position in queue: %d." % (i + 1))

        return student

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: remove()
    :param: discord.Member | student
    :param: int | position
    :returns: void
    :access: public
    :preconditions: The discord.Member object that is passed is present in the queue,
                    or the discord.Member object that is present at the given
                    position exists in the queue.
    :postconditions: The passed discord.Member instance or the discord.Member
                     instance at the passed position is removed from the queue.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    async def remove(self, student=None, position=None) -> None:
        found = False

        # using default parameters, we can check if an index was passed rather
        # than a discord.Member object. if this is the case, verify that it
        # exists as an index and set student to the discord.Member object at it
        if position is not None:
            if not 0 <= position < len(self._queue):
                raise exceptions.BadPosition

            student = self._queue[position]

        # iterate through a guild's queue and find the discord.Member instance.
        # once the discord.Member instance has been found, notify the other members in queue
        # their position has changed
        for i in range(len(self._queue)):
            if student == self._queue[i]: found = True
            if found and self._queue[i] != student:
                await self._queue[i].send("Your new position in queue: %d." % i)

        # remove the discord.Member object from the queue and notify them
        await student.send("You were removed from the queue.")
        self._queue.remove(student)

        return


    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: queue_emb()
    :returns: discord.Embed()
    :access: public
    :preconditions: The queue is requested by either a Handler or Queueable.
    :postconditions: The guild's current queue is returned.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    def queue_emb(self) -> discord.Embed():
        desc = ""

        # if the queue is empty, set the description of the embed as "empty"
        # else, add each student to the queue along with their position in it
        if not self._queue: desc = "Empty queue."
        else:
            for i in range(len(self._queue)):
                desc += "%d. %s\n" % (i + 1, self._queue[i].display_name)

        # create the embed with the necessary information
        queue = discord.Embed(
                    title="Current Queue",
                    color=discord.Color.blurple(),
                    description=desc
                )

        return queue

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: accepting()
    :param: bool | accept
    :returns: void
    :access: public
    :preconditions: Either a discord.Guild instance can go from having no
                    handlers on duty to at least one, or from at least one handler
                    on duty to having none.
    :postconditions: The students are wiped from the queue after 15 minutes if
                     office hours have not reopened.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    def accepting(self, accepting) -> None:
        self._accepting = accepting

        return

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: end_oh()
    :returns: void
    :access: public
    :preconditions: All handlers in a discord.Guild instance have gone off duty.
    :postconditions: The students are wiped from the queue after 15 minutes if
                     office hours have not reopened.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    async def end_oh(self) -> None:
        # retain the queue for 15 minutes in the case another handler goes on duty
        await asy_sleep(60 * 15)

        # since accepting can change in the 15 minutes, we check if another handler
        # has gone on duty. If they have, don't wipe the students from the queue
        if self._accepting: return

        for student in self._queue:
            await student.send("Office hours have closed, so you were removed from the queue.")
            self._queue.remove(student)

        return

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: is_empty()
    :returns: bool
    :access: public
    :preconditions: OHQueue has been instantiated.
    :postconditions: A boolean that indicates if a guild's queue is empty is returned.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    def is_empty(self) -> bool:
        return len(self._queue) == 0

    """""""""""""""""""""""""""""""""""""""""""""""""""
    :name: check()
    :param: int | student_id
    :returns: bool
    :access: public
    :preconditions: A member attempts to remove themself from a guild's queue.
    :postconditions: A boolean that indicates if a discord.Member object that
                     matches the passed id exists a guild's queue is returned.
    """""""""""""""""""""""""""""""""""""""""""""""""""
    def check(self, student_id) -> bool:
        for member in self._queue:
            if member.id == student_id: return True

        return False
