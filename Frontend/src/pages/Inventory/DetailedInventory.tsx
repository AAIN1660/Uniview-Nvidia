import React from "react";
import { useState, useEffect } from "react";
import styles from "./Inventory.module.css";
import Filters from "./Filters";
import { useNavigate, useLocation } from "react-router-dom";
import MockData from "./InventoryMockData";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCommentDots, faTimes } from "@fortawesome/free-solid-svg-icons";
import InventoryChatApp from "./InventoryChatApp";
// import ToolkitProvider from "react-bootstrap-table2-toolkit/dist/react-bootstrap-table2-toolkit.min";
// import BootstrapTable from "react-bootstrap-table-next";
// import paginationFactory from "react-bootstrap-table2-paginator";
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
  Cell,
} from "recharts";

const DetailedInventory = () => {
  const email = localStorage.getItem('email');
  const location = useLocation();
  const [filters, setFilters] = useState(location?.state?.filters);
  const [selectedMRO, setSelectedMRO] = useState(filters?.mroCenter);
  const [selectedComponentForChart, setSelectedComponentForChart] = useState(
    MockData?.sku_data?.[selectedMRO]?.[0]?.sku_name
  );
  const dropDownOptions = [
    ...new Set(MockData?.sku_data?.[selectedMRO]?.map((each) => each.sku_name)),
  ];
  const [tableData, setTableData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chartData, setChartData] = useState(null);
  const [reOrderAvg, setReOrderAvg] = useState(0);
  const navigate = useNavigate();
  const [averageSales, setAverageSales] = useState(null);

  const stringToDate = (dateString) => {
    const [month, day, year] = dateString.split("/");
    if (!month || !day || !year) {
      return null;
    }
    return new Date(year, month - 1, day);
  };

  const openChat = () => {
    setIsChatOpen(true);
  };

  const closeChat = () => {
    setIsChatOpen(false);
  };

  const getMonths = (fromDate, toDate): string[] => {
    if (!fromDate || !toDate) {
      return [];
    }
    const fromYear = fromDate.getFullYear();
    const fromMonth = fromDate.getMonth();
    const toYear = toDate.getFullYear();
    const toMonth = toDate.getMonth();
    const months: any[] = [];
    const monthname = [
      "",
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];

    for (let year = fromYear; year <= toYear; year++) {
      let monthNum = year === fromYear ? fromMonth : 0;
      const monthLimit = year === toYear ? toMonth : 11;

      for (; monthNum <= monthLimit; monthNum++) {
        let month = monthNum + 1;
        months.push(`${monthname[month]} ${year}`);
      }
    }
    return months;
  };

  const fetchAverageData = (tableDataAll) => {
    let proccesedSkus: any[] = [];
    const processedData: any[] = [];
    const allMonths: string[] = getMonths(
      stringToDate(filters.fromDate),
      stringToDate(filters.toDate)
    );

    allMonths?.forEach?.((monthToFind) => {
      proccesedSkus = [];
      tableDataAll?.[monthToFind]?.forEach((record) => {
        if (!proccesedSkus.includes(record?.sku_name)) {
          const allFunds = tableDataAll?.[monthToFind]?.filter(
            (elem) =>
              elem.sku_name === record.sku_name && elem.month === monthToFind
          );
          processedData.push({
            ...record,
            month: monthToFind,
            stock: (
              allFunds.reduce(
                (prev, curr, index) => prev + curr?.stock || 0,
                0
              ) / allFunds.length
            )?.toFixed(0),
            economical_order_quantity: (
              allFunds.reduce(
                (prev, curr, index) => prev + curr?.demand * 0.2,
                0
              ) / allFunds?.length
            )?.toFixed(0),
            safety_stock: record?.threshold_quantity,
            reorder_point: (record?.threshold_quantity * 1.1)?.toFixed(2),
            demand: (
              allFunds.reduce((prev, curr, index) => prev + curr?.demand, 0) /
              allFunds?.length
            )?.toFixed(0),
          });
          proccesedSkus.push(record.sku_name);
        }
      });
    });
    setTableData(processedData);
  };

  const getMonthYear = (date) => {
    const monthname = [
      "",
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    return `${monthname?.[Number(date?.split("/")?.[0])]} ${date?.split(
      "/"
    )?.[2]}`;
  };

  const validateTableData = () => {
    const tableDataAll: {} = {};
    MockData?.data?.forEach((eachRecord) => {
      if (eachRecord?.mro_name === selectedMRO) {
        let toDateStock = MockData?.sku_data?.[selectedMRO]?.filter(
          (each) =>
            each?.sku_name === eachRecord?.sku_name &&
            each?.date === filters.toDate
        )?.[0]?.stock;
        let skuData = MockData?.sku_data?.[selectedMRO]?.filter(
          (each) =>
            each?.sku_name === eachRecord?.sku_name &&
            stringToDate(each?.date) >= stringToDate(filters?.fromDate) &&
            stringToDate(each?.date) <= stringToDate(filters?.toDate) &&
            (eachRecord.threshold_quantity > toDateStock ||
              (toDateStock < eachRecord.threshold_quantity * 1.1 &&
                toDateStock > eachRecord?.threshold_quantity &&
                each?.date === filters?.toDate))
        );
        skuData.forEach((sku) => {
          let month = getMonthYear(sku?.date);
          if (!tableDataAll?.[month]) {
            tableDataAll[month] = [];
          }
          tableDataAll?.[month]?.push({
            ...eachRecord,
            month: month,
            stock: sku.stock,
            economical_order_quantity: sku.demand * 0.2,
            safety_stock: eachRecord?.threshold_quantity,
            reorder_point: (eachRecord?.threshold_quantity * 1.1)?.toFixed(2),
            date: sku?.date,
            demand: sku?.demand,
          });
        });
      }
    });
    fetchAverageData(tableDataAll);
  };

  useEffect(() => {
    validateTableData();
  }, []);

  const columns = [
    {
      dataField: "month",
      text: "Month",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "sku_name",
      text: "Component",
      headerAlign: "left",
      align: "left",
      formatter: (cell: any, row: any) => (
        <p onClick={() => formatChartData(row)}>{row?.sku_name}</p>
      ),
    },
    {
      dataField: "demand",
      text: "Average Sales",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "avg_lead_time",
      text: "Avg Lead Time",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "demand_std_dev",
      text: "Demand Std Dev",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "lead_time_std_dev",
      text: "Lead Time Std Dev",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "service_factor",
      text: "Service Factor",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "stock",
      text: "Current Stock",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "economical_order_quantity",
      text: "Economical Order Quantity",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "safety_stock",
      text: "Safety Stock",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "reorder_point",
      text: "Reorder Point",
      headerAlign: "left",
      align: "left",
    },
  ];

  function getCurrentWeekNumber(passeddate) {
    const dayNo = Number(passeddate?.split?.("/")?.[1]);
    if (dayNo < 7) {
      return 1;
    } else if (dayNo < 14) {
      return 2;
    } else if (dayNo < 21) {
      return 3;
    } else {
      return 4;
    }
  }

  // function getCurrentWeekNumber(date) {
  //   const convertedDate = stringToDate(date);
  //   const yearStart = new Date(convertedDate.getFullYear(), 0, 1);
  //   const weekNumber = Math.ceil(
  //     ((convertedDate - yearStart) / 86400000 + yearStart.getDay() + 1) / 7
  //   );
  //   return Math.floor(weekNumber % 4);
  // }

  const formatChartData = (row) => {
    let data = MockData?.sku_data?.[selectedMRO]?.filter(
      (item) =>
        item?.sku_name === row?.sku_name &&
        stringToDate(item?.date) >= stringToDate(filters.fromDate) &&
        stringToDate(item?.date) <= stringToDate(filters.toDate)
    );

    let reOrderPoint = tableData?.filter(
      (each) => each.sku_name === row?.sku_name
    )?.[0]?.reorder_point;

    let week1Data = data
      ?.filter((each) => getCurrentWeekNumber(each.date) === 1)
      ?.reduce((prev, curr, index) => prev + curr.stock, 0);
    let week2Data = data
      ?.filter((each) => getCurrentWeekNumber(each.date) === 2)
      .reduce((prev, curr, index) => prev + curr.stock, 0);
    let week3Data = data
      ?.filter((each) => getCurrentWeekNumber(each.date) === 3)
      .reduce((prev, curr, index) => prev + curr.stock, 0);
    let week4Data = data
      ?.filter((each) => getCurrentWeekNumber(each.date) === 4)
      .reduce((prev, curr, index) => prev + curr.stock, 0);
    let chartweeklydata = [
      {
        label: "Week 1",
        stock: week1Data,
        reorderPoint: reOrderPoint,
        skuName: row?.sku_name,
      },
      {
        label: "Week 2",
        stock: week2Data,
        reorderPoint: reOrderPoint,
        skuName: row?.sku_name,
      },
      {
        label: "Week 3",
        stock: week3Data,
        reorderPoint: reOrderPoint,
        skuName: row?.sku_name,
      },
      {
        label: "Week 4",
        stock: week4Data,
        reorderPoint: reOrderPoint,
        skuName: row?.sku_name,
      },
    ];
    setChartData(chartweeklydata);
  };

  const pagination = paginationFactory({
    page: 1,
    sizePerPage: 10,
    lastPageText: ">>",
    firstPageText: "<<",
    nextPageText: ">",
    prePageText: "<",
    showTotal: true,
    alwaysShowAllBtns: true,
    hideSizePerPage: false,
  });

  const goBackToInventory = () => {
    navigate("/layout/inventory", { state: { filters: filters } });
  };
  return (
    <div className={styles.inventoryContainer}>
      <button className={styles.chatButton} onClick={openChat}>
        <FontAwesomeIcon icon={faCommentDots} />
      </button>
      <div className={styles.allContent}>
        <Filters disableAll={true} filters={filters} setFilters={setFilters} />

        <button
          onClick={goBackToInventory}
          className={styles.closeBtn}
          style={{ border: "none", margin: "16px", float: 'right' }}
        >
          Close <FontAwesomeIcon icon={faTimes} />
        </button>

        <div className={styles.healthSummary}>
          <div className={styles.titleRow}>
            <h5>EXPECTED COMPONENT TO BE REORDERED</h5>
          </div>
          {tableData && (
            <div className={styles.summaryContainer}>
              {/* <ToolkitProvider
                bootstrap4
                keyField="id"
                data={tableData || []}
                columns={columns}
                bordered={false}
              >
                {(props) => (
                  <div>
                    <BootstrapTable
                      {...props.baseProps}
                      // other BootstrapTable props
                      bordered={false}
                      noDataIndication={loading ? "Loading..." : "No Records"}
                      pagination={pagination}
                    />
                  </div>
                )}
              </ToolkitProvider> */}
            </div>
          )}
          {chartData && (
            <div className={styles.summaryContainer}>
              <div className={styles.summary3}>
                <h6>{chartData?.[0]?.skuName}</h6>
                <div className={styles.summary3container}>
                  <div className={styles.summary3Filters}>
                    <h6>
                      Reorder point for {chartData?.[0]?.sku_name}:{" "}
                      {chartData?.[0]?.reorderPoint}{" "}
                    </h6>
                    <div className={styles.barChart}>
                      <BarChart
                        width={900}
                        height={300}
                        data={chartData}
                        margin={{
                          top: 30,
                          right: 30,
                          left: 20,
                          bottom: 5,
                        }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="label" />
                        <YAxis />
                        <Tooltip />
                        <Legend />

                        <Bar dataKey="stock" isAnimationActive={true}>
                          {chartData?.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={
                                entry.stock > entry.reorderPoint
                                  ? "#684281"
                                  : "#C1A0D7"
                              }
                            />
                          ))}
                        </Bar>
                        <ReferenceLine
                          y={Number(chartData?.[0]?.reorderPoint)}
                          stroke="red"
                          strokeDasharray="4 4"
                          label={`Reorder Point=${chartData?.[0]?.reorderPoint}`}
                        />
                      </BarChart>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {isChatOpen && <InventoryChatApp onClose={closeChat} />}
    </div>
  );
};

export default DetailedInventory;
