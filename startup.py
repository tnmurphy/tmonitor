import uvicorn
import database

if __name__ == "__main__":
    import main

    database.add_engine_to_app(main.app, database.production_db)

    uvicorn.run("main:app", host="0.0.0.0", port=5000, log_level="info")
