"""
As a module this enables the FastAPI app to connect.

As a program this creates the database.


MIT License

Copyright (c) 2025 Timothy Norman Murphy <tnmurphy@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

from sqlmodel import create_engine, SQLModel
from sensor_reading import SensorReading

production_db = "sqlite:///monitor.db"
test_db = "sqlite:///test_monitor.db"

def new_test_database(app):
    app.state.engine = create_engine(test_db)
    SQLModel.metadata.create_all(app.state.engine)

def add_engine_to_app(app):
    app.state.engine = create_engine(dburl)

def make_database(url=production_db):
    engine = create_engine(url)
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    make_database()
