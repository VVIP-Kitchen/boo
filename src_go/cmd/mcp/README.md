# MCP Server for Boo Services

This is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes Boo's services as tools for AI assistants like Claude, VS Code Copilot, and other MCP-compatible hosts.

## Available Tools

### 1. `tenor_search`

Search for GIFs on Tenor.

**Arguments:**

- `query` (required): The search query to find GIFs

**Returns:** A URL to a random GIF matching the search query

### 2. `weather`

Get current weather information for a location.

**Arguments:**

- `location` (required): The location to get weather for (city name or coordinates)

**Returns:** Detailed weather data including temperature, humidity, wind, and conditions

## Building

From the `src_go` directory:

```bash
go build -o mcp-server ./cmd/mcp
```

Or on Windows:

```powershell
go build -o mcp-server.exe ./cmd/mcp
```

## Configuration

### Environment Variables

The server requires the following environment variables:

- `TENOR_API_KEY`: Your Tenor API key for GIF search
- `TOMORROW_IO_API_KEY`: Your Tomorrow.io API key for weather data

You can set these in a `.env` file in the working directory.

### Claude Desktop

Add the following to your `claude_desktop_config.json`:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "boo-services": {
      "command": "/path/to/mcp-server",
      "args": [],
      "env": {
        "TENOR_API_KEY": "your-tenor-api-key",
        "TOMORROW_IO_API_KEY": "your-tomorrow-io-api-key"
      }
    }
  }
}
```

### VS Code (GitHub Copilot)

Add to your VS Code `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "boo-services": {
        "command": "/path/to/mcp-server",
        "env": {
          "TENOR_API_KEY": "your-tenor-api-key",
          "TOMORROW_IO_API_KEY": "your-tomorrow-io-api-key"
        }
      }
    }
  }
}
```

## Usage Examples

Once configured, you can ask your AI assistant:

- "Search for a funny cat GIF"
- "What's the weather like in Tokyo?"
- "Find me a dancing GIF and tell me the weather in Paris"

## Adding More Services

To add more services to the MCP server:

1. Import the service package
2. Initialize the service in `main()`
3. Register a new tool using `server.RegisterTool()`

Example:

```go
err = server.RegisterTool(
    "new_service",
    "Description of what the service does",
    func(arguments NewServiceArguments) (*mcp_golang.ToolResponse, error) {
        // Your service logic here
        result := myService.DoSomething(arguments.Param)
        return mcp_golang.NewToolResponse(mcp_golang.NewTextContent(result)), nil
    },
)
```
