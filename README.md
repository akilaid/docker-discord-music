# Docker Music Container

This repository contains the Dockerfile and necessary configuration files to build and run a music container.

## Prerequisites

- Docker installed on your machine

## Getting Started

1. Pull this repository:

    ```bash
    docker pull akilaid/discord-music-bot
    ```
## Configuration

1. You need to create 'ezAdmin' role to give commands to music bot.
2. Create discord bot using [Discord Developer Portal](https://discord.com/developers/applications)
    ```
    https://discord.com/developers/applications
    ```
3. Turn on 'MESSAGE CONTENT INTENT' under Privileged Gateway Intents Section of bot. Required for your bot to receive message content in most messages.
4. Invite fresh bot to your Discord server [Invite Link](https://discord.com/oauth2/authorize?client_id=<your-bot-client-ID>&scope=bot&permissions=3222592)
    ```
    https://discord.com/oauth2/authorize?client_id=<your-bot-client-ID>&scope=bot&permissions=3222592
    ```


2. Run the Docker container:

    ```bash
    docker run -d --name my-disocrd-music-bot -e BOT_TOKEN=<your discord bot token> akilaid/discord-music-bot
    ```

## Usage

| Command | Description |
|---------|-------------|
| !play <youtube url>   | Play a song  |
| !pause  | Pause the currently playing song |
| !skip   | Skip to the next song |
| !stop   | Stop playing music |
| !clear   | Clear queued songs |

Also users can use UI buttons to control media while a song is playing.


## License

This project is licensed under the [MIT License](LICENSE).
