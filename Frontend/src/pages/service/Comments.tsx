import React, { useRef } from "react";
import "./Comments.css";
import { statusLifeCycle } from "./Helper";
export default function Comments({ data, handleChange }) {
  return (
    <div>
      <div className="comments container mt-5">
        <div className="card">
          <div className="card-header">
            <h2>Comments</h2>
          </div>
          <div className="card-body">
            <div className="form-group">
              <label className="tech-notes-label">Technician Notes:</label>
              <textarea
                onChange={(e) => handleChange("comments", e.target.value)}
                className="tech-notes"
                defaultValue={data?.comments}
              />
            </div>
          </div>
          {/* <div className="card-footer text-right">
            <button className="btn btn-outline-secondary">
              <i className="bi bi-chat-right-text"></i>
            </button>
          </div> */}
          <div>
            <h5>Status:</h5>
            <select onChange={(e) => {
                handleChange("status", e.target.value)
            }} defaultValue={data?.status?.toUpperCase()}>
                {statusLifeCycle.map((status) => {
                    return <option>{status}</option>
                })}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
