
import discord

from discordbot.selects import BetSelect, BetOutcomesSelect


class CloseABetView(discord.ui.View):
    def __init__(self, bet_ids: list, submit_callback: callable):
        super().__init__(timeout=60)
        self.add_item(BetSelect(bet_ids))

        if len(bet_ids) == 1 and "option_dict" in bet_ids[0]:
            outcomes = bet_ids[0]["option_dict"]
            options = [
                discord.SelectOption(
                    label=outcomes[key]["val"],
                    value=key,
                    emoji=key
                ) for key in outcomes
            ]
        else:
            options = []

        self.add_item(BetOutcomesSelect(options, discord.ui.Button))
        self.submit_callback = submit_callback

    @discord.ui.button(label="Submit", style=discord.ButtonStyle.green, row=2, disabled=True)
    async def submit_callback(self, button: discord.ui.Button, interaction: discord.Interaction):

        data = {}
        for child in self.children:
            if type(child) == BetSelect:
                try:
                    data["bet_id"] = child.values[0]
                except IndexError:
                    # this means that this was default
                    data["bet_id"] = child.options[0].value
            elif type(child) == BetOutcomesSelect:
                data["emoji"] = child.values[0]

        # call the callback that actually places the bet
        await self.submit_callback(
            interaction,
            data["bet_id"],
            data["emoji"]
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, row=2, disabled=False, emoji="✖️")
    async def cancel_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.edit_message(content="Cancelled", view=None)
