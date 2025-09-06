import io
import base64
from typing import List, Optional

import modal
import torch
from PIL import Image
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, util
from fastapi import FastAPI, HTTPException, File, UploadFile

### Setup
image = modal.Image.debian_slim().uv_pip_install(
    "torch",
    "numpy",
    "Pillow",
    "torchvision",
    "fastapi[standard]",
    "sentence-transformers"
)
app = modal.App("boo-embeddings-api", image=image)

### Pydantic models
class TextEmbeddingRequest(BaseModel):
    text: str

class TextBatchEmbeddingRequest(BaseModel):
    texts: List[str]

class ImageEmbeddingRequest(BaseModel):
    image_base64: str

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    dimension: int

class BatchEmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    dimension: int
    count: int

### FastAPI setup
web_app = FastAPI(
    title="Boo text + image embeddings API",
    description="Text and Image embeddings using CLIP ViT-B-32",
    version="0.1.0"
)

### Load model to this global variable on app startup
model = None

def get_model():
    global model
    if model is None:
        print("Loading CLIP model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = SentenceTransformer("clip-ViT-B-32", device=device)
        print("CLIP model loaded on device {device}")
    return model

@web_app.get("/")
async def root():
    return {
        "message": "Boo text + image embeddings API",
        "model": "clip-ViT-B-32",
        "endpoints": {
            "text": "/embed/text",
            "text_batch": "/embed/text/batch",
            "image": "/embed/image",
            "image_upload": "/embed/image/upload"
        }
    }

@web_app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None
    }

@web_app.post("/embed/text", response_model=EmbeddingResponse)
async def embed_text(request: TextEmbeddingRequest):
    try:
        model_instance = get_model()
        embedding = model_instance.encode(request.text)
        return EmbeddingResponse(
            embedding=embedding.tolist(),
            dimension=len(embedding)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embedding: {str(e)}")

@web_app.post("/embed/text/batch", response_model=BatchEmbeddingResponse)
async def embed_text_batch(request: TextBatchEmbeddingRequest):
    try:
        model_instance = get_model()
        embeddings = model_instance.encode(request.texts)
        return BatchEmbeddingResponse(
            embeddings=embeddings.tolist(),
            dimension=len(embeddings[0]) if len(embeddings) > 0 else 0,
            count=len(embeddings)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embeddings: {str(e)}")

@web_app.post("/embed/image", response_model=EmbeddingResponse)
async def embed_image(request: ImageEmbeddingRequest):
    try:
        model_instance = get_model()
        image_data = base64.b64decode(request.image_base64)
        image = Image.open(io.BytesIO(image_data)).convert('RGB')
        embedding = model_instance.encode(image)
        return EmbeddingResponse(
            embedding=embedding.tolist(),
            dimension=len(embedding)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating image embedding: {str(e)}")

@web_app.post("/embed/image/upload", response_model=EmbeddingResponse)
async def embed_image_upload(file: UploadFile = File(...)):
    try:
        model_instance = get_model()
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert('RGB')
        embedding = model_instance.encode(image)
        return EmbeddingResponse(
            embedding=embedding.tolist(),
            dimension=len(embedding)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing uploaded image: {str(e)}")

### Deploy the FastAPI app on Modal
@app.function(
    image=image,
    gpu="T4",
    cpu=2.0,
    memory=2048,
    timeout=60,
    scaledown_window=90  # Keep container warm for 1.5 mins
)

@modal.asgi_app()
def fastapi_app():
    get_model()
    return web_app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(web_app, host="0.0.0.0", port=8000, reload=True)

