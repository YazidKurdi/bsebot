import discord
from discordbot.slashcommandeventclasses import BSEddiesCreateBet, BSEddiesPlaceBet, BSEddiesCloseBet


class BSEddiesBetCreateModal(discord.ui.Modal):
    def __init__(self, client, guilds, logger, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.logger = logger

        self.bseddies_create = BSEddiesCreateBet(client, guilds, logger)
        self.bseddies_place = BSEddiesPlaceBet(client, guilds, logger)
        self.bseddies_close = BSEddiesCloseBet(client, guilds, logger)

        self.add_item(discord.ui.InputText(label="Bet title", placeholder="Enter your bet title here"))
        self.add_item(
            discord.ui.InputText(
                label="Enter the bet outcomes on separate lines",
                placeholder="Outcome 1...\nOutcome 2...\nOutcome 3...\nOutcome 4...\netc, etc...",
                style=discord.InputTextStyle.long
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Timeout: DIGITS + (s|m|h|d) (Optional)",
                required=False,
                placeholder="Examples: 25m, 2d, 8h, etc..."
            )
        )

    async def callback(self, interaction: discord.Interaction):
        """

        :param interaction:
        :return:
        """

        response_components = interaction.data["components"]
        bet_title_comp = response_components[0]
        bet_title = bet_title_comp["components"][0]["value"]

        bet_outcomes_comp = response_components[1]
        bet_outcomes = bet_outcomes_comp["components"][0]["value"].split("\n")

        bet_timeout_comp = response_components[2]
        bet_timeout = bet_timeout_comp["components"][0]["value"] or "20m"

        self.logger.info(f"{bet_title}, {bet_outcomes}")

        if len(bet_outcomes) > 8:
            await interaction.response.send_message(
                content="You have provided too many outcomes - please provide 8 or less.",
                ephemeral=True
            )
            return

        elif len(bet_outcomes) < 2:
            await interaction.response.send_message(
                content="You have provided too few outcomes - please provide at least 2.",
                ephemeral=True
            )
            return

        await self.bseddies_create.handle_bet_creation(
            interaction,
            bet_title,
            *bet_outcomes,
            timeout_str=bet_timeout.lower(),
            autogenerated=False,
            bseddies_place=self.bseddies_place,
            bseddies_close=self.bseddies_close
        )
