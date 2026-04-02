import React from "react";
import { useRef, useState, useEffect } from "react";
import { DefaultButton, Panel } from "@fluentui/react";
import styles from "../pages/service/Service.module.css";
// import ToolkitProvider from "react-bootstrap-table2-toolkit/dist/react-bootstrap-table2-toolkit.min";
// import BootstrapTable from "react-bootstrap-table-next";
// import paginationFactory from "react-bootstrap-table2-paginator";
import Filters from "./Filters";
import Mockdata from "../pages/service/ServiceMockData";
import StimulatorMockData from "./SimulatorMockData";

import {
  ClipboardTextEditRegular,
  DismissRegular,
  DocumentPdfRegular,
  FolderOpenRegular,
  PrintRegular,
  SearchRegular,
  ServiceBellRegular,
  SparkleFilled,
  TableCalculatorRegular,
  TextBulletListCheckmarkFilled,
  TextWordCountRegular,
} from "@fluentui/react-icons";
import { useNavigate } from "react-router-dom";
import {
  formatCurrentDate,
  generateAlphaNumericCode,
  isDate,
  stringToDate,
} from "../pages/service/Helper";
import ChatButton from "../pages/service/ChatButton";
const Utilities = () => {
  const email = localStorage.getItem('email');
  const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [filteredData, setFilteredData] = useState<any>(null);
  const searchRef = useRef<HTMLInputElement>();
  const [filters, setFilters] = useState({
    search: "",
    fromDate: "",
    toDate: "",
    mroCenter: "",
  });
  const [summaryCount, setSummaryCount] = useState({
    requests: 0,
    open_requests: 0,
    closed_requests: 0,
    in_progress: 0,
  });
  const navigate = useNavigate();

  const navigateToSR = (sr_num) => {
    navigate(`/layout/service/${sr_num}`);
  };

  // const pagination = paginationFactory({
  //   page: 1,
  //   sizePerPage: 5,
  //   lastPageText: ">>",
  //   firstPageText: "<<",
  //   nextPageText: ">",
  //   prePageText: "<",
  //   showTotal: true,
  //   alwaysShowAllBtns: true,
  //   hideSizePerPage: false,
  // });

  const columns = [
    {
      dataField: "Rank",
      text: "Rank",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "Engine_id",
      text: "Engine Id",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "engine_type",
      text: "Engine Type",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "current_status",
      text: "Current Status",
      sort: true,
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "Priority",
      text: "Priority Score",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "Estimated_completion_date",
      text: "Estimated Completion Date",
      headerAlign: "left",
      align: "left",
    },
  ];

  const existingData = localStorage.getItem("sserviceData");
  if (!existingData || existingData?.length === 0) {

    const updatedMockData = StimulatorMockData?.map?.((dataEntry) => {
      if(email && email !== "") {
        dataEntry.created_by = email
      }
      return dataEntry
    })

    setData(updatedMockData);
    localStorage.setItem("sserviceData", JSON.stringify(updatedMockData));
  }
  else if (!data) {
    let dataString = localStorage.getItem("sserviceData");

    if (dataString) {
      setData(JSON.parse(dataString));
    }
  }

  const handleFilteredData = () => {
    if (data && data?.length > 0) {
      let existingData = [...data];

      if (filters.search !== "") {
        let searchTerm = filters?.search?.toLowerCase();
        existingData = existingData.filter((each) => {
          return (
            each?.Engine_id?.toLowerCase().includes(searchTerm) ||
            each?.engine_type?.toLowerCase().includes(searchTerm) ||
            each?.current_status?.toLowerCase().includes(searchTerm) ||
            each?.Priority?.toLowerCase().includes(searchTerm) ||
            each?.Estimated_completion_date?.toLowerCase().includes(searchTerm)
          );
        });
      }

      if (filters.fromDate !== "" && filters.toDate !== "") {
        existingData = existingData.filter((each) => {
          let srDate = stringToDate(each?.request_created_date);
          let fromDate = new Date(filters?.fromDate);
          let toDate = new Date(filters?.toDate);
          if (
            srDate &&
            isDate(filters?.fromDate) &&
            isDate(filters?.toDate) &&
            isDate(srDate)
          ) {
            return (
              srDate?.getTime() >= fromDate?.getTime() &&
              srDate?.getTime() <= toDate?.getTime()
            );
          }
          return false;
        });
      }


    if (filters.mroCenter !== "") {
        existingData = existingData.filter((record) => {
          return record.MRO_name === filters.mroCenter;
        });
      }

      if (searchRef.current && filters.search === "") {
        searchRef.current.value = "";
      }

      const newSummary = {
        requests: existingData?.length,
        open_requests: existingData?.filter(
          (record) =>
            record?.current_status === "In Maintenance" ||
            record?.current_status === "Waiting for Parts" ||
            record?.current_status === "Diagnostic Testing"
        )?.length,
        closed_requests: existingData?.filter(
          (record) =>
            record?.created_by === email &&
            (record?.current_status === "Pending Inspection" || record?.current_status === "Engine Overhaul")
        )?.length,
        in_progress: existingData?.filter(
          (record) =>
            record?.created_by === email &&
            (record?.current_status === "Pending Inspection")
        )?.length
      };

      setSummaryCount(newSummary);
      setFilteredData(existingData);

    }
  };

  useEffect(() => {
    handleFilteredData();
  }, [filters, data]);

  return (
    <div className={styles.serviceContainer}>
      {/* <div>
        <Panel
          headerText="Configure answer generation"
          isOpen={isConfigPanelOpen}
          isBlocking={false}
          onDismiss={() => setIsConfigPanelOpen(false)}
          closeButtonAriaLabel="Close"
          onRenderFooterContent={() => (
            <DefaultButton onClick={() => setIsConfigPanelOpen(false)}>
              Close
            </DefaultButton>
          )}
          isFooterAtBottom={true}
        ></Panel>
      </div> */}
      <div className={styles.allServicesContent}>
        <Filters filters={filters} setFilters={setFilters} />
        {/* <div
          className={styles.chatBtnContainer}
          onClick={() => setIsConfigPanelOpen(true)}
        >
          <SparkleFilled
            fontSize={"24px"}
            aria-hidden="true"
            aria-label="Chat logo"
          />
          <button
            className={styles.chatBtn}
          >
            Chat
          </button>
        </div> */}
        <div className={styles.dashboard}>
          <div className={styles.dashboardUpper}>
            <div className={styles.box}>
              <h5>Total REQUESTS</h5>
              {/* <h3>85</h3> */}
              <h3>{summaryCount?.requests}</h3>
              <span>
                <TableCalculatorRegular />
              </span>
            </div>
            <div className={styles.box}>
              <h5>In-progress Request</h5>
              {/* <h3>10</h3> */}
              <h3>{summaryCount?.in_progress}</h3>
              <span>
                <FolderOpenRegular />
              </span>
            </div>
            <div className={styles.box}>
              <h5>OPEN REQUESTS</h5>
              {/* <h3>5</h3> */}
              <h3>{summaryCount?.open_requests}</h3>
              {/* <h3>{summaryCount?.closed_requests}</h3> */}
              <span>
                <TextBulletListCheckmarkFilled />
              </span>
            </div>
            <div className={styles.box}>
              <h5>Completed Requests</h5>
              {/* <h3>70</h3> */}
              <h3>{summaryCount?.closed_requests}</h3>
              {/* <h3>{summaryCount?.notifications}</h3> */}
              <span>
                <ServiceBellRegular />
              </span>
            </div>
            <div className={styles.box}>
              <h5>Average Throughput</h5>
              <h3>{Math.floor(Math.random() * (99 - 80) ) + 80}</h3>
              {/* <h3>{summaryCount?.notifications}</h3> */}
              <span>
                <TextWordCountRegular />
              </span>
            </div>
          </div>
          <div className={styles.dashboardMiddle}>
            <input type="text" placeholder="SEARCH" ref={searchRef} />
            <SearchRegular
              onClick={() =>
                setFilters({
                  ...filters,
                  search: searchRef?.current?.value || "",
                })
              }
            />
          </div>

          <div className={styles.dashboardLower}>
            {/* <ToolkitProvider
              bootstrap4
              keyField="id"
              data={filteredData || []}
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
          {/* <ChatButton
            createNewTicket={createNewTicket}
            doesExistTicket={doesExistTicket}
          /> */}
        </div>
      </div>
    </div>
  );
};

export default Utilities;
