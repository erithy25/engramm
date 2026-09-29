"""Requests ENGRAMM cannot carry out: alarms, music, smart home, sending messages, live data.

The counted intent classifier (engramm/nlp/intent.py, trained on MASSIVE) names the kind of
request; when it is one of these with a clear margin, ENGRAMM says honestly what it cannot do
(replies ``device.*`` in data/conv/replies.yaml) instead of searching its reading for an answer.
"""

from __future__ import annotations

from pathlib import Path

# MASSIVE intent → reply group; intents ENGRAMM can serve (qa_*, general_*, datetime_*, cooking…) are absent
GROUPS = {
    "alarm_query": "reminders", "alarm_remove": "reminders", "alarm_set": "reminders",
    "calendar_query": "reminders", "calendar_remove": "reminders", "calendar_set": "reminders",
    "lists_createoradd": "reminders", "lists_query": "reminders", "lists_remove": "reminders",
    "audio_volume_down": "media", "audio_volume_mute": "media", "audio_volume_other": "media",
    "audio_volume_up": "media", "music_dislikeness": "media", "music_likeness": "media", "music_settings": "media",
    "play_audiobook": "media", "play_game": "media", "play_music": "media", "play_podcasts": "media",
    "play_radio": "media",
    "iot_cleaning": "smarthome", "iot_coffee": "smarthome", "iot_hue_lightchange": "smarthome",
    "iot_hue_lightdim": "smarthome", "iot_hue_lightoff": "smarthome", "iot_hue_lighton": "smarthome",
    "iot_hue_lightup": "smarthome", "iot_wemo_off": "smarthome", "iot_wemo_on": "smarthome",
    "email_addcontact": "messages", "email_query": "messages", "email_querycontact": "messages",
    "email_sendemail": "messages", "social_post": "messages", "social_query": "messages",
    "news_query": "online", "weather_query": "online", "qa_stock": "online", "transport_query": "online",
    "transport_taxi": "online", "transport_ticket": "online", "transport_traffic": "online",
    "takeaway_order": "online", "takeaway_query": "online", "recommendation_events": "online",
}
MIN_MARGIN = 25.0         # score gap to the runner-up; set on MASSIVE dev and the team prompts (false hits scored 6–16, real commands 45–120)


class DeviceRequests:
    def __init__(self, model_path: Path):
        from engramm.nlp.intent import IntentClassifier
        self.clf = IntentClassifier.load(model_path)

    def group(self, text: str) -> tuple[str, str] | None:
        """(reply group, intent) when the message is a request ENGRAMM cannot carry out."""
        intent, margin = self.clf.predict(text)
        g = GROUPS.get(intent)
        return (g, intent) if g and margin >= MIN_MARGIN else None


def find_model(*dirs: Path | None) -> Path | None:
    for d in dirs:
        if d is not None and (Path(d) / "intent.json").exists():
            return Path(d) / "intent.json"
    return None
