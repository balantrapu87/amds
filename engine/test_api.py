"""
Minimal test FastAPI server to demonstrate the video generation system.
This simulates the core functionality without requiring external AI services.
"""

import os
import json
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Create a simple test API
app = FastAPI(
    title="Test Motion Design Studio Engine",
    version="1.0.0",
    description="Minimal test server"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job registry for testing
JOB_REGISTRY = {}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "test-motion-api", "concurrency": 1}

@app.post("/render")
async def test_render():
    """Test render endpoint that returns immediately"""
    job_id = str(uuid.uuid4())
    
    # Register job as completed immediately
    JOB_REGISTRY[job_id] = {
        "job_id": job_id,
        "status": "completed",
        "step": "test",
        "duration_frames": 150,
        "duration_seconds": 5,
        "scenes_count": 1,
        "output_path": f"output/{job_id}.mp4"
    }
    
    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "completed",
            "message": "Test render job completed successfully",
            "duration_frames": 150,
            "duration_seconds": 5,
            "scenes_count": 1
        }
    )

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status"""
    if job_id not in JOB_REGISTRY:
        raise HTTPException(status_code=404, detail="Job ID not found")
    return JOB_REGISTRY[job_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)