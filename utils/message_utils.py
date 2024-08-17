def handle_user_mentions(prompt, message):
  if "<@" in prompt:
    mentions = message.mentions
    for mention in mentions:
      user_id = mention.id
      username = mention.name
      prompt = prompt.replace(f"<@{user_id}>", f"{username}")
  return prompt
