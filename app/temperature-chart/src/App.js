// This is an application that fetches sensor data from a website and displays it in a graph.
// There are hour, day and week views. It is possible to ask the website for a list of sensors 
// and the user can then select which sensor to view in the graph. 
// The data is sampled by the server so that it returns averages, maxima and minima for "sample buckets" 
// rather than all the data for the requested view. 


// This application fetches sensor data from a website and displays it in a graph.
// There are hour, day, and week views. The user can select which sensor to view.
// The data is sampled by the server to return averages, maxima, and minima for "sample buckets".

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

class ViewStyle {
  // A viewstyle controls how wide a view is, how far and fast the user
  // moves around in it and how it the ticks etc look. 
  constructor(
    periodName,
    period,
    movePeriod,
    fastMovePeriod,
    tickFormatter,
    edgeFormatter,
    sampleMethods,
    snapFunction
  ) {
    this.periodName = periodName;
    this.period = period;
    this.movePeriod = movePeriod;
    this.fastMovePeriod = fastMovePeriod;
    this.tickFormatter = tickFormatter;
    this.edgeFormatter = edgeFormatter;
    this.sampleMethods = sampleMethods.split(",");
    this.snapFunction = snapFunction;
  }

  snapToNearest(adjusted) {
    this.snapFunction(adjusted);
  }
}

class View {
  // A viewport is essentially a time range + a view style. 
  constructor(viewStyle, startTimestamp = 0, endTimestamp = 1) {
    this.viewStyle = viewStyle;
    this.startTimestamp = startTimestamp;
    this.endTimestamp = endTimestamp;
  }

  snapToNearest(adjusted) {
    this.viewStyle.snapToNearest(adjusted);
  }

  static atNow(style) {
    // Return a view that ends at the current time, using a particular style.
    const nowStamp = Math.floor(Date.now() / 1000);
    const view = new View(style);
    const adjusted = new Date((nowStamp - style.period) * 1000);
    view.snapToNearest(adjusted);
    const adjustedStamp = Math.floor(adjusted.getTime() / 1000);

    view.startTimestamp = adjustedStamp;
    view.endTimestamp = adjustedStamp + 2 * style.period;

    console.log(
      `atNow: ${view.viewStyle.periodName} end-start = ${view.endTimestamp - view.startTimestamp}`
    );
    console.log("atNow: startTS:", view.startTimestamp * 1000);
    console.log("atNow: start:", new Date(view.startTimestamp * 1000));
    console.log("atNow: endTS:", view.endTimestamp * 1000);
    console.log("atNow: end:", new Date(view.endTimestamp * 1000));

    return view;
  }

  getBucketCount() {
    const gap = this.endTimestamp - this.startTimestamp;
    const buckets = Math.max(1, Math.floor(gap / this.viewStyle.movePeriod));
    console.log(
      `getBucketCount: ${this.viewStyle.periodName} with gap ${gap} buckets=${buckets}`
    );
    return buckets;
  }

  static moveBackwards(previous, fast = false) {
    const nextView = new View(previous.viewStyle);
    const amount = fast ? previous.viewStyle.fastMovePeriod : previous.viewStyle.movePeriod;
    nextView.endTimestamp = Math.max(previous.endTimestamp - amount, 0);
    nextView.startTimestamp = Math.max(previous.startTimestamp - amount, 0);
    return nextView;
  }

  static moveForwards(previous, fast = false) {
    const nextView = new View(previous.viewStyle);
    const nowStamp = Math.floor(Date.now() / 1000);
    const amount = fast ? previous.viewStyle.fastMovePeriod : previous.viewStyle.movePeriod;
    const nextEndTimestamp = Math.min(previous.endTimestamp + amount, nowStamp);
    const movement = nextEndTimestamp - previous.endTimestamp;

    nextView.endTimestamp = nextEndTimestamp;
    nextView.startTimestamp = previous.startTimestamp + movement;
    return nextView;
  }
}

// Snap functions for each view style
const hourSnapFunction = (adjusted) => {
  adjusted.setMinutes(0, 0, 0);
};

const daySnapFunction = (adjusted) => {
  adjusted.setHours(0, 0, 0, 0);
};

const weekSnapFunction = (adjusted) => {
  adjusted.setHours(0, 0, 0, 0);
  // Optional: Snap to the start of the week (Monday)
  // const day = adjusted.getDay();
  // adjusted.setDate(adjusted.getDate() - day + (day === 0 ? -6 : 1));
};

const hourView = new ViewStyle(
  "hour",
  3600,
  3600 / 4,
  3600,
  (ts) => moment(ts * 1000).format("mm"),
  (ts) => moment(ts * 1000).format("HH:mm"),
  "avg,min,max",
  hourSnapFunction
);

const dayView = new ViewStyle(
  "day",
  86400,
  3600,
  86400 / 2,
  (ts) => moment(ts * 1000).format("HH:mm"),
  (ts) => moment(ts * 1000).format("HH:mm Do"),
  "min,max,avg",
  daySnapFunction
);

const weekView = new ViewStyle(
  "week",
  604800,
  86400,
  604800,
  (ts) => moment(ts * 1000).format("Do MMM"),
  (ts) => moment(ts * 1000).format("Do MMM"),
  "min,max,avg",
  weekSnapFunction
);

const initialView = View.atNow(hourView);

function App() {
  const [currentView, setCurrentView] = useState(initialView);
  const [data, setData] = useState([]);
  const [sensors, setSensors] = useState([]);
  const [selectedSensor, setSelectedSensor] = useState(null);

  const CustomizedAxisTick = ({ x, y, payload, index, data }) => {
    let tick = "";
    if (index === 0 || index === data.length - 2) {
      tick = currentView.viewStyle.edgeFormatter(payload.value);
    } else {
      tick = currentView.viewStyle.tickFormatter(payload.value);
    }
    return (
      <g transform={`translate(${x},${y})`}>
        <text x={0} y={0} dy={8} textAnchor="end" fill="#666" transform="rotate(-35)">
          {tick}
        </text>
      </g>
    );
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const date = new Date(payload[0].payload.timestamp * 1000);
      const formattedDate = moment(date).format("HH:mm   DD/MM/YYYY");
      return (
        <div className="custom-tooltip" style={{ background: "#fff", padding: "10px", border: "1px solid #ccc" }}>
          <p>{formattedDate}</p>
          {payload.map((item) => (
            <p key={item.name}>
              {item.name}: {item.value.toFixed(2)} {item.unit}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  useEffect(() => {
    fetch(`${API_URL}/sensors`, { mode: "cors" })
      .then((response) => response.json())
      .then((jsonData) => {
        setSensors(jsonData);
        if (jsonData.length > 0 && !selectedSensor) {
          setSelectedSensor(jsonData[0]);
        }
      })
      .catch((error) => console.error("Error fetching sensors:", error));
  }, [selectedSensor, currentView]);

  useEffect(() => {
    if (!selectedSensor) return;
    const period = currentView.endTimestamp - currentView.startTimestamp;
    fetch(
      `${API_URL}/sample?sensors=${selectedSensor}&start_timestamp=${currentView.startTimestamp}&period=${period}&units=C&sample_buckets=${currentView.getBucketCount()}&sample_methods=${currentView.viewStyle.sampleMethods}&limit=3000`,
      { mode: "cors" }
    )
      .then((response) => response.json())
      .then((sensor_data) => {
        setData(sensor_data.downsampled_data);
      })
      .catch((error) => console.error("Error fetching data:", error));
  }, [currentView, selectedSensor]);

  const moveBackwards = () => setCurrentView(View.moveBackwards(currentView));
  const moveForwards = () => setCurrentView(View.moveForwards(currentView));
  const moveFastBackwards = () => setCurrentView(View.moveBackwards(currentView, true));
  const moveFastForwards = () => setCurrentView(View.moveForwards(currentView, true));
  const setToNow = () => setCurrentView(View.atNow(currentView.viewStyle));

  const setViewStyle = (style) => {
    const newView = new View(style);
    Object.assign(newView, currentView);
    newView.viewStyle = style;
    const nowStamp = Date.now() / 1000;
    const gap = nowStamp - newView.startTimestamp;

    if (nowStamp - newView.startTimestamp < newView.viewStyle.period) {
      setCurrentView(View.atNow(newView.viewStyle));
    } else {
      setCurrentView(newView);
    }
  };

  return (
    <div style={{ width: "95%", height: 600 }}>
      <h1>Greenhouse Monitoring</h1>
      <div style={{ marginBottom: "16px" }}>
        <button onClick={moveFastBackwards}>FastBack</button>
        <button onClick={moveBackwards}>Back</button>
        <button onClick={moveForwards}>Forward</button>
        <button onClick={moveFastForwards}>Fast Forward</button>
        <button onClick={setToNow}>Now</button>
      </div>
      <div style={{ marginBottom: "16px" }}>
        <button onClick={() => setViewStyle(hourView)} style={{ fontWeight: currentView.viewStyle === hourView ? "bold" : "normal" }}>
          Hour
        </button>
        <button onClick={() => setViewStyle(dayView)} style={{ fontWeight: currentView.viewStyle === dayView ? "bold" : "normal" }}>
          Day
        </button>
        <button onClick={() => setViewStyle(weekView)} style={{ fontWeight: currentView.viewStyle === weekView ? "bold" : "normal" }}>
          Week
        </button>
      </div>
      <div style={{ marginBottom: "16px" }}>
        <label>Select Sensor: </label>
        <select value={selectedSensor || ""} onChange={(e) => setSelectedSensor(e.target.value)} style={{ marginLeft: "10px" }}>
          {sensors.map((sensor) => (
            <option key={sensor} value={sensor}>
              {sensor}
            </option>
          ))}
        </select>
      </div>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="timestamp"
            domain={[currentView.startTimestamp, currentView.endTimestamp]}
            tick={<CustomizedAxisTick data={data} />}
            tickFormatter={currentView.viewStyle.tickFormatter}
          />
          <YAxis />
          <Tooltip content={<CustomTooltip />} />
          <Legend verticalAlign="top" height={64} />
          {data.length > 0 &&
            Object.keys(data[0])
              .filter((key) => key !== "timestamp")
              .map((dataseries) => (
                <Line
                  key={dataseries}
                  type="monotone"
                  dataKey={dataseries}
                  stroke={getColorForSeries(dataseries)}
                  name={prettyDataSeriesName(dataseries)}
                  activeDot={{ r: 8 }}
                />
              ))}
        </LineChart>
      </ResponsiveContainer>
      <span style={{ margin: "10px 15px" }}>View starts at: {new Date(currentView.startTimestamp * 1000).toLocaleString()}</span>
      <span style={{ margin: "10px 15px" }}>Now: {moment(Date.now()).toLocaleString()}</span>
      <span style={{ margin: "10px 15px" }}>Selected sensor: {selectedSensor}</span>
    </div>
  );
}

function prettyDataSeriesName(series) {
  const [sensor, unit, method] = series.split("_");
  const measurements = {
    C: "temperature, C",
    kPa: "pressure, kPa",
    lux: "light, lux",
    presence: "human presence",
  };
  return `${method} ${measurements[unit] || "?"} node: ${sensor}`;
}

function getColorForSeries(series) {
  const [, , method] = series.split("_");
  const colors = {
    avg: "#8884d8",
    min: "#ff0000",
    max: "#11aa11",
  };
  return colors[method] || "#8884d8";
}

export default App;

