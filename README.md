# AudioCodes Voice&#46;AI Gateway Channel for Rasa

AudioCodes Voice&#46;AI Gateway is an application that enables telephony access
for chatbots.

The Rasa integration is using a REST protocol named
[AC-Bot-API](https://www.audiocodes.com/media/14764/voiceai-gateway-bot-api-reference.pdf).

## Setting Credentials

In order to integrate with AudioCodes Voice&#46;AI Gateway, configure
a provider on VAIG side with the following attributes:

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

## Running on AudioCodes Voice.​AI Gateway

If you want to connect to the AudioCodes input channel using the run
script, e.g. using:

```bash
rasa run
```
you need to supply a `credentials.yml` with the following content:

```yaml
rasa_audiocodes.AudiocodesInput:
  token: "CHOOSE_YOUR_TOKEN"
```

## Installation

The easiest way to install the package is through [PyPI](https://pypi.org/project/rasa-audiocodes).

```sh
pip install rasa-audiocodes
```

## Docker

If you're using Rasa on Docker, you can copy rasa_audiocodes and docker-compose.yml
to your application directory, and edit the volumes section to match your app directory.

If you already have a docker-compose file, just add this to the rasa volumes:

```yaml
      - ./rasa_audiocodes:/opt/venv/lib/python3.7/site-packages/rasa_audiocodes
```
