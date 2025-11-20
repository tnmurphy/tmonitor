import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function App() {
  const [data, setData] = useState([]);
  const [startTimestamp, setStartTimestamp] = useState(Math.floor(Date.now() / 1000 - 3600));
  const [period, setPeriod] = useState(3600); // Default: 1 hour in seconds

  useEffect(() => {
    fetch(`http://chivero:5000/read?start_timestamp=${startTimestamp}&period=${period}`, { mode: "cors" })
      .then(response => response.json())
      .then(jsonData => {
        const formattedData = jsonData.readings.filter(item => item.unit==="C").map(item => ({
          time: new Date(item.recorded_timestamp * 1000).toLocaleString(),
          temperature: item.value
        }));
        setData(formattedData);
      })
      .catch(error => console.error('Error fetching data:', error));
  }, [startTimestamp, period]);

  const moveBackward = () => {
    setStartTimestamp(prev => Math.max(prev - period, 0));
  };

  const moveForward = () => {
    setStartTimestamp(prev => prev + period);
  };

  const setPeriodToHour = () => setPeriod(3600);
  const setPeriodToDay = () => setPeriod(86400);
  const setPeriodToWeek = () => setPeriod(604800);
  const setToNow = () => setStartTimestamp(Math.floor(Date.now() / 1000));

  return (
    <div style={{ width: '100%', height: 400 }}>
      <h1>Temperature Over Time</h1>
      <div style={{ marginBottom: '16px' }}>
        <button onClick={moveBackward}>Back</button>
        <button onClick={moveForward}>Forward</button>
        <button onClick={setToNow}>Now</button>
        <span style={{ margin: '0 10px' }}>
          Start: {new Date(startTimestamp * 1000).toLocaleString()}
        </span>
      </div>
      <div style={{ marginBottom: '16px' }}>
        <button
          onClick={setPeriodToHour}
          style={{ fontWeight: period === 3600 ? 'bold' : 'normal' }}
        >
          Hour
        </button>
        <button
          onClick={setPeriodToDay}
          style={{ fontWeight: period === 86400 ? 'bold' : 'normal' }}
        >
          Day
        </button>
        <button
          onClick={setPeriodToWeek}
          style={{ fontWeight: period === 604800 ? 'bold' : 'normal' }}
        >
          Week
        </button>
      </div>
      <ResponsiveContainer>
        <LineChart
          data={data}
          margin={{
            top: 5, right: 30, left: 20, bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="temperature" stroke="#8884d8" activeDot={{ r: 8 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default App;

