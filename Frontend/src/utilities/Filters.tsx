import React from "react";
import styles from "./Filters.module.css";
import { DatePicker } from "@fluentui/react";

const Filters = ({ setFilters, filters }) => {
  const handleChange = (key: string, value) => {
    let changedFilters = { ...filters, [key]: value };
    setFilters(changedFilters);
  };

  const clearFilters = () => {
    setFilters({
      search: "",
      fromDate: "",
      toDate: "",
      mroCenter: ""
    });
  };

  const formatDate = (date: Date | null | undefined) => {
    if (!(date instanceof Date)) return "";
    const day = date.getDate().toString().padStart(2, "0");
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const year = date.getFullYear().toString().slice(-2);
    return `${month}/${day}/${year}`;
  };

  return (
    <div className={styles.filterContainer}>
      <div>
        {/* <div>
          <input type="text" placeholder="Search Here" />
        </div>
        <div>
          <button>Search</button>
        </div> */}
        <div>
          <label>From Date ...</label>
          <input
            type="date"
            placeholder="Select a date..."
            style={{ width: 200 }} 
            value={
              filters?.fromDate ? filters.fromDate.toISOString().split("T")[0] : ""
            }
            onChange={(e) => {
              const selectedDate = new Date(e.target.value);
              handleChange("fromDate", selectedDate);
            }}
          />
        </div>
        <div>
          <label>To Date</label>
          <input
            type="date"
            placeholder="Select a date..."
            style={{ width: 200 }} 
            value={
              filters?.toDate ? filters.toDate.toISOString().split("T")[0] : ""
            }
            onChange={(e) => {
              const selectedDate = new Date(e.target.value);
              handleChange("toDate", selectedDate);
            }}
          />
        </div>
        <button onClick={clearFilters}>Reset Filters</button>
      </div>
      <div>
      <div>
      <label>MRO Center</label>
          <select
            value={filters.mroCenter}
            onChange={(e) => handleChange("mroCenter", e.target.value)}
          >
            <option value="">Select MRO Center</option>
            <option value="MRO Center A">MRO Center A</option>
            <option value="MRO Center B">MRO Center B</option>
            <option value="MRO Center C">MRO Center C</option>
            <option value="MRO Center D">MRO Center D</option>
            <option value="MRO Center E">MRO Center E</option>
          </select>
        </div>
      </div>
    </div>
  );
};

export default Filters;
