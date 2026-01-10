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
    sampleBuckets,
    sampleMethods
  ) {
    this.periodName = periodName
    this.period = period;
    this.movePeriod = movePeriod;
    this.fastMovePeriod = fastMovePeriod;
    this.tickFormatter = tickFormatter;
    this.edgeFormatter = edgeFormatter;
    this.sampleBuckets = sampleBuckets;
    this.sampleMethods = sampleMethods.split(",");
  }
}


class View {
  constructor(viewStyle, startTime) {
    // The initial timestamp and end timestamp if no start timestamp is specified
    // const now = new Date();
    this.viewStyle = viewStyle;
    [this.startTimestamp, this.endTimestamp] = this.calcTimeRange(startTime);
  }

  calcTimeRange(now) {
    const adjusted = new Date();
  
    // Subtract the specified period
    switch (this.period.periodName.toLowerCase()) {
      case 'hour':
        adjusted.setHours(now.getHours() - 1);
        break;
      case 'day':
        adjusted.setDate(now.getDate() - 1);
        break;
      case 'week':
        adjusted.setDate(now.getDate() - 7);
        break;
      default:
        break;
    }
  
    switch (this.period.periodName.toLowerCase()) {
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

    // Return the timestamp in seconds
    console.log(" Selecting start time for graph. Current time is: " + now + " adjusted to be one " + this.period.periodName +" back: " + adjusted);
    return [Math.floor(adjusted.getTime()/1000), Math.floor(now.getTime()/1000)];
  };

  getBucketCount() {
     Math.max(1,Math.round((this.endTimestamp - this.startTimestamp)/this.viewStyle.movePeriod)) // One point per hour
  }
}

const hourView = new ViewStyle(
  "hour",
  3600, // 1 hour in seconds
  300, // 5 minutes in seconds
  3600, // 1 hour in seconds
  (ts) => moment(ts * 1000).format("mm"), // Show minutes
  (ts) => moment(ts * 1000).format("HH:mm"), // Show minutes
  "avg" // Only average for hour view
);

const dayView = new ViewStyle(
  "day",
  86400, // 1 day in seconds
  3600, // 1 hour in seconds
  86400, // 1 day in seconds
  (ts) => moment(ts * 1000).format("HH:mm"), // Show hours and minutes
  (ts) => moment(ts * 1000).format("HH:mm Do"), // Show day and hour at the edges of the axis
  (startTimestamp, endTimestamp) => Math.max(1,Math.round((endTimestamp - startTimestamp)/3600)), // One point per hour
  "min,max,avg" // Min, max and average for day view
);

const weekView = new ViewStyle(
  "week",
  604800, // 1 week in seconds
  86400, // 1 day in seconds
  604800, // 1 week in seconds
  (ts) => moment(ts * 1000).format("Do MMM"), // Show Month and day at the left and right edges
  (ts) => moment(ts * 1000).format("Do MMM"), // Show Month and day at the left and right edges
  (startTimestamp, endTimestamp) => Math.max(1,Math.round((endTimestamp - startTimestamp)/86400)), // One point per day
  "min,max,avg" // Min, max and average for week view
);


function App() {

  const [data, setData] = useState([]);
  const [currentView, setCurrentView] = useState(new View(hourView, new Date.now()));
  const [sensors, setSensors] = useState([]);
  const [selectedSensor, setSelectedSensor] = useState(null);

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

    fetch(
`${API_URL}/sample?sensors=${selectedSensor}&start_timestamp=${currentView.startTimestamp}&period=${currentView.period}&units=C&sample_buckets=${currentView.getBucketCount()}&sample_methods=${currentView.currentViewStyle.sampleMethods}&limit=3000`,
      { mode: "cors" }
    )
      .then((response) => response.json())
      .then((sensor_data) =>  {
        let downsampled_data = sensor_data.downsampled_data
        console.log("SENSOR_DATA: " + sensor_data)
        setData(downsampled_data);

      })
      .catch((error) => console.error("Error fetching data:", error));
  }, [currentView, selectedSensor]);

  const moveBackward = () => {
    newView = new View(currentView.viewStyle)
    setCurrentView(newView)
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



// Example usage:
// console.log(timestamp);


  const setToNow = () => { 
      setStartTimestamp(getAdjustedTimestamp(currentView))
  };

  return (
    <div style={{ width: "95%", height: 600 }}>
      <h1>Greenhouse Monitoring</h1>

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
            tickFormatter={currentView.tickFormatter}
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
        Now: {moment(Date.now()).format()}
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

