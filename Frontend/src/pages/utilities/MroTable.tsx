import React, { useState, useEffect } from 'react';
import ReactPaginate from 'react-paginate';
import { data } from './SimuLatorMockData'; // Adjust import path as per your project structure
import './MroTable.css';

const MroTable = ({ filters }) => {
  const [currentPage, setCurrentPage] = useState(0);
  const itemsPerPage = 5;
  const { selectedMonth, selectedMROCenter } = filters;

  const handlePageClick = (data) => {
    setCurrentPage(data.selected);
  };

  // Filter data based on selectedMonth and selectedMROCenter
  const filteredData = data.filter(item => {
    // Filter by selected month
    if (selectedMonth) {
      const [selectedYear, selectedMonthNum] = selectedMonth.split('-').map(Number);
      const startDate = new Date(selectedYear, selectedMonthNum - 1, 1);
      const endDate = new Date(selectedYear, selectedMonthNum - 1, new Date(selectedYear, selectedMonthNum, 0).getDate()); // Last day of the selected month

      const itemStartDateParts = item.Start_date.split('-').map(Number);
      const itemStartDate = new Date(itemStartDateParts[2], itemStartDateParts[1] - 1, itemStartDateParts[0]);
      const itemEndDateParts = item.Estimated_completion_date.split('-').map(Number);
      const itemEndDate = new Date(itemEndDateParts[2], itemEndDateParts[1] - 1, itemEndDateParts[0]);

      // Check if item's start or end date falls within the selected month's range
      if (!(itemStartDate >= startDate && itemStartDate <= endDate) &&
          !(itemEndDate >= startDate && itemEndDate <= endDate) &&
          !(itemStartDate <= startDate && itemEndDate >= endDate)) {
        return false;
      }
    }

    // Filter by selected MRO center
    if (selectedMROCenter && item.MRO_name !== selectedMROCenter) {
      return false;
    }

    return true;
  });

  const offset = currentPage * itemsPerPage;
  const currentPageData = filteredData.slice(offset, offset + itemsPerPage);

  return (
    <div className="table-container mrotablecontainer">
      <table>
        <thead>
          <tr>
            <th>Service Request ID</th>
            <th>Engine ID</th>
            <th>Recommended MRO Center</th>
            <th>Geo Location</th>
            <th>Inventory Status</th>
            <th>Resource Availability</th>
            <th>Cost Considerations</th>
            <th>Planned Start Date</th>
            <th>Estimated Completion Date</th>
            <th style={{ minWidth: '150px' }}>Reason</th>
          </tr>
        </thead>
        <tbody>
          {currentPageData.map((item) => (
            <tr key={item.id}>
              <td>{item.id}</td>
              <td>{item.Engine_id}</td>
              <td>{item.MRO_name}</td>
              <td>{item.GeoLocation}</td>
              <td>{item.Inventory_status}</td>
              <td>{item.Resource_availability}</td>
              <td>{item.Cost_consideration}</td>
              <td>{item.Start_date}</td>
              <td>{item.Estimated_completion_date}</td>
              <td style={{ minWidth: '150px' }}>{item.Reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {filteredData.length === 0 && (
        <div className="no-data-message">No data available for selected filters.</div>
      )}
      <ReactPaginate
        previousLabel={"Previous"}
        nextLabel={"Next"}
        breakLabel={"..."}
        breakClassName={"break-me"}
        pageCount={Math.ceil(filteredData.length / itemsPerPage)}
        marginPagesDisplayed={2}
        pageRangeDisplayed={5}
        onPageChange={handlePageClick}
        containerClassName={"pagination"}
        subContainerClassName={"pages pagination"}
        activeClassName={"active"}
      />
    </div>
  );
};

export default MroTable;
