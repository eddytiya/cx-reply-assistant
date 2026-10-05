from google import genai
from google.genai import errors, types

from app.config import settings


def test_generation():
    try:
        with genai.Client(
            api_key=settings.gemini_api_key.get_secret_value(),
            http_options=types.HttpOptions(timeout=30000),
        ) as client:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=(
                    "Write one short, polite customer-support sentence "
                    "asking for photos of a damaged bottle and its packaging. "
                    "Do not promise a refund or replacement."
                ),
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=200,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
                ),
            )

            text = response.text

            if not text or not text.strip():
                print("No text was returned. Generation is not verified.")
                return

            print("Generation successful.")
            print("Model:", settings.gemini_model)
            print("Response:", text.strip())

    except errors.APIError as error:
        print("Gemini rejected or failed the request.")
        print("HTTP status:", error.code)
        print("API message:", error.message)
        print("Check model access and quota in Google AI Studio.")

    except Exception as error:
        print("Generation check failed:", type(error).__name__)
        print("Check your connection and local configuration.")


if __name__ == "__main__":
    test_generation()