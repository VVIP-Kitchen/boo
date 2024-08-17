def replace_emojis(text, custom_emojis):
  words = text.split()
  for i, word in enumerate(words):
    if word.startswith(":") and word.endswith(":"):
      emoji_name = word[1:-1]
      if emoji_name in custom_emojis:
        words[i] = str(custom_emojis[emoji_name])
  return " ".join(words)
