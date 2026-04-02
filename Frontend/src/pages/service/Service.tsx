import React from "react";
import { useState } from "react";
import styles from "./Service.module.css";
import ServicerRequestDetailsCard from "./ServicerRequestDetailsCard";
import Comments from "./Comments";

import OrderTrackingBar from "./OrderTrackingBar";
import {
  ArrowSyncRegular,
  DismissRegular
} from "@fluentui/react-icons";
import { useNavigate, useParams } from "react-router-dom";
import { formatCurrentDate, statusLifeCycle } from "./Helper";

const Service = () => {
  const navigate = useNavigate();

  const { sr_num } = useParams();
  let localStorageData: [any] | null = JSON.parse(
    localStorage.getItem("serviceData") || `[]`
  );
  let data = localStorageData?.filter(
    (data) => data?.sr_number === sr_num
  )?.[0];
  const [updatedData, setUpdatedData] = useState(data);

  const updateClicked = () => {
    let newData = {};
    if (JSON.stringify(data) === JSON.stringify(updatedData)) {
      alert("No changes were made to update");
      return;
    }
    if (data?.status !== updatedData?.status) {
      const originalStatus = data?.status?.toUpperCase();
      const updatedStatus = updatedData?.status?.toUpperCase();
      const indexOfUpdatedStatus = statusLifeCycle?.indexOf(updatedStatus);
      const updatedLifeCycle = data?.lifecycle?.map((eadhCycle, index) => {
        if (index === indexOfUpdatedStatus) {
          return {
            ...eadhCycle,
            status_date: formatCurrentDate(),
            status: "in-progress",
          };
        } else if (index > indexOfUpdatedStatus) {
          return {
            ...eadhCycle,
            status_date: "",
            status: "pending",
            message: "",
          };
        } else {
          return {
            ...eadhCycle,
            status: "completed",
            status_date:
              eadhCycle?.status_date === ""
                ? formatCurrentDate()
                : eadhCycle?.status_date,
          };
        }
      });
      newData = {
        ...updatedData,
        lifecycle: updatedLifeCycle,
      };
    } else {
      newData = {
        ...updatedData,
      };
    }

    let wholeData: [any] | null = JSON.parse(
      localStorage.getItem("serviceData") || `[]`
    );
    if (wholeData && wholeData?.length > 0) {
      const modifiedData = wholeData?.map((singleData) => {
        if (newData?.sr_number === singleData?.sr_number) {
          return newData;
        } else {
          return singleData;
        }
      });

      localStorage.setItem("serviceData", JSON.stringify(modifiedData));
      alert("Data Updated");
      modifiedData?.map((singleData) => {
        if (sr_num === singleData?.sr_number) {
          setUpdatedData(singleData)
        } 
      });
    }
  };

  const goToAllServices = () => {
    navigate(`/layout/services`);
  };

  const handleChange = (key, value) => {
    setUpdatedData({
      ...updatedData,
      [key]: value,
    });
  };

  const stages = data?.lifecycle;

  return (
    <div className={styles.serviceContainer}>
      <div>
        <div className={styles.titleRow}>
          <h6 className={styles.sr_no}>{data?.sr_number}</h6>
          <DismissRegular onClick={goToAllServices} />
        </div>
        <OrderTrackingBar stages={stages} />
      </div>
      <div className={styles.detailsWrapper}>
        <ServicerRequestDetailsCard data={data} handleChange={handleChange} />
        <Comments data={data} handleChange={handleChange} />
        
      </div>
      <div>
        <button className={styles.cancelAction} onClick={goToAllServices}>
          CANCEL{" "}
          <span>
            <DismissRegular />
          </span>
        </button>
        {/* <button className={styles.printAction}>
          PRINT{" "}
          <span>
            <PrintRegular />
          </span>
        </button> */}
        <button onClick={updateClicked} className={styles.printAction}>
          UPDATE{" "}
          <span>
            <ArrowSyncRegular />
          </span>
        </button>
      </div>
    </div>
  );
};

export default Service;
