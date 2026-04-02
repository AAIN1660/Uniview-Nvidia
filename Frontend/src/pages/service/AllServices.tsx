import React from "react";
import { useRef, useState, useEffect } from "react";
import { DefaultButton, Panel } from "@fluentui/react";
import styles from "./Service.module.css";
// import ToolkitProvider from "react-bootstrap-table2-toolkit/dist/react-bootstrap-table2-toolkit.min";
// import BootstrapTable from "react-bootstrap-table-next";
// import paginationFactory from "react-bootstrap-table2-paginator";
import Filters from "./Filters";
import Mockdata from "./ServiceMockData";

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
} from "./Helper";
import ChatButton from "./ChatButton";
const AllServices = () => {
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
    request: "All",
  });
  const [summaryCount, setSummaryCount] = useState({
    requests: 0,
    open_requests: 0,
    closed_requests: 0,
    notifications: 0,
  });
  const navigate = useNavigate();

  const navigateToSR = (sr_num) => {
    navigate(`/layout/service/${sr_num}`);
  };

  

  const columns = [
    {
      dataField: "sr_number",
      text: "SR Number",
      headerAlign: "left",
      align: "left",
      formatter: (cell: any, row: any) => (
        <p onClick={() => navigateToSR(row?.sr_number)}>{row?.sr_number}</p>
      ),
    },
    {
      dataField: "sr_date",
      text: "SR Date",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "priority",
      text: "Priority",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "status",
      text: "Status",
      sort: true,
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "comments",
      text: "Comments/Notes",
      headerAlign: "left",
      align: "left",
    },
    {
      dataField: "attachments",
      text: "Additional Documents",
      headerAlign: "left",
      align: "left",
      formatter: (cell: any, row: any) => (
        <p>
          {row?.attachments?.map((attachment) => {
            if (attachment?.type === "pdf") {
              return (
                <a target="_blank">
                  <DocumentPdfRegular />
                </a>
              );
            } else if (attachment?.type === "word") {
              return (
                <a target="_blank">
                  <TextWordCountRegular />
                </a>
              );
            } else if (attachment?.type === "text") {
              return (
                <a target="_blank">
                  <ClipboardTextEditRegular />
                </a>
              );
            }
          })}
        </p>
      ),
    },
  ];

  const existingData = localStorage.getItem("serviceData");
  if (!existingData || existingData?.length === 0) {

    const updatedMockData = Mockdata?.map?.((dataEntry) => {
      if(email && email !== "") {
        dataEntry.created_by = email
      }
      return dataEntry
    })

    setData(updatedMockData);
    localStorage.setItem("serviceData", JSON.stringify(updatedMockData));
  }
  else if (!data) {
    let dataString = localStorage.getItem("serviceData");
    if (dataString) {
      setData(JSON.parse(dataString));
    }
  }

  const doesExistTicket = (srNo) => {
    if (srNo && srNo !== "" && data && data?.length > 0) {
      const ticket = data?.filter(
        (eachTicket) =>
          eachTicket?.sr_number?.toLowerCase() === srNo?.toLowerCase()
      );
      if (ticket?.length > 0) {
        return true;
      }
    }
    return false;
  };

  const createNewTicket = (description) => {
    const ticketNo = generateAlphaNumericCode();
    const ticket = {
      sr_number: ticketNo,
      sr_date: formatCurrentDate(),
      service_type: "",
      description: description,
      specific_maintainence_task_requested: "",
      symptoms_observed: "",
      attachments: [
        {
          type: "pdf",
          url: "",
        },
        {
          type: "word",
          url: "",
        },
        {
          type: "text",
          url: "",
        },
      ],
      priority: "Medium",
      created_by: email,
      status: "SR RAISED",
      comments: "",
      lifecycle: [
        {
          status_name: "SR RAISED",
          status_date: formatCurrentDate(),
          status: "completed",
          message: "",
        },
        {
          status_name: "Approved",
          status_date: "",
          status: "pending",
          message: "",
        },
        {
          status_name: "Scheduled",
          status_date: "",
          status: "pending",
          message: "",
        },
        {
          status_name: "Review & Quality Check",
          status_date: "",
          status: "pending",
          message: "",
        },
        {
          status_name: "Completed",
          status_date: "",
          status: "pending",
          message: "",
        },
        {
          status_name: "Dispatched",
          status_date: "",
          status: "pending",
          message: "",
        },
      ],
    };

    let newData = data;
    if (data) {
      newData.push(ticket);
    } else {
      newData = [ticket];
    }

    localStorage.setItem("serviceData", JSON.stringify(newData));

    setData(newData);
    handleFilteredData();

    return ticketNo;
  };

  const handleFilteredData = () => {
    if (data && data?.length > 0) {
      let existingData = [...data];

      if (filters.search !== "") {
        let searchTerm = filters?.search?.toLowerCase();
        existingData = existingData.filter((each) => {
          return (
            each?.sr_number?.toLowerCase().includes(searchTerm) ||
            each?.comments?.toLowerCase().includes(searchTerm) ||
            each?.sr_date?.toLowerCase().includes(searchTerm) ||
            each?.priority?.toLowerCase().includes(searchTerm) ||
            each?.ststus?.toLowerCase().includes(searchTerm)
          );
        });
      }

      if (filters.fromDate !== "" && filters.toDate !== "") {
        existingData = existingData.filter((each) => {
          let srDate = stringToDate(each?.sr_date);
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

      if (filters.request !== "All") {
        existingData = existingData?.filter((record) => {
          let recordStatus = record?.status?.toUpperCase();
          if (filters?.request === "Pending") {
            return !(
              recordStatus === "COMPLETED" || recordStatus === "DISPATCHED"
            );
          } else {
            return (
              recordStatus === "COMPLETED" || recordStatus === "DISPATCHED"
            );
          }
        });
      }
      if (searchRef.current && filters.search === "") {
        searchRef.current.value = "";
      }

      existingData.sort((a, b) => {
        const dateA = new Date(a.sr_date).getTime();
        const dateB = new Date(b.sr_date).getTime();
        return dateB - dateA;
    });

      setFilteredData(existingData);
    }
  };

  useEffect(() => {
    handleFilteredData();
  }, [filters, data]);

  const updateSummary = () => {
    if (data?.length > 0) {
      const newSummary = {
        requests: data?.filter((record) => record?.created_by === email)
          ?.length,
        open_requests: data?.filter(
          (record) =>
            record?.created_by === email &&
            record?.status !== "COMPLETED" &&
            record?.status !== "DISPATCHED"
        )?.length,
        closed_requests: data?.filter(
          (record) =>
            record?.created_by === email &&
            (record?.status === "COMPLETED" || record?.status === "DISPATCHED")
        )?.length,
        notifications: 0,
      };
      setSummaryCount(newSummary);
    }
  };

  useEffect(() => {
    updateSummary();
  }, [data]);

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
              <h5>YOUR REQUESTS</h5>
              <h3>{summaryCount?.requests}</h3>
              <span>
                <TableCalculatorRegular />
              </span>
            </div>
            <div className={styles.box}>
              <h5>YOUR OPEN REQUESTS</h5>
              <h3>{summaryCount?.open_requests}</h3>
              <span>
                <FolderOpenRegular />
              </span>
            </div>
            <div className={styles.box}>
              <h5>YOUR CLOSED REQUESTS</h5>
              <h3>{summaryCount?.closed_requests}</h3>
              <span>
                <TextBulletListCheckmarkFilled />
              </span>
            </div>
            <div className={styles.box}>
              <h5>NOTIFICATIONS FOR YOU</h5>
              <h3>{summaryCount?.notifications}</h3>
              <span>
                <ServiceBellRegular />
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
          <ChatButton
            createNewTicket={createNewTicket}
            doesExistTicket={doesExistTicket}
          />
        </div>
      </div>
    </div>
  );
};

export default AllServices;
