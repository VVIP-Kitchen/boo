import io
import os
import base64

import torch
import runpod
import torch.nn.functional as F

from PIL import Image
from transformers import CLIPModel, CLIPProcessor

def get_best_device():
    if torch.cuda.is_available() and torch.version.cuda:  # extra sanity check
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

device = get_best_device()
print("Using device:", device)

MODEL_NAME = os.getenv("MODEL_NAME", "openai/clip-vit-base-patch32")
_model = CLIPModel.from_pretrained(MODEL_NAME).to(device)
_processor = CLIPProcessor.from_pretrained(MODEL_NAME)
_model.eval()

def handler(event):
    """
    Payload:
    {
        "input": {
            "text": "hi there!",
            "image": "data:image/png;base64,iVB....."
        }
    }
    """
    print("--- Boo image embeddings API ---")
    out = {}
    payload = event["input"]
    with torch.no_grad():
        if "text" in payload and payload["text"]:
            inputs = _processor(text=payload["text"], return_tensors="pt", padding=True)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            t = _model.get_text_features(**inputs)
            t = F.normalize(t, p=2, dim=-1)
            out["text"] = t[0].cpu().tolist()
        if "image" in payload and payload["image"]:
            b64 = payload["image"].split(",")[-1]
            img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
            inputs = _processor(images=img, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}
            i = _model.get_image_features(**inputs)
            i = F.normalize(i, p=2, dim=-1)
            out["image"] = i[0].cpu().tolist()
    return out

if __name__ == '__main__':
    runpod.serverless.start({'handler': handler })
