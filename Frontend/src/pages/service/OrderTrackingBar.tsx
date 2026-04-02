import React from "react";
import PropTypes from "prop-types";
import "./OrderTrackingBar.css";

const OrderTrackingBar = ({ stages }) => {
  return (
    <div className="trackingBarHolder">
      <div className="col-12 col-md-10 hh-grayBox pt45 pb20">
        <div className="row justify-content-between">
          {stages.map((stage, index) => (
            <div key={index} className="stage-container">
              <div
                className={`order-tracking ${stage.status} ${
                  stage.status === "in-progress" ? "in-progress" : ""
                }`}
              >
                <span className={`is-complete ${stage.status}`}>
                  <span className="inner-circle"></span>
                </span>
                <div className="content">
                  <p>{stage.status_name} </p>
                  <span>{stage.status_date}</span>
									<p className="contentmessage">{stage.message}</p>
                </div>
              </div>
              {index < stages.length - 1 && (
                <div
                  className={`connector ${
                    stages[index + 1].status === "pending"
                      ? "connector-pending"
                      : "connector-completed"
                  }`}
                ></div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

OrderTrackingBar.propTypes = {
  stages: PropTypes.arrayOf(
    PropTypes.shape({
      status_name: PropTypes.string.isRequired,
      status_date: PropTypes.string.isRequired,
      status: PropTypes.oneOf(["completed", "in-progress", "pending"])
        .isRequired,
      message: PropTypes.string.isRequired
    })
  ).isRequired,
};

export default OrderTrackingBar;
