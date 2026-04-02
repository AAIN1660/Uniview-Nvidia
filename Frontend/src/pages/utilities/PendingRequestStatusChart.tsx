import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, LabelList } from 'recharts';
import 'bootstrap/dist/css/bootstrap.min.css';
import { data, transformData } from './SimuLatorMockData'; // Adjust the import path as per your project structure

const BarGraph = ({ selectedMonth, selectedMROCenter }) => {
  const [filteredData, setFilteredData] = useState([]);

  useEffect(() => {
    let filtered = data;

    if (selectedMonth) {
      const [year, month] = selectedMonth.split('-').map(Number);
      const startOfMonth = new Date(year, month - 1, 1);
      const endOfMonth = new Date(year, month, 0); // Last day of the selected month

      filtered = filtered.filter((item) => {
        const [startDay, startMonth, startYear] = item.Start_date.split('-').map(Number);
        const [endDay, endMonth, endYear] = item.Estimated_completion_date.split('-').map(Number);

        const startDate = new Date(startYear, startMonth - 1, startDay);
        const endDate = new Date(endYear, endMonth - 1, endDay);

        return (
          (startDate >= startOfMonth && startDate <= endOfMonth) ||
          (endDate >= startOfMonth && endDate <= endOfMonth) ||
          (startDate <= startOfMonth && endDate >= endOfMonth)
        );
      });
    }

    if (selectedMROCenter) {
      filtered = filtered.filter((item) => item.MRO_name === selectedMROCenter);
    }

    setFilteredData(transformData(filtered));
  }, [selectedMonth, selectedMROCenter]);

  if (filteredData.length === 0) {
    return (
      <div className="card ms-5" style={{ width: '600px', margin: '20px auto' }}>
        <div className="card-body">
          <h5 className="card-title">No Data Available</h5>
          <p className="card-text">* As on Date</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card ms-5" style={{ width: '600px', margin: '20px auto' }}>
      <div className="card-body">
        <h5 className="card-title">* Current Pending Request Status</h5>
        <BarChart
          width={500}
          height={300}
          data={filteredData}
          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="High" fill="#00C49F">
            <LabelList dataKey="High" position="top" />
          </Bar>
          <Bar dataKey="Medium" fill="#FFBB28">
            <LabelList dataKey="Medium" position="top" />
          </Bar>
          <Bar dataKey="Low" fill="#FF8042">
            <LabelList dataKey="Low" position="top" />
          </Bar>
        </BarChart>
        <p className="card-text">* As on Date</p>
      </div>
    </div>
  );
};

export default BarGraph;
