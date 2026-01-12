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
  constructor(
    periodName, 
    period,
    movePeriod,
    fastMovePeriod,
    tickFormatter,
    edgeFormatter,
    sampleMethods
  ) {
    this.periodName = periodName
    this.period = period;
    this.movePeriod = movePeriod;
    this.fastMovePeriod = fastMovePeriod;
    this.tickFormatter = tickFormatter;
    this.edgeFormatter = edgeFormatter;
    this.sampleMethods = sampleMethods.split(",");
  }
}


class View {
  constructor(viewStyle, startTimestamp=0, endTimestamp=1) {
    // The initial timestamp and end timestamp if no start timestamp is specified
    this.viewStyle = viewStyle;
    this.startTimestamp = startTimestamp;
    this.endTimestamp = endTimestamp;
  }

  static atNow(style) {
    const now = new Date();
    const view = new View(style);
    view.timeRangeEndingNow(now);
    return view;
  }

  snapToNearest(adjusted) { 
    switch (this.viewStyle.periodName.toLowerCase()) {
      case 'hour':
        // Set minutes, seconds, and milliseconds to 0 to get the start of the current hour
        adjusted.setMinutes(0, 0, 0);
        break;
      case 'day':
        // Set hours, minutes, seconds, and milliseconds to 0 to get the start of the current day
        adjusted.setHours(0, 0, 0, 0);
        break;
      case 'week':
        adjusted.setHours(0, 0, 0, 0);
        break;
      default:
        throw new Error("Invalid period. Use 'hour', 'day', or 'week'.");
    }
  }

  moveBackOneView(adjusted) { 
    // Subtract the specified period
    switch (this.viewStyle.periodName.toLowerCase()) {
      case 'hour':
        adjusted.setHours(adjusted.getHours() - 1);
        break;
      case 'day':
        adjusted.setDate(adjusted.getDate() - 1);
        break;
      case 'week':
        adjusted.setDate(adjusted.getDate() - 7);
        break;
      default:
        break;
    }
  }; 

  timeRangeEndingNow(now) {
    const adjusted = new Date(now);
    this.moveBackOneView(adjusted);
    this.snapToNearest(adjusted);

    // Return the timestamp in seconds
    this.startTimestamp = Math.floor(adjusted.getTime()/1000);
    this.endTimestamp = Math.floor(now.getTime()/1000);
    console.log("timeRangeEndingNow: view: " +this.viewStyle.periodName + " end-start = " + (this.endTimestamp - this.startTimestamp));
  };

  getBucketCount() {
     // The bucket count is based on how many movePeriods fit into the start/end range
     return Math.max(1,Math.round((this.endTimestamp - this.startTimestamp)/this.viewStyle.movePeriod)); 
  };

  static moveBackwards(previous, fast=false) {
    console.log("View.moveBackwards: "+previous.viewStyle.periodName);
    const nextView = new View(previous.viewStyle);


    const amount = fast ? previous.viewStyle.fastMovePeriod : previous.viewStyle.movePeriod;
    nextView.endTimestamp = Math.max(previous.endTimestamp - amount, 0);
    nextView.startTimestamp = Math.max(previous.startTimestamp - amount, 0);
    console.log("backwards: "+nextView.viewStyle.periodName);
    return nextView;
  };

  static moveForwards(previous, fast=false) {
    const nextView = new View(previous.viewStyle);
    const nowStamp = Math.floor(Date.now() / 1000.0);
    const amount = fast ? previous.viewStyle.fastMovePeriod : previous.viewStyle.movePeriod;

    // Dont move into the future.
    console.log("MoveForwards: nowStamp=" + nowStamp);
    const nextEndTimestamp = Math.min(previous.endTimestamp + amount, nowStamp);
    const movement = nextEndTimestamp - previous.endTimestamp

    nextView.endTimestamp = nextEndTimestamp;
    nextView.startTimestamp = previous.startTimestamp + movement;
    console.log("MoveForwards: " + nextView.viewStyle.periodName +" "+nextView.startTimestamp);
    // A shallow copy to ensure react sees a change.
    return nextView;
  };

}

const hourView = new ViewStyle(
  "hour",
  3600, // 1 hour in seconds
  1800, // 30 minutes in seconds
  3600, // 1 hour in seconds
  (ts) => moment(ts * 1000).format("mm"), // Show minutes
  (ts) => moment(ts * 1000).format("HH:mm"), // Show minutes
  "avg" // Only average for hour view
);

const dayView = new ViewStyle(
  "day",
  86400, // 1 day in seconds
  3600,  // 1 hour in seconds
  86400/2, // 1/2 day in seconds
  (ts) => moment(ts * 1000).format("HH:mm"), // Show hours and minutes
  (ts) => moment(ts * 1000).format("HH:mm Do"), // Show day and hour at the edges of the axis
  "min,max,avg" // Min, max and average for day view
);

const weekView = new ViewStyle(
  "week",
  604800, // 1 week in seconds
  86400, // 1 day in seconds
  604800, // 1 week in seconds
  (ts) => moment(ts * 1000).format("Do MMM"), // Show Month and day at the left and right edges
  (ts) => moment(ts * 1000).format("Do MMM"), // Show Month and day at the left and right edges
  "min,max,avg" // Min, max and average for week view
);
const initialView = View.atNow(hourView);

function App() {

 const [currentView, setCurrentView] = useState(initialView);
  const [data, setData] = useState([]);
  const [sensors, setSensors] = useState([]);
  const [selectedSensor, setSelectedSensor] = useState(null);

  let CustomizedAxisTick = ({ x, y, payload, index, data }) => {
    let tick = "";
    if (index === 0 || index === data.length - 2) {
      tick = currentView.viewStyle.edgeFormatter(payload.value);
    } else {
      tick = currentView.viewStyle.tickFormatter(payload.value);
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
          {payload.map((item) => (
            <p style={{
               padding: "10px",
               }}
            key={item.name}>
              {item.name}: {item.value} {item.unit}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  useEffect(() => {
    // First fetch to get available sensors
    fetch(`${API_URL}/sensors`, { mode: "cors" })
      .then((response) => response.json())
      .then((jsonData) => {
        setSensors(jsonData);
        if (jsonData.length > 0 && !selectedSensor) {
          setSelectedSensor(jsonData[0]);
        }
      })
      .catch((error) => console.error("Error fetching sensors:", error));
  }, [selectedSensor]);

  useEffect(() => {
    if (!selectedSensor) return;
    console.log("fetching view: " + currentView.viewStyle.periodName);
    console.log("view keys: " + Object.keys(currentView));
    console.log("view methods:" + Object.getOwnPropertyNames(currentView));
    console.log("Buckets: " + currentView.getBucketCount())
    console.log("endTimestamp: " + currentView.endTimestamp);
    console.log("startTimestamp: " + currentView.startTimestamp);
    const period = currentView.endTimestamp - currentView.startTimestamp;
    fetch(
`${API_URL}/sample?sensors=${selectedSensor}&start_timestamp=${currentView.startTimestamp}&period=${period}&units=C&sample_buckets=${currentView.getBucketCount()}&sample_methods=${currentView.viewStyle.sampleMethods}&limit=3000`,
      { mode: "cors" }
    )
      .then((response) => response.json())
      .then((sensor_data) =>  {
        console.log("SENSOR_DATA: " + sensor_data)
        let downsampled_data = sensor_data.downsampled_data
        for (var i = 0; i < downsampled_data.length; i++) {
            const ts = downsampled_data[i].timestamp
            const sd = new Date(ts*1000);
            console.log("DOWNSAMPLED_DATA["+i+"]: " + sd + " " + ts);
        }
        setData(downsampled_data);
      })
      .catch((error) => console.error("Error fetching data:", error));
  }, [currentView, selectedSensor]);

  const moveBackwards = () => {
    console.log("moveBackwards: "+currentView.viewStyle.periodName);
    const newView = View.moveBackwards(currentView);
    setCurrentView(newView);
  };

  const moveForwards = () => {
    const newView = View.moveForwards(currentView);
    setCurrentView(newView);
  };

  const moveFastBackwards = () => {
    const newView = View.moveBackwards(currentView, true);
    setCurrentView(newView);
  };

  const moveFastForwards = () => {
    const newView = View.moveForwards(currentView, true);
    setCurrentView(newView);
  };

  const setViewStyle = (style) => {
    const newView = new View(style);
    Object.assign(newView, currentView);
    newView.viewStyle =	style;
    setCurrentView(newView);
  }
 



// Example usage:
// console.log(timestamp);


  const setToNow = () => { 
      const nextView = View.atNow(currentView.viewStyle);
      setCurrentView(nextView);
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
        <button
          onClick={() => setViewStyle(hourView)}
          style={{ fontWeight: currentView.viewStyle === hourView ? "bold" : "normal" }}
        >
          Hour
        </button>
        <button
          onClick={() => setViewStyle(dayView)}
          style={{ fontWeight: currentView.viewStyle === dayView ? "bold" : "normal" }}
        >
          Day
        </button>
        <button
          onClick={() => setViewStyle(weekView)}
          style={{ fontWeight: currentView.viewStyle === weekView ? "bold" : "normal" }}
        >
          Week
        </button>
      </div>

      <div style={{ marginBottom: "16px" }}>
        <label>Select Sensor: </label>
        <select
          value={selectedSensor || ''}
          onChange={(e) => setSelectedSensor(e.target.value)}
          style={{ marginLeft: "10px" }}
        >
          {sensors.map((sensor) => (
            <option key={sensor} value={sensor}>
              {sensor}
            </option>
          ))}
        </select>
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
              currentView.startTimestamp,
              currentView.endTimestamp
            ]}
            tick={<CustomizedAxisTick data={data} />}
            tickFormatter={currentView.viewStyle.tickFormatter}
          />
          <YAxis />
          <Tooltip content={<CustomTooltip />} />
          <Legend verticalAlign="top" height={64} />

          {/* Dynamically create lines for each value */}
          {data.length > 0 && (
            <>
              {Object.keys(data[0])
                .filter(key => key !== "timestamp")
                .map(dataseries => (
                <Line
                  key={dataseries}
                  type="monotone"
                  dataKey={dataseries}
                  stroke={getColorForSeries(dataseries)}
                  name={prettyDataSeriesName(dataseries)}
                  activeDot={{ r: 8 }}
                />
              ))}
            </>
          )}
        </LineChart>
      </ResponsiveContainer>

      <span style={{ margin: "10px 15px" }}>
        View starts at: {new Date(currentView.startTimestamp * 1000).toLocaleString()}
      </span>
      <span style={{ margin: "10px 15px" }}>
        Now: {moment(Date.now()).toLocaleString()}
      </span>
      <span style={{ margin: "10px 15px" }}>
        Selected sensor: {selectedSensor}
      </span>
    </div>
  );
}

function prettyDataSeriesName(series) {
  const [sensor,unit,method] = series.split("_")

  const measurements = {
    C: 'temperature, C',
    kPa: 'pressure, kPa',
    lux: 'light, lux',
    presence: "human presence"
  };

  const m = measurements[unit] || '?';
  
  return method + " " + m + " node: " + sensor  
}

// Helper function to assign colors to different sample methods
function getColorForSeries(series) {
  const [sensor,_,method] = series.split("_")
  const colors = {
    avg: '#8884d8',
    min: '#ff0000',
    max: '#11aa11'
  };
  
  let col = colors[method] || '#8884d8';

  console.debug("COLOUR for "+method+" from "+sensor+" is "+col)
  return col
}

export default App;

