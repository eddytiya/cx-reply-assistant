from google import genai

from app.config import settings


def check_connection():
    with genai.Client(
        api_key=settings.gemini_api_key.get_secret_value(),
    ) as client:
        models = client.models.list()

        print("Models supporting content generation:")

        for model in models:
            actions = model.supported_actions or []

            if "generateContent" in actions:
                print(model.name)


if __name__ == "__main__":
    check_connection()