package handlers

import "github.com/bwmarrin/discordgo"

var Commands = []*discordgo.ApplicationCommand{
	{
		Name:        "ping",
		Description: "Replies with Pong!",
	},
	{
		Name:        "ping_admin",
		Description: "Admin-only ping command",
	},
}

func SlashCommands(discord *discordgo.Session, interaction *discordgo.InteractionCreate) {
	// Ping Command Handler
	if interaction.Type == discordgo.InteractionApplicationCommand {
		switch interaction.ApplicationCommandData().Name {
		case "ping":
			pingCommandHandler(discord, interaction)
		case "ping_admin":
			pingAdminCommandHandler(discord, interaction)
		}
	}
}

func pingCommandHandler(discord *discordgo.Session, interaction *discordgo.InteractionCreate) {
	discord.InteractionRespond(interaction.Interaction, &discordgo.InteractionResponse{
		Type: discordgo.InteractionResponseChannelMessageWithSource,
		Data: &discordgo.InteractionResponseData{
			Content: "Pong!",
		},
	})
}

func pingAdminCommandHandler(discord *discordgo.Session, interaction *discordgo.InteractionCreate) {
	// Checking if the user has admin privileges or a specific role with the name "boo manager"
	member, err := discord.GuildMember(interaction.GuildID, interaction.Member.User.ID)
	if err != nil {
		discord.InteractionRespond(interaction.Interaction, &discordgo.InteractionResponse{
			Type: discordgo.InteractionResponseChannelMessageWithSource,
			Data: &discordgo.InteractionResponseData{
				Content: "Error fetching member information.",
			},
		})
		return
	}

	isAdmin := false
	for _, roleID := range member.Roles {
		role, err := discord.State.Role(interaction.GuildID, roleID)
		if err == nil && (role.Permissions&discordgo.PermissionAdministrator != 0 || role.Name == "boo manager") {
			isAdmin = true
			break
		}
	}
	if !isAdmin {
		discord.InteractionRespond(interaction.Interaction, &discordgo.InteractionResponse{
			Type: discordgo.InteractionResponseChannelMessageWithSource,
			Data: &discordgo.InteractionResponseData{
				Content: "You do not have permission to use this command.",
			},
		})
		return
	}

	pingCommandHandler(discord, interaction)
}
