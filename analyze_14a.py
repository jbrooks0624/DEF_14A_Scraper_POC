from dotenv import load_dotenv
import os
import asyncio
load_dotenv()
from openai import OpenAI, AsyncOpenAI

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(
    api_key=api_key,
)

async_client = AsyncOpenAI(
    api_key=api_key,
)

SYSTEM_PROMPT = """
You are a helpful assistant that analyzes 14a filings and provides a summary of the changes in control.

You will be given the text of a 14a filing, that has been filtered down to only the relevant sections.

You will need to analyze the text and provide the change in control payouts to executives and board members.

Please provide the following information:
    - The name of person
    - The amount of the payout

Please provide the information in the following JSON format:
```json
{
    "name": "John Doe",
    "amount": 100000
},
{
    "name": "Jane Doe",
    "amount": 200000
}
```
"""

def get_user_prompt(text):
    return f"""
    Given the following text, please analyze it and provide the change in control payouts to executives and board members.
    {text}
    """


async def analyze(text):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": get_user_prompt(text)}
    ]
    response = await async_client.responses.create(
        model="gpt-5-mini",
        input=messages,
    )
    return response.output_text


async def main():
    text = open("result.txt", "r").read()
    print(await analyze(text))

if __name__ == "__main__":
    asyncio.run(main())