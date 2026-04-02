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
      request: "All",
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
      </div>
    </div>
  );
};

export default Filters;
