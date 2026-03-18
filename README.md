# AudioCodes VoiceAI Connect Channel for Rasa

AudioCodes VoiceAI Connect is an application that enables telephony access
for chatbots.

The Rasa integration is using a REST protocol named
[AC-Bot-API](https://techdocs.audiocodes.com/voice-ai-gateway/api/version-180/#VAIG_API/API_1.htm).

## Installation

The easiest way to install the package is through [PyPI](https://pypi.org/project/rasa-audiocodes).

```sh
pip install rasa-audiocodes
```

## Rasa Configuration

Add the following content to `credentials.yml`:

```yaml
rasa_audiocodes.AudiocodesInput:
  token: "CHOOSE_YOUR_TOKEN"
```

## Docker

If you're using Rasa on Docker, you can install it from pip:

```yaml
RUN pip install "rasa-audiocodes>=1.0.0"
```
## VoiceAI Connect Cloud Setup

The easiest way to start using VAIC is by visiting https://livehub.audiocodes.io.

You can get a phone number, and route it to your bot.

Configuration is straight-forward. Click the + sign, then enter the name
of the bot, URL and the token.

You can now click Validate to verify that the bot is accessible and the
audiocodes channel is configured correctly.

![PNC Configuration](doc/pnc.png)

Click Next, then choose a country and a city to get a phone number.

After a minute, the number should be routed to your bot.

## VoiceAI Connect Configuration

If you maintain a VAIC instance, configure a provider with the following attributes:

```json
  {
    "name": "rasa",
    "type": "ac-bot-api",
    "botURL": "https://<RASA>/webhooks/audiocodes/webhook",
    "credentials": {
      "token": "CHOOSE_YOUR_TOKEN"
    }
  }
```
