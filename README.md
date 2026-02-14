# MIRI Claude Code Plugins

A plugin marketplace for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) used at
the Machine Intelligence Research Institute.

## Prerequisites

Plugins may have their own prerequisites. See each plugin's README for details.

## Installation

### Via [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) CLI

```bash
claude /plugin marketplace add machine-intelligence/claude-code-plugins
claude /plugin install video-tools@miri-tools
```

### Via [Claude Desktop](https://claude.ai/download) App

1. Open Claude Desktop and click the **Code** tab
2. Open the sidebar (click the sidebar icon or press **Cmd + .**)
3. Click **Plugins** at the bottom of the sidebar
4. Click the **+** button, then **Browse plugins**
5. In the Browse plugins dialog, click the **By Anthropic** dropdown
6. Select **Add marketplace from GitHub**
7. Enter `machine-intelligence/claude-code-plugins` and click **Sync**
8. Switch to the new marketplace in the dropdown and install the plugins you want

### Alternative: Manual settings.json

For managed or automated setups, add to `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "miri-tools": {
      "source": {
        "source": "github",
        "repo": "machine-intelligence/claude-code-plugins"
      }
    }
  },
  "enabledPlugins": {
    "video-tools@miri-tools": true
  }
}
```

## Available Plugins

| Plugin                                | Description                                                    |
| ------------------------------------- | -------------------------------------------------------------- |
| [video-tools](./video-tools/)         | Tools for downloading and clipping videos from the internet    |

