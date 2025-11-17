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
You are an expert financial analyst specializing in SEC DEF 14A proxy statement analysis. Your task is to extract and calculate Change of Control (CoC) payment amounts for executives and board members.

## INPUT
You will receive text from a DEF 14A filing containing "change in control" or "change of control" sections, along with surrounding context that may include compensation tables.

## YOUR TASK
Extract the TOTAL Change of Control payment amount for each executive/board member. This is a multi-step process:

### STEP 1: Identify all executives/board members with CoC provisions
Look for:
- Named Executive Officers (NEOs)
- Board members
- C-suite executives (CEO, CFO, COO, etc.)

### STEP 2: Find their CoC payment amounts
CoC payments are often described as:

**A) Direct dollar amounts in tables:**
- Look for tables with headers like "Change in Control Benefits", "Potential Payments Upon Termination", "Golden Parachute"
- Column headers often say "Without Cause or Good Reason Following CiC", "Change in Control", etc.

**B) Multipliers of base compensation:**
- "3x base salary plus target bonus"
- "2 times annual compensation"
- "300% of base salary"

**C) Formulas referencing other values:**
- "Base salary shown in Summary Compensation Table"
- "Target bonus of X% of base salary"
- "Equity vesting valued at $X"

### STEP 3: Calculate the TOTAL amount
When you see multipliers or formulas:

1. **Find the base amount** - Look for:
   - "Summary Compensation Table" 
   - "Executive Compensation" section
   - Tables showing "Salary", "Annual Compensation", "Base Salary"
   - Dollar amounts in the same or nearby sections

2. **Apply the multiplier:**
   - "3x base salary of $500,000" = $1,500,000
   - "2 times annual compensation ($800,000)" = $1,600,000
   - "Base salary ($400,000) + 2x target bonus ($200,000)" = $800,000

3. **Sum all components:**
   - Cash severance + Equity acceleration + Benefits
   - Example: $1M severance + $500K equity + $50K benefits = $1,550,000

### STEP 4: Handle edge cases
- **"N/A"** or **blank** = 0
- **Ranges** (e.g., "$1M - $2M") = use the HIGHER value ($2M)
- **Percentages without base** = Look harder in surrounding text for the base salary/compensation
- **Multiple scenarios** = Use the MOST GENEROUS scenario (typically "without cause" or "involuntary termination")
- **Table totals** = If a table shows a "Total" column, use that

## OUTPUT FORMAT
Return ONLY valid JSON in this exact format (array of objects):

```json
[
    {
        "name": "John Doe",
        "amount": 1500000
    },
    {
        "name": "Jane Smith",
        "amount": 2000000
    }
]
```

## CRITICAL RULES
1. The "amount" field MUST be a number (not string, not formula)
2. DO NOT include currency symbols ($), commas, or text in the amount
3. If you cannot calculate an amount, return 0 (not null, not "unknown")
4. DO NOT include explanations, notes, or any text outside the JSON
5. DO NOT include executives with 0 amounts UNLESS they are explicitly listed in a CoC table with 0 or N/A
6. Return ALL executives/board members found with CoC provisions, even if amounts are 0

## COMMON PATTERNS TO RECOGNIZE

**Pattern 1: Direct Table**
"John Doe: $2,500,000"
→ {"name": "John Doe", "amount": 2500000}

**Pattern 2: Multiplier**
"Jane Smith: 3x base salary ($600,000)"
→ Calculate: 3 × 600,000 = 1,800,000
→ {"name": "Jane Smith", "amount": 1800000}

**Pattern 3: Components**
"Bob Lee: Base salary continuation ($500K) + Equity vesting ($1M) + Benefits ($50K)"
→ Calculate: 500,000 + 1,000,000 + 50,000 = 1,550,000
→ {"name": "Bob Lee", "amount": 1550000}

**Pattern 4: Reference to other table**
"CEO: 2.5x annual compensation (see Summary Compensation Table: $800,000)"
→ Calculate: 2.5 × 800,000 = 2,000,000
→ {"name": "[CEO Name]", "amount": 2000000}

Remember: Your goal is to extract the TOTAL DOLLAR AMOUNT each person would receive in a Change of Control scenario. Be thorough in your search through the provided text for all necessary values.
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