from together import Together
import os

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
ai_features_enabled = bool(TOGETHER_API_KEY)

# client = Together(api_key=TOGETHER_API_KEY)
client = Together()

# List all available models
models = client.models.list()

# print(f"models = {models}")

# Filter for a specific image model to see its config
image_models = [m for m in models if m.type == "image"]

for model in image_models:
    print(f'("{model.display_name}", "{model.id}"),')
    # Attributes like 'config' often contain parameter limits (e.g., max_steps)
    # print(f"Capabilities: {model.config}")
    # print(f"model = {model}")
