import React, { useEffect, useState } from "react";
import styles from "./Filters.module.css";

const Filters = ({ setFilters, filters, disableAll = false }) => {
  const [fromDate, setFromDate] = useState(
    convertToInputSupportedDate(filters.fromDate)
  );
  const [toDate, setToDate] = useState(
    convertToInputSupportedDate(filters.toDate)
  );

  const [mroCenter, setMroCenter] = useState(filters?.mroCenter)
  const [granularity, setGranularity] = useState(filters?.granularity)

  const handleChange = (key: string, value) => {
    let changedFilters = { ...filters, [key]: value };
    setFilters(changedFilters);
  };

  const clearFilters = () => {
    setFilters({
      fromDate: "06/01/2024",
      toDate: "06/30/2024",
      mroCenter: "MRO Center A",
      granularity: "Weekly",
    });
  };

  const formatDate = (date: Date | null | undefined) => {
    if (!(date instanceof Date)) return "";
    const day = date.getUTCDate().toString().padStart(2, "0");
    const month = (date.getUTCMonth() + 1).toString().padStart(2, "0");
    const year = date.getUTCFullYear().toString();
    return `${month}/${day}/${year}`;
  };

  function convertToInputSupportedDate(date) {
    if (!date || date === "") {
      return;
    }
    const [month, day, year] = date?.split("/");
    return `${year}-${month}-${day}`;
  }

  useEffect(() => {
    if (fromDate !== "" && toDate !== "") {
      setFilters((prev) => {
        return {
          ...prev,
          fromDate: formatDate(new Date(fromDate)),
          toDate: formatDate(new Date(toDate)),
        };
      });
    }
  }, [fromDate, toDate]);

  useEffect(() => {
      if(filters?.fromDate !== '') {
        setFromDate(convertToInputSupportedDate(filters?.fromDate))
      }
      if(filters?.toDate !== '') {
        setToDate(convertToInputSupportedDate(filters?.toDate))
      }
      if(filters?.mroCenter !== '') {
        setMroCenter(filters?.mroCenter)
      }
      if(filters?.granularity !== '') {
        setGranularity(filters?.granularity)
      }
  }, [filters])

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
            value={fromDate}
            disabled={disableAll}
            onChange={(e) => {
              setFromDate(e.target.value);
            }}
          />
        </div>
        <div>
          <label>To Date</label>
          <input
            type="date"
            placeholder="Select a date..."
            style={{ width: 200 }}
            disabled={disableAll}
            value={toDate}
            onChange={(e) => {
              setToDate(e.target.value);
            }}
          />
        </div>
        <button disabled={disableAll} onClick={clearFilters}>
          Reset Filters
        </button>
      </div>
      <div>
        <div>
          <label>MRO Center</label>
          <select
            disabled={disableAll}
            onChange={(e) => handleChange("mroCenter", e.target.value)}
            value={mroCenter}
          >
            <option>MRO Center A</option>
            <option>MRO Center B</option>
            <option>MRO Center C</option>
          </select>
        </div>
        <div>
          <label>Granularities</label>
          <select
            disabled={true}
            onChange={(e) => handleChange("granularity", e.target.value)}
            defaultValue={granularity}
          >
            <option>Weekly</option>
            <option>Monthly</option>
            <option>Yearly</option>
          </select>
        </div>
      </div>
      {/* <div>
        <div>
          <label>Request</label>
          <div className={styles.actionBtns}>
            <button
              className={filters?.request === "All" ? styles.activeButton : ""}
              onClick={(e) => handleChange("request", e.target.textContent)}
            >
              All
            </button>
            <button
              className={
                filters?.request === "Pending" ? styles.activeButton : ""
              }
              onClick={(e) =>
                handleChange("request", (e.target as HTMLElement).textContent)
              }
            >
              Pending
            </button>
            <button
              className={
                filters?.request === "Completed" ? styles.activeButton : ""
              }
              onClick={(e) =>
                handleChange("request", (e.target as HTMLElement).textContent)
              }
            >
              Completed
            </button>
          </div>
        </div>
      </div> */}
    </div>
  );
};

export default Filters;
