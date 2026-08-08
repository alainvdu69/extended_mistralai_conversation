"""Constants for the Extended Mistral AI Conversation integration."""
DOMAIN = "extended_mistralai_conversation"
DEFAULT_NAME = "Extended Mistral AI Conversation"
DEFAULT_MODEL = "mistral-medium"
DEFAULT_TOOLS_CONFIG_PATH = "config/mistral_tools.yaml"
DEFAULT_PROMPT_PATH = "config/mistral_prompt.txt"
DEFAULT_ALLOWED_DOMAINS = ["light", "cover", "script", "media_player"]
DEFAULT_ALLOWED_SERVICES = {
    "light": ["turn_on", "turn_off", "toggle"],
    "cover": ["open_cover", "close_cover", "set_cover_position"],
    "script": ["turn_on", "turn_off", "assist_timer", "extinction_musique"],
    "media_player": ["volume_set", "media_play_pause", "turn_on", "turn_off"],
}