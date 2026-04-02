import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LabelList
} from 'recharts';
import { data, transformAverageThroughput } from './SimuLatorMockData';
import './ThroughputBarChart.css';

const ThroughputBarChart = ({ selectedMonth, selectedMROCenter }) => {
  const [transformedData, setTransformedData] = useState([]);
    console.log(transformedData);
    
  useEffect(() => {
    let filteredData = data;

    if (selectedMonth) {
      const [year, month] = selectedMonth.split('-').map(Number);
      const startDate = new Date(year, month - 1, 1);
      const endDate = new Date(year, month, 0);

      filteredData = filteredData.filter((item) => {
        const [startDay, startMonth, startYear] = item.Start_date.split('-').map(Number);
        const [endDay, endMonth, endYear] = item.Estimated_completion_date.split('-').map(Number);

        const startDateItem = new Date(startYear, startMonth - 1, startDay);
        const endDateItem = new Date(endYear, endMonth - 1, endDay);

        return (
          (startDateItem >= startDate && startDateItem <= endDate) ||
          (endDateItem >= startDate && endDateItem <= endDate) ||
          (startDateItem <= startDate && endDateItem >= endDate)
        );
      });
    }

    if (selectedMROCenter) {
      filteredData = filteredData.filter((item) => item.MRO_name === selectedMROCenter);
    }

    const transformedAverageThroughput = transformAverageThroughput(filteredData);

    // Aggregate average throughput data for each MRO center
    const aggregatedData = {};
    transformedAverageThroughput.forEach(item => {
      if (!aggregatedData[item.name]) {
        aggregatedData[item.name] = item.averageThroughput;
      }
    });

    // Prepare final data for chart
    const finalData = Object.keys(aggregatedData).map((center, index) => ({
      MRO_name: center,
      averageThroughput: 90 + index, // Replace with your dummy values or logic
      fill: COLORS[index % COLORS.length] // Assign color from COLORS array
    }));


    setTransformedData(finalData);
  }, [selectedMonth, selectedMROCenter]);

  const COLORS = ['#5F3A8A', '#AB82C5', '#88D8F7', '#5FB9E5', '#2F637B', '#FFBB28', '#FF8042']; 

  const CustomLegend = () => (
    <div className="custom-legend">
      {transformedData.map((entry, index) => (
        <div key={`item-${index}`} className="legend-item">
          <span className="color-box" style={{ backgroundColor: entry.fill }}></span>
          <span className="legend-text">{entry.MRO_name}</span>
        </div>
      ))}
    </div>
  );

  return (
    <div className="chart-wrapper">
      <div className="header">
        <h3 className="title">THROUGHPUT</h3>
      </div>
      {transformedData.length === 0 ? (
        <div className="no-data-message">
          <p>No data available for the selected filters.</p>
        </div>
      ) : (
        <>
          <CustomLegend />
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={transformedData}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="MRO_name" />
              <YAxis />
              <Tooltip />
              <Bar
                dataKey="averageThroughput"
                fill={(entry) => entry.fill} // Assign color dynamically based on 'fill' property
              >
                <LabelList dataKey="averageThroughput" position="top" style={{ fontSize: 12 }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
      {transformedData.length > 0 && (
        <div className="footer">
          <div className="footer-text">Overall Average Throughput</div>
          <div className="footer-number">90 Days Per Request</div>
        </div>
      )}
    </div>
  );
};

export default ThroughputBarChart;
