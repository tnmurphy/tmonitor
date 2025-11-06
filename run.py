import uvicorn
from fastapi import FastAPI
import database

if __name__ == "__main__":
    import main
    database.add_engine_to_app(main.app)

    uvicorn.run("main:app", port=5000, log_level="info")
