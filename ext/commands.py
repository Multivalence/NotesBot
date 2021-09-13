import discord
from discord.ext import commands
from discord.ext import menus
from sqlite3 import IntegrityError

class NoSubcommandFound(commands.CommandError):
    pass

class NoteAlreadyExists(commands.CommandError):
    pass

class MemberNotFound(commands.CommandError):
    pass

class CharacterLimited(commands.CommandError):
    pass


class NotesMenu(menus.ListPageSource):
    def __init__(self, data):
        super().__init__(data, per_page=10)

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page
        joined = '\n'.join(f'{i}. {v.mention}' for i, v in enumerate(entries, start=1))

        embed = discord.Embed(
            title="Notes",
            description=joined,
            colour=discord.Colour.blue()
        )

        embed.set_footer(text=f"Page: {menu.current_page + 1}/{self.get_max_pages()}")
        embed.set_thumbnail(url="https://library.kissclipart.com/20180914/gze/kissclipart-clipboard-check-clipart-paper-computer-icons-clipb-6cdfd47416dde35f.png")

        return embed



class Commands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.is_char_limited = lambda text : not len(list(text)) <= 1980

    async def cog_command_error(self, ctx, error):

        # Gets original attribute of error
        error = getattr(error, "original", error)

        if isinstance(error, NoSubcommandFound):
            return await ctx.send("You did not provide a sub-command!")

        elif isinstance(error, NoteAlreadyExists):
            return await ctx.send("Note already exists for this user. Use the `append` sub-command instead")

        elif isinstance(error, MemberNotFound):
            return await ctx.send("There are no notes for the member you have specified!")

        elif isinstance(error, CharacterLimited):
            return await ctx.send("You have surpassed the maximum character limit. Changes have not been saved!")


    @commands.guild_only()
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.group(invoke_without_command=True)
    async def note(self, ctx):
        raise NoSubcommandFound


    @note.command(name='read', description='Read note for specified user')
    async def read(self, ctx, member : discord.Member):

        await ctx.trigger_typing()

        async with self.bot.db.execute('SELECT note from notes WHERE user_id = (?)', (member.id,)) as cursor:
            text = await cursor.fetchone()


        if not text:
            return await ctx.send("This user does not have any note")

        embed = discord.Embed(
            title=f"Note for `{member.display_name}`",
            description=f"{text[0]}",
            colour=discord.Colour.gold()
        )

        return await ctx.send(embed=embed)


    @note.command(name='add', description='Add note for specified user')
    async def add(self, ctx, member : discord.Member, *, text):

        await ctx.trigger_typing()

        if self.is_char_limited(text):
            raise CharacterLimited

        sql = 'INSERT INTO notes(user_id) VALUES (?)'
        sql2 = 'UPDATE notes set note = ? where user_id = ?'

        try:
            await self.bot.db.execute(sql, (member.id,))
            await self.bot.db.execute(sql2, (text, member.id))
            await self.bot.db.commit()

        except IntegrityError:
            raise NoteAlreadyExists


        else:

            embed = discord.Embed(
                title="Action Successful",
                description=f"Added Note for {member.mention}",
                colour=discord.Colour.green()
            )

            return await ctx.send(embed=embed)



    @note.command(name='remove', description='Remove note for specified user')
    async def remove(self, ctx, member : discord.Member):

        await ctx.trigger_typing()

        async with self.bot.db.execute('SELECT user_id from notes') as cursor:
            user_ids = await cursor.fetchall()

            if member.id not in [i[0] for i in user_ids]:
                raise MemberNotFound


        sql = 'DELETE FROM notes WHERE user_id=?'

        async with self.bot.db.execute(sql, (member.id,)) as cursor:
            await self.bot.db.commit()


        embed = discord.Embed(
            title="Action Successful",
            description=f"Removed Note for: {member.mention}",
            colour=discord.Colour.red()
        )

        return await ctx.send(embed=embed)


    @note.command(name='list', description='Lists all members which have notes')
    async def list(self, ctx):

        await ctx.trigger_typing()

        async with self.bot.db.execute('SELECT user_id FROM notes') as cursor:
            user_ids = await cursor.fetchall()

        member_list = [ctx.guild.get_member(i[0]) for i in user_ids]

        pages = menus.MenuPages(source=NotesMenu(member_list), clear_reactions_after=True)
        await pages.start(ctx)




    @note.command(name='append', description='Appends data to a pre-existing note')
    async def append(self, ctx, member : discord.Member, *, text):

        await ctx.trigger_typing()

        text = text.replace("{newline}","\n").replace("{space}", " ")




        async with self.bot.db.execute('SELECT note from notes WHERE user_id = (?)', (member.id,)) as cursor:
            data = await cursor.fetchone()


        if not data:
            raise MemberNotFound

        if self.is_char_limited(data[0] + text):
            raise CharacterLimited

        new_data = data[0] + text


        sql = 'UPDATE notes set note = ? where user_id = ?'

        await self.bot.db.execute(sql, (new_data,member.id))
        await self.bot.db.commit()


        embed = discord.Embed(
            title="Action Successful",
            description=f"Added new data for Note: {member.mention}",
            colour=discord.Colour.magenta()
        )

        return await ctx.send(embed=embed)








#Setup
def setup(bot):
    bot.add_cog(Commands(bot))