import React from 'react';
import styles from './SimulatorFilter.module.css';

const SimulatorFilter = ({ filters, onFilterChange }) => {
  const handleMonthChange = (e) => {
    const selectedMonth = e.target.value ? new Date(e.target.value).toISOString().substring(0, 7) : '';
    onFilterChange({ ...filters, selectedMonth });
  };

  const handleMROCenterChange = (e) => {
    const selectedMROCenter = e.target.value === 'selectAll' ? '' : e.target.value;
    onFilterChange({ ...filters, selectedMROCenter });
  };

  const clearFilters = () => {
    onFilterChange({
      selectedMonth: '',
      selectedMROCenter: '',
    });
  };

  return (
    <div className={styles.filterContainer}>
      <div>
        <div className='ms-5'>
          <label>Select Month:</label>
          <input
            type="month"
            value={filters.selectedMonth}
            onChange={handleMonthChange}
            style={{ width: 200 }} 
          />
        </div>
        <div>
          <label>Select MRO Center:</label>
          <select
            value={filters.selectedMROCenter || 'selectAll'}
            onChange={handleMROCenterChange}
            style={{ width: 200, height: 29, marginBottom: '6px' }} 
          >
            <option value="selectAll">Select All</option>
            <option value="MRO Center A">MRO Center A</option>
            <option value="MRO Center B">MRO Center B</option>
            <option value="MRO Center C">MRO Center C</option>
          </select>
        </div>
        <button onClick={clearFilters}>Reset Filters</button>
      </div>
    </div>
  );
};

export default SimulatorFilter;
