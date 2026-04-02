import React, { useRef } from "react";
import "./ServicerRequestDetailsCard.css";
export default function ServicerRequestDetailsCard({ data, handleChange }) {
  return (
    <div className="service-request-details">
      <div className="m-4">
        <div className="card card-backgroubd-color col-12">
          <div className="card-header text-center">
            <h5>Service Request Details</h5>
          </div>
          <div className="card-body">
            <div className="form-group row">
              <div className="col-sm-4 col-form-label">
                <label>Type of Service:</label>
              </div>
              <div className="col-sm-8">
                <input
                  onChange={(e) => handleChange("service_type", e.target.value)}
                  type="text"
                  className="form-control-plaintext bg-white ps-3"
                  defaultValue={data?.service_type}
                />
              </div>
            </div>
            <div className="form-group row mt-1">
              <div className="col-sm-4 col-form-label">
                <label>Description of Issue:</label>
              </div>

              <div className="col-sm-8">
                <input
                onChange={(e) => handleChange("description", e.target.value)}
                type="text"
                  className="form-control-plaintext bg-white ps-3"
                  defaultValue={data?.description}
                />
              </div>
            </div>
            <div className="form-group row mt-1">
              <div className="col-sm-4 col-form-label pt-4 pb-4">
                <label>Specific Maintenance Tasks Requested:</label>
              </div>

              <div className="col-sm-8">
                <textarea
                onChange={(e) => handleChange("specific_maintainence_task_requested", e.target.value)}
                defaultValue={data?.specific_maintainence_task_requested}
                />
              </div>
            </div>
            <div className="form-group row">
              <div className="col-sm-4 col-form-label">
                <label>Symptoms Observed:</label>
              </div>
              <div className="col-sm-8">
                <textarea
                onChange={(e) => handleChange("symptoms_observed", e.target.value)}
                defaultValue={data?.symptoms_observed}
                />
              </div>
            </div>
            <div
              className="form-group row mt-1 text-center"
              style={{ backgroundColor: "#165B6A" }}
            >
              <div className="col-sm-8 col-form-label text-center">
                <label>Attachments (Photos, Docs, etc.):</label>
              </div>
              {/* <div className="col-sm-4">
                <button className="btn button-color mt-2 mb-2">Preview</button>
              </div> */}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
