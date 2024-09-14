import os
import re
import json
import time
import random

from tqdm import tqdm
from openai import OpenAI, RateLimitError

token = os.environ["GITHUB_TOKEN"]
endpoint = "https://models.inference.ai.azure.com"

client = OpenAI(
  base_url=endpoint,
  api_key=token,
)


def preprocess_markdown(file_path):
  with open(file_path, "r", encoding="utf-8") as file:
    content = file.read()

  cleaned = re.sub(r"[*#_`]", "", content)
  cleaned = re.sub(r"\s+", " ", cleaned).strip()
  return cleaned


def split_into_chunks(text, chunk_size=1000):
  return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def generate_instruction_response_pairs(chunk, max_retries=5, model="gpt-4o-mini", temperature=0.7):
  prompt = f"""
Given the following text, create 3 instruction-response pairs suitable for fine-tuning an AI model.
Each pair should consist of an instruction, an optional context, and a response.
The pairs should be diverse and cover different aspects of the text.

Text:
{chunk}

Output the pairs in the following JSON format:
[
    {{
        "instruction": "REQUIRED",
        "context": "OPTIONAL (can be null if not applicable)",
        "response": "REQUIRED"
    }},
    {{
        "instruction": "REQUIRED",
        "context": "OPTIONAL (can be null if not applicable)",
        "response": "REQUIRED"
    }},
    {{
        "instruction": "REQUIRED",
        "context": "OPTIONAL (can be null if not applicable)",
        "response": "REQUIRED"
    }}
]

Ensure that the "instruction" and "response" fields are always filled, and use the "context" field when additional background information is helpful.
"""

  for attempt in range(max_retries):
    try:
      response = client.chat.completions.create(
        model=model,
        messages=[
          {
            "role": "system",
            "content": "You are an AI assistant that creates instruction-response pairs with optional context from given text.",
          },
          {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=1000,
      )

      content = response.choices[0].message.content
      content = re.sub(r"^```json\s*|\s*```$", "", content.strip())

      return json.loads(content)

    except RateLimitError as e:
      if attempt < max_retries - 1:
        wait_time = (2**attempt) + random.random()
        print(
          f"Rate limit reached. Waiting for {wait_time:.2f} seconds before retrying..."
        )
        time.sleep(wait_time)
      else:
        print(f"Max retries reached. Skipping this chunk.")
        return []

    except json.JSONDecodeError as e:
      print(f"Error parsing JSON: {e}")
      print(f"Problematic content:\n{content}")
      return []

    except Exception as e:
      print(f"An unexpected error occurred: {e}")
      return []


def main(markdown_file_path, output_file_path):
  print("Preprocessing markdown file...")
  cleaned_text = preprocess_markdown(markdown_file_path)

  chunks = split_into_chunks(cleaned_text)

  print("Generating instruction-response pairs...")
  total_pairs = 0

  with open(output_file_path, "w", encoding="utf-8") as f:
    f.write("[\n")

    for i, chunk in enumerate(tqdm(chunks, desc="Processing chunks", unit="chunk")):
      pairs = generate_instruction_response_pairs(chunk)
      total_pairs += len(pairs)

      for pair in pairs:
        json.dump(pair, f, ensure_ascii=False, indent=2)
        if i < len(chunks) - 1 or pair != pairs[-1]:
          f.write(",\n")
        else:
          f.write("\n")

      f.flush()

    f.write("]\n")

  print(f"Created {total_pairs} instruction-response pairs.")


if __name__ == "__main__":
  markdown_file = "./raw/grading_doc.md"
  output_file = "./processed/instruction_dataset.json"
  main(markdown_file, output_file)
