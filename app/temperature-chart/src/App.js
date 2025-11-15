import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function App() {
  const [data, setData] = useState([]);

  useEffect(() => {
    // Replace this URL with your actual endpoint
    fetch('http://chivero:5000/read?period=3600', {mode: "cors"})
      .then(response => response.json())
      .then(jsonData => { 
          console.log(jsonData)
          return jsonData
       })
      .then(jsonData => {
        // Convert timestamp to a readable date string
        const formattedData = jsonData.readings.map(item => ({
          time: new Date(item.recorded_timestamp * 1000).toLocaleTimeString(),
          temperature: item.value
        }));
        setData(formattedData);
      })
      .catch(error => console.error('Error fetching data:', error));
  }, []);

  return (
    <div style={{ width: '100%', height: 400 }}>
      <h1>Temperature Over Time</h1>
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

