import logging
from sanic import Blueprint, response
from sanic.request import Request
import datetime
import uuid
from typing import Text, List, Dict, Any, Callable, Awaitable, Iterable, Optional
import sanic
import json
from sanic.response import HTTPResponse
from rasa.core import jobs
from rasa.core.constants import INTENT_MESSAGE_PREFIX
from rasa.core.channels.channel import UserMessage, OutputChannel, InputChannel

logger = logging.getLogger(__name__)

CHANNEL_NAME = "audiocodes"
KEEP_ALIVE_SECONDS = "120"


class AudiocodesInput(InputChannel):
    class Conversation:
        def __init__(self, cid):
            self.activityIds = []
            self.ws = None
            self.cid = cid
            self.update()

        def update(self):
            self.lastActivity = datetime.datetime.utcnow()

        @staticmethod
        def get_metadata(activity: Dict[Text, Any]) -> Optional[Dict[Text, Any]]:
            return activity.get("parameters")

        @staticmethod
        def _handle_event(event: Dict[Text, Any]) -> Text:
            text = f'{INTENT_MESSAGE_PREFIX}vaig_event_{event["name"]}'
            event_params = {}
            if "parameters" in event:
                event_params.update(event["parameters"])
            if "value" in event:
                event_params.update({"value": event["value"]})
            if len(event_params) > 0:
                text += json.dumps(event_params)
            return text

        def is_valid(self, now, delta) -> bool:
            if now - self.lastActivity > delta:
                logger.warning(f"Conversation {self.cid} is invalid due to inactivity")
                return False
            return True

        async def handle_activities(
            self,
            message: Dict[Text, Any],
            output_channel: OutputChannel,
            on_new_message: Callable[[UserMessage], Awaitable[Any]],
        ) -> None:
            logger.debug(f"(handle_activities) --- Activities:")
            logger.debug(message)
            for activity in message["activities"]:
                text = None
                if activity["id"] in self.activityIds:
                    logger.warning(
                        f'Got activity that already handled. Activity ID: {activity["id"]}'
                    )
                    continue
                self.activityIds.append(activity["id"])
                if activity["type"] == "message":
                    text = activity["text"]
                elif activity["type"] == "event":
                    text = self._handle_event(activity)
                else:
                    logger.warning(
                        "Received an activity from audiocodes that we can not "
                        f"handle. Activity: {activity}"
                    )
                if not text:
                    continue
                metadata = self.get_metadata(activity)
                user_msg = UserMessage(
                    text=text,
                    output_channel=output_channel,
                    sender_id=self.cid,
                    metadata=metadata,
                )
                try:
                    await on_new_message(user_msg)
                except Exception as e:  # skipcq: PYL-W0703
                    logger.exception(
                        f"Exception occurred during handled audiocodes message: {user_msg}. {e}"
                    )
                    logger.debug(e, exc_info=True)
                    await output_channel.send_custom_json(
                        self.cid,
                        {
                            "type": "event",
                            "name": "hangup",
                            "text": "Exception occurred during handled last message",
                        },
                    )

    @classmethod
    def name(cls) -> Text:
        return CHANNEL_NAME

    @classmethod
    def from_credentials(
        cls, credentials: Optional[Dict[Text, Any]]
    ) -> Optional[InputChannel]:
        if not credentials:
            cls.raise_missing_credentials_exception()
            return None
        return cls(credentials.get("token"), credentials.get("websocket_is_on"), credentials.get("keep_alive"))

    def __init__(self, token: Text, websocket_is_on: bool, keep_alive: Optional[Text]) -> None:
        self.conversations = {}
        self.token = token
        self.websocket_is_on = websocket_is_on
        self.scheduler_job = None
        self.keep_alive = int(keep_alive or KEEP_ALIVE_SECONDS)

    async def _set_scheduler_job(self) -> None:
        if self.scheduler_job:
            self.scheduler_job.remove()
        self.scheduler_job = (await jobs.scheduler()).add_job(
            self.clean_old_conversations, "interval", minutes=10
        )

    def _check_token(self, token: Optional[Text]) -> None:
        if not token or not token.replace("Bearer ", "") == self.token:
            sanic.exceptions.abort(401)

    def _get_conversation(
        self, token: Optional["Text"], cid: Text
    ) -> Optional["Conversation"]:
        self._check_token(token)
        conversation = self.conversations.get(cid)
        if not conversation:
            sanic.exceptions.abort(404, "Not found")
            return None
        conversation.update()
        return conversation

    def clean_old_conversations(self) -> None:
        logger.debug(
            f"Performing clean old conversations, current number: {len(self.conversations)}"
        )
        now = datetime.datetime.utcnow()
        delta = datetime.timedelta(seconds=self.keep_alive * 1.5)
        self.conversations = {
            k: v for k, v in self.conversations.items() if v.is_valid(now, delta)
        }

    def handle_start_conversation(self, body: Dict[Text, Any]) -> Dict[Text, Any]:
        cid = body["conversation"]
        if cid in self.conversations:
            sanic.exceptions.abort(500, "Conversation already exists")
        logger.debug(f"(handle_start_conversation) --- New Conversation has arrived. Conversation: {cid}")
        self.conversations[cid] = AudiocodesInput.Conversation(cid)
        urls = {
            "activitiesURL": f"/webhooks/audiocodes/conversation/{cid}/activities",
            "disconnectURL": f"/webhooks/audiocodes/conversation/{cid}/disconnect",
            "refreshURL": f"/webhooks/audiocodes/conversation/{cid}/keepalive",
            "expiresSeconds": self.keep_alive,
        }
        if self.websocket_is_on:
            urls.update({"websocketURL": f"/webhooks/audiocodes/conversation/{cid}/websocket"}) 
        return urls


    def blueprint(
        self, on_new_message: Callable[[UserMessage], Awaitable[Any]]
    ) -> Blueprint:
        ac_webhook = Blueprint("ac_webhook", __name__)

        @ac_webhook.websocket('/conversation/<cid>/websocket')
        async def new_client_connection(request, ws, cid: Text):
            if self.websocket_is_on is False:
               raise ConnectionRefusedError('websocket is unavailable')
            logger.debug(f"(new_client_connection) --- New client is trying to connect. Conversation: {cid}")
            conversation = self._get_conversation(request.headers.get("Authorization"), cid)
            if conversation.ws is not None:
                logger.debug(f"(new_client_connection) --- The client was already connected. Conversation: {cid}")
                return
            conversation.ws = ws

            try:
                await ws.recv()
            except:
                logger.debug(f"(new_client_connection) --- Websocket was closed by client: {cid}")
                conversation.ws = None


        @ac_webhook.route("/", methods=["GET"])
        async def health(request: Request) -> HTTPResponse:
            return response.json({"status": "ok"})

        # {"conversation": <cid>, id, timestamp}
        @ac_webhook.route("/webhook", methods=["GET", "POST"])
        async def receive(request: Request) -> HTTPResponse:
            if not self.scheduler_job:
                await self._set_scheduler_job()
            self._check_token(request.headers.get("Authorization"))
            if request.method == 'GET':
                return response.json({
                    "type": "ac-bot-api",
                    "success": True
                })
            return response.json(self.handle_start_conversation(request.json))

        # {"conversation": <cid>, "activities": List[Activity]}
        @ac_webhook.route("/conversation/<cid>/activities", methods=["POST"])
        async def on_activities(request: Request, cid: Text) -> HTTPResponse:
            logger.debug(f"(on_activities) --- New activities from the user. Conversation: {cid}")
            conversation = self._get_conversation(
                request.headers.get("Authorization"), cid
            )
            ac_output = WebsocketOutput(conversation.ws, cid) if conversation.ws is not None else AudiocodesOutput()
            await conversation.handle_activities(
                request.json, output_channel=ac_output, on_new_message=on_new_message,
            )
            if conversation.ws is None:
                return response.json(
                    {"conversation": cid, "activities": ac_output.messages}
                )

            return response.json({})

        # {"conversation": <cid>, "reason": Optional[Text]}
        @ac_webhook.route("/conversation/<cid>/disconnect", methods=["POST"])
        async def disconnect(request: Request, cid: Text) -> HTTPResponse:
            self._get_conversation(request.headers.get("Authorization"), cid)
            reason = str({"reason": request.json.get("reason")})
            await on_new_message(
                UserMessage(text=f"{INTENT_MESSAGE_PREFIX}vaig_event_end{reason}", output_channel=None, sender_id=cid)
            )
            del self.conversations[cid]
            logger.debug(f"(disconnect) --- Conversation was deleted")
            return response.json({})

        # {"conversation": <cid>}
        @ac_webhook.route("/conversation/<cid>/keepalive", methods=["POST"])
        async def keepalive(request: Request, cid: Text) -> HTTPResponse:
            self._get_conversation(request.headers.get("Authorization"), cid)
            return response.json({})

        return ac_webhook


class AudiocodesOutput(OutputChannel):
    @classmethod
    def name(cls) -> Text:
        return CHANNEL_NAME

    def __init__(self) -> None:
        self.messages = []

    async def add_message(self, message) -> None:
        logger.debug(f"{self.__class__.__name__}::add_message --- message: {message}")
        message.update(
            {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.datetime.utcnow().isoformat("T")[:-3] + "Z",
            }
        )
        await self.do_add_message(message)

    async def do_add_message(self, message) -> None:
        self.messages.append(message)

    async def send_text_message(
        self, recipient_id: Text, text: Text, **kwargs: Any
    ) -> None:
        await self.add_message({ "type": "message", "text": text })

    async def send_image_url(
        self, recipient_id: Text, image: Text, **kwargs: Any
    ) -> None:
        raise NotImplementedError()

    async def send_attachment(
        self, recipient_id: Text, attachment: Text, **kwargs: Any
    ) -> None:
        raise NotImplementedError()

    async def send_custom_json(
        self, recipient_id: Text, json_message: Dict[Text, Any], **kwargs: Any
    ) -> None:
        await self.add_message(json_message)


class WebsocketOutput(AudiocodesOutput):
    def __init__(self, ws, cid) -> None:
        self.ws = ws
        self.cid = cid

    async def do_add_message(self, message) -> None:
        await self.ws.send(json.dumps({ "conversation": self.cid, "activities": [message] }))
