from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List
from pathlib import Path
from loguru import logger
from contextlib import asynccontextmanager
from src.config import load_config, AppConfig
from src.pipeline import RAGPipeline, PipelineError

class QueryRequest(BaseModel):
    question: str
    customer_data: str = ""

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]

class DeleteRequest(BaseModel):
    filename: str

# Load configuration
config = load_config()
pipeline = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    try:
        logger.debug("Starting pipeline initialization")
        pipeline = RAGPipeline(config)
        await pipeline.initialize_async()
        logger.info("✅ Application started successfully")
        yield
    except Exception as e:
        logger.error(f"❌ Startup failed, continuing with limited functionality: {str(e)}")
        pipeline = None
        yield
    finally:
        logger.info("🛑 Application shutdown")
        if pipeline:
            pipeline.__del__()

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def get_web_interface(request: Request):
    try:
        template_path = Path("templates/index.html").resolve()
        logger.info(f"Serving index.html from {template_path}")
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"❌ Failed to serve web interface: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load template: {str(e)}")

@app.post("/query", response_model=QueryResponse)
@app.post("/voice-query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    try:
        if not pipeline:
            logger.error("Query failed: Pipeline is None")
            raise PipelineError("Pipeline not initialized", code=503)
        logger.debug(f"Processing query: {request.question}, customer_data: {request.customer_data}")
        customer_data = request.customer_data or ""
        answer, sources = await pipeline.process_voice_query(request.question, customer_data)
        logger.debug(f"Query response: answer={answer[:50]}..., sources={sources}")
        return QueryResponse(answer=answer, sources=sources or [])
    except PipelineError as e:
        logger.error(f"❌ Query failed: {e}")
        raise HTTPException(status_code=e.code, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Unexpected query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    try:
        if not pipeline:
            logger.error("Upload failed: Pipeline is None")
            raise PipelineError("Pipeline not initialized", code=503)
        file_paths = []
        uploads_dir = Path(config.data_dir)
        uploads_dir.mkdir(exist_ok=True)
        for file in files:
            if file.size > config.get_max_file_size_bytes():
                logger.error(f"File {file.filename} exceeds max size of {config.max_file_size_mb}MB")
                raise PipelineError(f"File {file.filename} exceeds max size of {config.max_file_size_mb}MB", code=400)
            file_path = uploads_dir / file.filename
            with file_path.open("wb") as f:
                f.write(await file.read())
            file_paths.append(file_path)
        logger.debug(f"Uploading files: {[f.name for f in file_paths]}")
        pipeline.add_documents(file_paths)
        logger.info(f"Uploaded files: {[f.name for f in file_paths]}")
        return {"status": "success", "files_uploaded": [f.filename for f in files]}
    except PipelineError as e:
        logger.error(f"❌ Upload failed: {e}")
        raise HTTPException(status_code=e.code, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Unexpected upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/documents")
async def list_documents():
    try:
        if not pipeline:
            logger.error("List documents failed: Pipeline is None")
            raise PipelineError("Pipeline not initialized", code=503)
        documents = pipeline.list_documents()
        logger.debug(f"Listed documents: {documents}")
        return {"documents": documents}
    except PipelineError as e:
        logger.error(f"❌ List documents failed: {e}")
        raise HTTPException(status_code=e.code, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Unexpected list documents error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/documents")
async def delete_document(request: DeleteRequest):
    try:
        if not pipeline:
            logger.error("Delete document failed: Pipeline is None")
            raise PipelineError("Pipeline not initialized", code=503)
        logger.debug(f"Deleting document: {request.filename}")
        result = pipeline.delete_document(request.filename)
        logger.info(f"Deleted document: {request.filename}")
        return result
    except PipelineError as e:
        logger.error(f"❌ Delete document failed: {e}")
        raise HTTPException(status_code=e.code, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Unexpected delete document error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/stats")
async def get_stats():
    try:
        if not pipeline:
            logger.error("Get stats failed: Pipeline is None")
            raise PipelineError("Pipeline not initialized", code=503)
        stats = pipeline.get_stats()
        logger.debug(f"Stats: {stats}")
        return stats
    except PipelineError as e:
        logger.error(f"❌ Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Unexpected stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    try:
        if not pipeline:
            logger.error("Health check failed: Pipeline is None")
            return {"status": "unhealthy", "detail": "Pipeline not initialized"}
        healthy = pipeline.health_check()
        logger.debug(f"Health check result: {'healthy' if healthy else 'unhealthy'}")
        return {"status": "healthy" if healthy else "unhealthy", "detail": pipeline.initialization_status}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "detail": f"Health check error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=config.log_level.lower(),
        reload=config.reload
    )