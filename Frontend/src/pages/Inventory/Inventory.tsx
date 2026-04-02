import React from "react";
import { useState, useEffect } from "react";
import styles from "./Inventory.module.css";
import Filters from "./Filters";
import {
  BarChart,
  Bar,
  Rectangle,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";

import { useLocation, useNavigate } from "react-router-dom";
import ChatButton from "./ChatButton";
import MockData from "./InventoryMockData";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCommentDots } from "@fortawesome/free-solid-svg-icons";
import InventoryChatApp from "./InventoryChatApp";
const Inventory = () => {
  const email = localStorage.getItem('email');
  const [selectedMRO, setSelectedMRO] = useState("MRO Center A");
  const [selectedGranularity, setSelectedGranularity] = useState("Weekly");
  const [selectedComponentForChart, setSelectedComponentForChart] = useState(
    MockData?.sku_data?.[selectedMRO]?.[0]?.sku_name
  );
  const dropDownOptions = [
    ...new Set(MockData?.sku_data?.[selectedMRO]?.map((each) => each.sku_name)),
  ];
  const location = useLocation();
  const passedFilters = location?.state?.filters;
  const passedFiltersFromDate = !passedFilters || passedFilters?.fromDate === '' ? '06/01/2024' : passedFilters?.fromDate;
  const passedFiltersToDate = !passedFilters || passedFilters?.toDate === '' ? '06/30/2024' : passedFilters?.toDate;
  const passedFiltersMRO = !passedFilters || passedFilters?.mroCenter === '' ? 'MRO Center A' : passedFilters?.mroCenter;
  const passedFiltersGrnularity = !passedFilters || passedFilters?.granularity === '' ? 'Weekly' : passedFilters?.granularity;


  const [filters, setFilters] = useState({
    fromDate: passedFiltersFromDate,
    toDate: passedFiltersToDate,
    mroCenter: passedFiltersMRO,
    granularity: passedFiltersGrnularity,
  });
  const [fromDate, setFromDate] = useState(filters?.fromDate);
  const [toDate, setToDate] = useState(filters?.toDate);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const navigate = useNavigate();

  const openChat = () => {
    setIsChatOpen(true);
  };

  const closeChat = () => {
    setIsChatOpen(false);
  };

  const openDetailedScreen = () => {
    navigate("/layout/detailedinventory", { state: { filters: filters } });
  };

  const stringToDate = (dateString) => {
    const [month, day, year] = dateString.split("/");
    if (!month || !day || !year) {
      return null;
    }
    return new Date(year, month - 1, day);
  };

  const prepareGraphData = () => {
    const fromInDate = stringToDate(fromDate);
    const toInDate = stringToDate(toDate);

    let finalData = MockData?.sku_data?.[selectedMRO]?.filter(
      (sku) =>
        sku?.sku_name === selectedComponentForChart &&
        stringToDate(sku?.date) >= fromInDate &&
        stringToDate(sku?.date) <= toInDate
    );
    let rpoint =
      MockData?.data?.filter(
        (data) => data.sku_name === selectedComponentForChart
      )?.[0]?.threshold_quantity * 1.1;
    return {
      data: finalData,
      reorderpoint: rpoint?.toFixed(0),
    };
  };
  const getComponentsData = () => {
    let componentsData: any[] = [];
    let max_demand = 0;
    MockData?.sku_data?.[selectedMRO]?.forEach((item) => {
      let threshold =
        MockData?.data?.filter(
          (each) =>
            each.mro_name === selectedMRO && each.sku_name === item.sku_name
        )?.[0]?.threshold_quantity || 0;
      if (item.stock < threshold && item?.date === toDate) {
        componentsData.push(item);
      } else if (
        item.stock < (threshold * 11) / 10 &&
        item.stock > threshold &&
        item.date === toDate
      ) {
        componentsData.push(item);
      }
      if (item.demand > max_demand) {
        max_demand = item.demand;
      }
    });
    return { data: componentsData, max_demand: max_demand };
  };

  const getNnoOfSKUS = () => {
    return (
      MockData?.sku_data?.[selectedMRO]?.filter((each) => each?.date === toDate)
        ?.length || 0
    );
  };

  const getInventoryBelowSafetyStock = () => {
    let count = 0;
    MockData?.sku_data?.[selectedMRO]?.forEach((item) => {
      let threshold =
        MockData?.data?.filter(
          (each) =>
            each.mro_name === selectedMRO && each.sku_name === item.sku_name
        )?.[0]?.threshold_quantity || 0;
      if (item.stock < threshold && item?.date === toDate) {
        count = count + 1;
      }
    });
    return count;
  };

  const getInventoryNearOrderPoint = () => {
    let count = 0;
    MockData?.sku_data?.[selectedMRO]?.forEach((item) => {
      let threshold =
        MockData?.data?.filter(
          (each) =>
            each.mro_name === selectedMRO && each.sku_name === item.sku_name
        )?.[0]?.threshold_quantity || 0;
      if (
        item.stock < (threshold * 11) / 10 &&
        item.stock > threshold &&
        item.date === toDate
      ) {
        count = count + 1;
      }
    });
    return count;
  };

  useEffect(() => {
    if (filters.fromDate !== "") {
      setFromDate(filters.fromDate);
    }
    if (filters.toDate !== "") {
      setToDate(filters.toDate);
    }
    if (filters.mroCenter !== "") {
      setSelectedMRO(filters.mroCenter);
    }
    if (filters.granularity !== "") {
      setSelectedGranularity(filters.granularity);
    }
  }, [filters]);

  return (
    <div className={styles.inventoryContainer}>
      <button className={styles.chatButton} onClick={openChat}>
        <FontAwesomeIcon icon={faCommentDots} />
      </button>
      <div className={styles.allContent}>
        <Filters filters={filters} setFilters={setFilters} />
        <div className={styles.healthSummary}>
          <h5>Inventory Health Summary</h5>
          <div className={styles.summaryContainer}>
            <div className={styles.summary1}>
              <h5>SUMMARY</h5>
              <table>
                <tr>
                  <td>No. of SKUs</td>
                  <td>{getNnoOfSKUS()}</td>
                </tr>
                <tr>
                  <td>SKUs with inventory below safety stock</td>
                  <td>{getInventoryBelowSafetyStock()}</td>
                </tr>
                <tr>
                  <td>SKUs with inventory nearing reorder point</td>
                  <td>{getInventoryNearOrderPoint()}</td>
                </tr>
                <tr>
                  <td>SKUs with optimal inventory</td>
                  <td>
                    {getNnoOfSKUS() -
                      getInventoryBelowSafetyStock() -
                      getInventoryNearOrderPoint()}
                  </td>
                </tr>
              </table>
            </div>
            <div className={styles.summary2}>
              <h4 className={styles.summary2Title}>
                EXPECTED COMPONENT TO BE REORDERED
              </h4>
              {getComponentsData()?.data?.map((sku, index) => {
                return (
                  <div className={styles.eachComponent}>
                    <h6>{sku.sku_name}</h6>
                    <div>
                      <div
                        style={{
                          width: `${(sku.demand / getComponentsData().max_demand) * 100
                            }%`,
                        }}
                        className={styles.progess}
                      ></div>
                    </div>
                    <h6>{sku.demand}</h6>
                  </div>
                );
              })}
              <button
                onClick={openDetailedScreen}
                className={styles.summaryButton}
              >
                Details
              </button>
            </div>
          </div>
          <div className={styles.summaryContainer}>
            <div className={styles.summary3}>
              <h6>DEMAND AND AVAILABLE STOCK</h6>
              <div className={styles.summary3container}>
                <div className={styles.summary3Filters}>
                  <div className={styles.chartLabel}>
                    <label>COMPONENT</label>
                    <label>
                      Reorder point: {prepareGraphData().reorderpoint}
                    </label>
                  </div>
                  <select
                    value={selectedComponentForChart}
                    onChange={(e) =>
                      setSelectedComponentForChart(e.target.value)
                    }
                  >
                    {dropDownOptions?.map((sku) => {
                      return <option>{sku}</option>;
                    })}
                  </select>
                  <div className={styles.barChart}>
                    <BarChart
                      width={1400}
                      height={300}
                      data={prepareGraphData()?.data}
                      margin={{
                        top: 30,
                        right: 30,
                        left: 20,
                        bottom: 5,
                      }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar
                        dataKey="demand"
                        fill="#8884d8"
                        activeBar={<Rectangle fill="#8884d8" stroke="blue" />}
                      />
                      <Bar
                        dataKey="stock"
                        fill="#82ca9d"
                        activeBar={<Rectangle fill="#82ca9d" stroke="purple" />}
                      />
                      <ReferenceLine
                        y={Number(prepareGraphData().reorderpoint)}
                        stroke="red"
                        strokeDasharray="4 4"
                        label={`Reorder Point=${prepareGraphData().reorderpoint
                          }`}
                      />
                    </BarChart>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      {isChatOpen && <InventoryChatApp onClose={closeChat} />}
    </div>
  );
};

export default Inventory;
