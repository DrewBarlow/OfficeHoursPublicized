import discord
from discord.utils import get as duget
from functools import wraps

class AlreadyOnDuty(Exception): pass
class BadPosition(Exception): pass
class CommandInDM(Exception): pass
class ExistsInQueue(Exception): pass
class NoQueueReason(Exception): pass
class NotInQueue(Exception): pass
class NotOnDuty(Exception): pass
class InSession(Exception): pass
class OfficeHoursClosed(Exception): pass
class QueueIsEmpty(Exception): pass

def office_hours_exceptions():
    def decorator(fxn):
        @wraps(fxn)
        async def inner(*args):
            try:
                return await fxn(*args)
            except ExistsInQueue:  # l3
                return await args[1].send("You're already queued!")
            except BadPosition:  # l3
                return await args[1].send("Nobody is queued at that position.")
            except NoQueueReason:  # l3
                return await args[1].send("You need a reason to queue.")
            except NotInQueue:  # l3
                return await args[1].send("You aren't queued.")
            except NotOnDuty:  # l2
                return await args[1].send("You aren't on duty.")
            except AlreadyOnDuty:  # l2
                return await args[1].send("You are already on duty.")
            except InSession:  # l2
                return await args[1].send("You are in a session.")
            except OfficeHoursClosed:  # l2
                return await args[1].send("Office hours are closed.")
            except QueueIsEmpty:  # l2
                return await args[1].send("The queue is currently empty.")
            except CommandInDM: pass  # l1

        return inner
    return decorator

def enqueue():
    def decorator(fxn):
        @wraps(fxn)
        @office_hours_exceptions()
        async def inner(*args):
            # make sure this isn't in a DM channel
            if args[1].message.channel is discord.DMChannel: raise CommandInDM

            # delete the queue message to hide the reason from other students
            await args[1].message.delete()

            # don't allow the author to queue if no handlers are on duty in this guild
            if len(args[0]._handlers_on_duty[args[1].guild.id]) == 0:
                raise OfficeHoursClosed

            # don't execute the function if no reason for queueing is given by the author
            MIN_ARGS_NEEDED = 3
            if len(args) < MIN_ARGS_NEEDED: raise NoQueueReason

            # don't execute the function if the author is already in a session in
            # this guild
            for session in args[0]._open_sessions[args[1].guild.id]:
                if session.get_members()["student"] == args[1].author:
                    raise InSession

            return await fxn(*args)
        return inner
    return decorator

def kick():
    def decorator(fxn):
        @wraps(fxn)
        @office_hours_exceptions()
        async def inner(*args):
            # make sure this isn't in a DM channel
            if args[1].message.channel is discord.DMChannel: raise CommandInDM

            # if the guild's queue is currently empty, don't execute the function
            if args[0]._queues[args[1].guild.id].is_empty():
                raise QueueIsEmpty

            return await fxn(*args)
        return inner
    return decorator

def dequeue():
    def decorator(fxn):
        @wraps(fxn)
        @office_hours_exceptions()
        async def inner(*args):
            # make sure this channel isn't in a DM channel
            if args[1].message.channel is discord.DMChannel: raise CommandInDM

            # don't execute the function if the author isn't queued in this guild
            if not args[0]._queues[args[1].guild.id].check(args[1].author.id):
                raise NotInQueue

            return await fxn(*args)
        return inner
    return decorator

def accept():
    def decorator(fxn):
        @wraps(fxn)
        @office_hours_exceptions()
        async def inner(*args):
            # make sure this isn't in a DM channel
            if args[1].message.channel is discord.DMChannel: raise CommandInDM

            # don't execute the function if the author isn't on duty in this guild
            if args[0]._handlers_on_duty[args[1].guild.id].get(args[1].author.id) is None:
                raise NotOnDuty

            # don't execute the function if the queue for this guild is empty
            if args[0]._queues[args[1].guild.id].is_empty():
                raise QueueIsEmpty

            # don't execute the function if the author is already handling a session
            # in this guild
            for session in args[0]._open_sessions[args[1].guild.id]:
                if session.get_members()["handler"] == args[1].author:
                    raise InSession

            return await fxn(*args)
        return inner
    return decorator

def close():
    def decorator(fxn):
        @wraps(fxn)
        @office_hours_exceptions()
        async def inner(*args):
            # make sure this isn't in a DM channel
            if args[1].message.channel is discord.DMChannel: raise CommandInDM

            # don't execute the function if the handler isn't on duty in this guild
            if args[1].author.id not in args[0]._handlers_on_duty[args[1].guild.id]:
                raise NotOnDuty

            return await fxn(*args)
        return inner
    return decorator

def on_duty():
    def decorator(fxn):
        @wraps(fxn)
        @office_hours_exceptions()
        async def inner(*args):
            # make sure this isn't in a DM channel
            if args[1].message.channel is discord.DMChannel: raise CommandInDM

            # don't continue if the author is already on duty in this guild
            duty_role = duget(args[1].guild.roles, name="On Duty")
            if duty_role in args[1].author.roles: raise AlreadyOnDuty

            return await fxn(*args)
        return inner
    return decorator

def off_duty():
    def decorator(fxn):
        @wraps(fxn)
        @office_hours_exceptions()
        async def inner(*args):
            # make sure this isn't in a DM channel
            if args[1].message.channel is discord.DMChannel: raise CommandInDM

            # prevent the author from going off duty if they're handling a session
            for session in args[0]._open_sessions[args[1].guild.id]:
                if session.get_members()["handler"] == args[1].author:
                    raise InSession

            # don't continue if the author is not on duty in this guild
            #duty_role = duget(args[1].guild.roles, name="On Duty")
            if duget(args[1].guild.roles, name="On Duty") not in args[1].author.roles:
                raise NotOnDuty

            return await fxn(*args)
        return inner
    return decorator
