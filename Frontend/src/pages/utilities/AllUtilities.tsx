import React, { useState } from 'react';
import MroTable from './MroTable';
import BarGraph from './BarGraph';
import ThroughputBarChart from './ThroughputBarChart';
import SimulatorFilter from './SimulatorFilter';
import { data } from './SimuLatorMockData'; // Import your mock data here

const AllUtilities = () => {
  const [filters, setFilters] = useState({
    selectedMonth: '',
    selectedMROCenter: '',
  });

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
  };

  return (
    <div style={{ overflowX: 'hidden' }}>
      <div className='row'>
        <SimulatorFilter filters={filters} onFilterChange={handleFilterChange} />
        <div className='col-6'>
          <BarGraph selectedMonth={filters.selectedMonth} selectedMROCenter={filters.selectedMROCenter} />
        </div>
        <div className='col-6'>
          <ThroughputBarChart selectedMonth={filters.selectedMonth} selectedMROCenter={filters.selectedMROCenter} />
        </div>
        <div className='col-12'>
          <MroTable data={data} filters={filters} />
        </div>
      </div>
    </div>
  );
};

export default AllUtilities;
