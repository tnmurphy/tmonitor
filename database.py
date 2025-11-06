from sqlmodel import create_engine, SQLModel
from sensor_reading import SensorReading

dburl = "sqlite:///monitor.db"

def add_engine_to_app(app):
    app.state.engine = create_engine(dburl)

def make_database():
    engine = create_engine(dburl)
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    make_database()
