// The following code displays a graph of temperature over time and allows the user to move
// that view backwards and forwards by an amount which is less than the total period shown.
// e.g. if the user chooses to show a day, then they are able to move forwards or backwards
// in increments of an hour.
// The data is fetched from a URL whenever the user chooses to move the view to a different start time
// or chooses to effectively zoom in or out by selecting a different period.

import React, { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import moment from "moment";

const API_URL = "http://chivero:5000";

class View {
  constructor(
    period,
    movePeriod,
    fastMovePeriod,
    tickFormatter,
    edgeFormatter,
  ) {
    this.period = period;
    this.movePeriod = movePeriod;
    this.fastMovePeriod = fastMovePeriod;
    this.tickFormatter = tickFormatter;
    this.edgeFormatter = edgeFormatter;
  }
}

const hourView = new View(
  3600, // 1 hour in seconds
  300, // 5 minutes in seconds
  3600, // 1 hour in seconds
  (ts) => moment(ts * 1000).format("mm"), // Show minutes
  (ts) => moment(ts * 1000).format("hh:mm"), // Show minutes
);

const dayView = new View(
  86400, // 1 day in seconds
  3600, // 1 hour in seconds
  86400, // 1 day in seconds
  (ts) => moment(ts * 1000).format("HH:mm"), // Show hours and minutes
  (ts) => moment(ts * 1000).format("HH:mm Do"), // Show day and hour at the edges of the axis
);

const weekView = new View(
  604800, // 1 week in seconds
  86400, // 1 day in seconds
  604800, // 1 week in seconds
  (ts) => moment(ts * 1000).format("HH Do"), // Show day of month and hour
  (ts) => moment(ts * 1000).format("Do MM"), // Show Month and day at the left and right edges
);

function App() {
  const [data, setData] = useState([]);
  const [startTimestamp, setStartTimestamp] = useState(
    Math.floor(Date.now() / 1000 - 300),
  );
  const [endTimestamp, setEndTimestamp] = useState(
    Math.floor(Date.now() / 1000),
  );
  const [currentView, setCurrentView] = useState(hourView);

  let CustomizedAxisTick = ({ x, y, payload, index, data }) => {
    let tick = "";
    if (index === 0 || index === data.length - 2) {
      tick = currentView.edgeFormatter(payload.value);
    } else {
      tick = currentView.tickFormatter(payload.value);
    }
    return (
      <g transform={`translate(${x},${y})`}>
        <text
          x={0}
          y={0}
          dy={8}
          textAnchor="end"
          fill="#666"
          transform="rotate(-35)"
        >
          {tick}
        </text>
      </g>
    );
  };

  let CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      // Format Unix timestamp to a readable date
      const date = new Date(payload[0].payload.timestamp * 1000);
      const formattedDate = moment(date).format();

      return (
        <div
          className="custom-tooltip"
          style={{
            background: "#fff",
            padding: "10px",
            border: "1px solid #ccc",
          }}
        >
          <p>{formattedDate}</p>
          <p>{`${payload[0].payload.value} ${payload[0].payload.unit}`}</p>
        </div>
      );
    }
    return null;
  };

  useEffect(() => {
    fetch(
      API_URL +
        `/read?start_timestamp=${startTimestamp}&period=${currentView.period}&units=C`,
      { mode: "cors" },
    )
      .then((response) => response.json())
      .then((jsonData) => {
        const formattedData = jsonData.readings
          .filter((item) => item.unit === "C")
          .map((item) => ({
            timestamp: item.recorded_timestamp,
            time: new Date(item.recorded_timestamp * 1000).toLocaleString(),
            unit: item.unit,
            value: item.value,
          }));
        setData(formattedData);
        if (formattedData.length > 0) {
          let lastDate = formattedData.at(-1)["timestamp"];
          setEndTimestamp(lastDate);
        }
      })
      .catch((error) => console.error("Error fetching data:", error));
  }, [startTimestamp, currentView.period]);

  const moveBackward = () => {
    setStartTimestamp((prev) => Math.max(prev - currentView.movePeriod, 0));
  };

  const moveForward = () => {
    setStartTimestamp((prev) => prev + currentView.movePeriod);
  };

  const moveFastBackward = () => {
    setStartTimestamp((prev) => Math.max(prev - currentView.fastMovePeriod, 0));
  };

  const moveFastForward = () => {
    setStartTimestamp((prev) => prev + currentView.fastMovePeriod);
  };

  const setToNow = () => setStartTimestamp(Math.floor(Date.now() / 1000));

  return (
    <div style={{ width: "95%", height: 400 }}>
      <h1>Greenhouse Temperature</h1>
      <div style={{ marginBottom: "16px" }}>
        <button onClick={moveFastBackward}>FastBack</button>
        <button onClick={moveBackward}>Back</button>
        <button onClick={moveForward}>Forward</button>
        <button onClick={moveFastForward}>Fast Forward</button>
        <button onClick={setToNow}>Now</button>
      </div>
      <div style={{ marginBottom: "16px" }}>
        <button
          onClick={() => setCurrentView(hourView)}
          style={{ fontWeight: currentView === hourView ? "bold" : "normal" }}
        >
          Hour
        </button>
        <button
          onClick={() => setCurrentView(dayView)}
          style={{ fontWeight: currentView === dayView ? "bold" : "normal" }}
        >
          Day
        </button>
        <button
          onClick={() => setCurrentView(weekView)}
          style={{ fontWeight: currentView === weekView ? "bold" : "normal" }}
        >
          Week
        </button>
      </div>
      <ResponsiveContainer>
        <LineChart
          responsive
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 60 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="timestamp"
            domain={[
              startTimestamp,
              Math.min(startTimestamp + currentView.period, endTimestamp),
            ]}
            tick={<CustomizedAxisTick data={data} />}
            tickFormatter={currentView.tickFormatter}
          />
          <YAxis />
          <Tooltip content={<CustomTooltip />} />
          <Legend verticalAlign="top" height={64} />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#8884d8"
            activeDot={{ r: 8 }}
          />
        </LineChart>
      </ResponsiveContainer>
      <span style={{ margin: "10px 15px" }}>
        View starts at: {new Date(startTimestamp * 1000).toLocaleString()}
      </span>
      <span style={{ margin: "10px 15px" }}>
        Now: {moment(Date.now()).format()}
      </span>
    </div>
  );
}

export default App;
