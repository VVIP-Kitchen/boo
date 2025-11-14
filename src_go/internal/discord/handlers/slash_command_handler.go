package handlers

import (
	"boo/internal/services/db"
	"io"

	"github.com/bwmarrin/discordgo"
)

var Commands = []*discordgo.ApplicationCommand{
	{
		Name:        "ping",
		Description: "Replies with Pong!",
	},
	{
		Name:        "ping_admin",
		Description: "Admin-only ping command",
	},
	{
		Name:        "update_system_prompt",
		Description: "Update the system prompt for the guild",
		Options: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "prompt",
				Description: "The new system prompt",
				Required:    true,
			},
		},
	},
	{
		Name:        "add_system_prompt",
		Description: "Add a system prompt for the guild",
		Options: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionAttachment,
				Name:        "prompt_file",
				Description: "The system prompt file (.txt or .md)",
				Required:    true,
			},
		},
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
		case "update_system_prompt":
			updateGuildSystemPrompt(discord, interaction)
		case "add_system_prompt":
			addGuildSystemPrompt(discord, interaction)
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

func updateGuildSystemPrompt(discord *discordgo.Session, interaction *discordgo.InteractionCreate) {
	// getting the system prompt file from the interaction options
	options := interaction.ApplicationCommandData().Options
	if len(options) == 0 {
		discord.InteractionRespond(interaction.Interaction, &discordgo.InteractionResponse{
			Type: discordgo.InteractionResponseChannelMessageWithSource,
			Data: &discordgo.InteractionResponseData{
				Content: "No system prompt provided.",
			},
		})
		return
	}
	systemPrompt := options[0].StringValue()
	err := db.GetDBService().UpdatePrompt(interaction.GuildID, systemPrompt)
	if err != nil {
		discord.InteractionRespond(interaction.Interaction, &discordgo.InteractionResponse{
			Type: discordgo.InteractionResponseChannelMessageWithSource,
			Data: &discordgo.InteractionResponseData{
				Content: "Error updating system prompt: " + err.Error(),
			},
		})
		return
	}
	discord.InteractionRespond(interaction.Interaction, &discordgo.InteractionResponse{
		Type: discordgo.InteractionResponseChannelMessageWithSource,
		Data: &discordgo.InteractionResponseData{
			Content: "System prompt updated successfully.",
		},
	})
}

func addGuildSystemPrompt(discord *discordgo.Session, interaction *discordgo.InteractionCreate) {
	// getting the system prompt file .txt or .md from the interaction options
	options := interaction.ApplicationCommandData().Options
	if len(options) == 0 {
		discord.InteractionRespond(interaction.Interaction, &discordgo.InteractionResponse{
			Type: discordgo.InteractionResponseChannelMessageWithSource,
			Data: &discordgo.InteractionResponseData{
				Content: "No system prompt file provided.",
			},
		})
		return
	}

	// Downloading the file
	attachmentID := options[0].Value.(string)
	attachmentURL := interaction.ApplicationCommandData().Resolved.Attachments[attachmentID].URL

	resp, err := discord.Client.Get(attachmentURL)
	if err != nil {
		discord.InteractionRespond(interaction.Interaction, &discordgo.InteractionResponse{
			Type: discordgo.InteractionResponseChannelMessageWithSource,
			Data: &discordgo.InteractionResponseData{
				Content: "Error downloading system prompt file: " + err.Error(),
			},
		})
		return
	}
	defer resp.Body.Close()
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		discord.InteractionRespond(interaction.Interaction, &discordgo.InteractionResponse{
			Type: discordgo.InteractionResponseChannelMessageWithSource,
			Data: &discordgo.InteractionResponseData{
				Content: "Error reading system prompt file: " + err.Error(),
			},
		})
		return
	}
	systemPrompt := string(bodyBytes)

	err = db.GetDBService().AddPrompt(interaction.GuildID, systemPrompt)
	if err != nil {
		discord.InteractionRespond(interaction.Interaction, &discordgo.InteractionResponse{
			Type: discordgo.InteractionResponseChannelMessageWithSource,
			Data: &discordgo.InteractionResponseData{
				Content: "Error adding system prompt: " + err.Error(),
			},
		})
		return
	}

	discord.InteractionRespond(interaction.Interaction, &discordgo.InteractionResponse{
		Type: discordgo.InteractionResponseChannelMessageWithSource,
		Data: &discordgo.InteractionResponseData{
			Content: "System prompt added successfully.",
		},
	})
}
