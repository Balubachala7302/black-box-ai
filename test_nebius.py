import os

from dotenv import load_dotenv
from openai import OpenAI
from openai import APIError, AuthenticationError, RateLimitError

# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

api_key = os.getenv("NEBIUS_API_KEY")

if not api_key:
    raise ValueError(
        "NEBIUS_API_KEY not found. Check your .env file."
    )


# ============================================================
# 2. CONNECT TO NEBIUS TOKEN FACTORY
# ============================================================

client = OpenAI(
    api_key=api_key,
    base_url="https://api.tokenfactory.nebius.com/v1/",
    timeout=30.0,
    max_retries=0,
)


# ============================================================
# 3. TEST NVIDIA NEMOTRON
# ============================================================

def main():
    print("=" * 55)
    print("       AI INCIDENT COMMANDER - API CONNECTION TEST")
    print("=" * 55)

    print("\nConnecting to NVIDIA Nemotron...")

    try:
        response = client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise AI assistant helping "
                        "developers investigate software incidents."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "A Python API's error rate suddenly increased "
                        "after a deployment. Give two possible causes "
                        "and one diagnostic step. Keep your answer "
                        "under 80 words."
                    ),
                },
            ],
            max_tokens=250,
        )

        # ----------------------------------------------------
        # 4. INSPECT THE RESPONSE
        # ----------------------------------------------------

        print("\nAPI request completed successfully.")

        print("\n--- RESPONSE DETAILS ---")
        print("Model:", response.model)
        print("Finish reason:", response.choices[0].finish_reason)

        message = response.choices[0].message

        print("\n--- MESSAGE ---")
        print(repr(message))

        print("\n--- NVIDIA NEMOTRON RESPONSE ---")

        if message.content:
            print(message.content)
        else:
            print("No text content was returned.")
            print(
                "Inspect the message details above to determine "
                "what the model returned."
            )

        print("\n--- TOKEN USAGE ---")

        if response.usage:
            print("Input tokens:", response.usage.prompt_tokens)
            print("Output tokens:", response.usage.completion_tokens)
            print("Total tokens:", response.usage.total_tokens)
        else:
            print("Token usage information was not provided.")

    except AuthenticationError:
        print("\nAuthentication failed.")
        print(
            "Check whether your Nebius API key is correct, "
            "active, and associated with the appropriate project."
        )

    except RateLimitError as error:
        print("\nRate limit or quota error.")
        print("Error type:", type(error).__name__)
        print("Details:", str(error))

    except APIError as error:
        print("\nNebius API returned an error.")
        print("HTTP status:", error.status_code)
        print("Error type:", type(error).__name__)
        print("Details:", str(error))

    except Exception as error:
        print("\nUnexpected error occurred.")
        print("Error type:", type(error).__name__)
        print("Details:", str(error))

    finally:
        client.close()




if __name__ == "__main__":
    main()