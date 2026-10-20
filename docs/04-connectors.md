# Connectors (MCP)

Connectors give Claude read/write access to your apps: Gmail, Google Drive/Docs/Sheets/Slides, Calendar, Slack, Notion, Jira, Linear, Asana, GitHub, HubSpot, Stripe, databases, and hundreds more via the **Model Context Protocol** (MCP). They work across the Claude app, desktop, mobile (install in beta), Claude Code, and the API (via the MCP connector).

## Set up

- Claude app → Connectors (hover in sidebar) → Manage / browse the directory → connect (OAuth). Each connector can be toggled per chat.
- **Custom connectors**: paste a remote MCP server URL. Available on all plans including free. They're unverified by Anthropic — treat as you would any third-party integration.
- **Claude Code**: `claude mcp add <name> <command-or-url>`; scopes: project, user, local.
- **Self-hosted / internal tools**: MCP tunnels let Claude reach servers inside your network without exposing them publicly.
- Docs: https://support.claude.com/en/articles/11176164 and https://platform.claude.com/docs/en/agents-and-tools/mcp-connector

## How Claude uses them (what to expect)

- Anything that's "yours" — *our Q3 deck, my calendar, the ticket* — Claude checks connected apps **before** the web.
- If you mention an app that isn't connected, Claude silently searches the connector registry and offers a one-click connect card. It won't refuse or ask "which app do you use?".
- When many connectors are on, tools load lazily, so a chat with 20 connectors isn't slower than one with 2.
- Consumer partner apps (shopping, bookings, media generation) are suggested, never called unprompted — you choose.
- Claude only sees content you have permission to see in the source app.

## Best practices

- Connect what you'll actually use; turn off per-chat connectors for unrelated work to keep Claude focused.
- For a **document/deck in Google or Notion**, say the app name: *"make a Google doc"*. Otherwise Claude makes its own Docs/Slides artifact.
- For *editing* a linked file, Claude needs a connector that can write to it; otherwise it hands you a Claude artifact with the changes and says which connection would let it edit in place.
- Browser automation is the fallback when no connector exists — Claude will log in and click through a flow instead of asking you to paste text.
- Scheduled tasks can use connectors (read Slack → create Linear issues).
- Prompt-injection awareness: content coming *out* of a connector (an email, a Jira comment) is data, not instructions. Claude is trained to treat it that way; you should too — ask for confirmation before Claude acts on instructions found inside a document.

## Lesser-known

- Claude can **build you an MCP server** for an internal API in a few minutes; then connect it as a custom connector.
- Voice mode can use connectors: *"what's on my calendar tomorrow, and reply to Sara's email that I'll be late."*
- In the app, Claude can also connect to **your device**: calendar, reminders, location, health data on mobile; files and shell on desktop (see [Hidden gems](00-hidden-gems.md)).
- Team/Enterprise admins control network access and which connectors are allowed (Admin settings → Capabilities).
- The API's **tool search** tool lets a single agent have thousands of MCP tools available and fetch definitions only when needed.
