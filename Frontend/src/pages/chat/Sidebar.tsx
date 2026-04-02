import React, { useState } from "react";
import "./Sidebar.css";

const Sidebar = ({ onOptionClick, askedQuestion }) => {
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    // const [isTitle, setIsTitle] = useState(false);
    // const [chatItems, useChatItem] = useState();
    // useChatItem(askedQuestion)
    let chatItems =askedQuestion
    // Toggle Sidebar
    const toggleSidebar = () => {
        setIsSidebarCollapsed(!isSidebarCollapsed);
    };

    return (
        <div className={`sidebar ${isSidebarCollapsed ? "collapsed" : ""}`}>
            <button className="toggle-button" onClick={toggleSidebar}>
                {/* <i className="fa-solid fa-table-cells-large"></i>
                 */}
                 <i className="fa fa-columns"></i>
            </button>
            {!isSidebarCollapsed && (
                <>
                    <h3 className="sidebar-header ms-1">History</h3>
                    {chatItems.map((item, index) => (
                        <div
                            key={index}
                            className="sidebar-item"
                            onClick={() => onOptionClick(item)} // Call parent callback with selected item
                        >
                            <i className="fa-solid fa-message mt-1" style={{ position: "relative", bottom: "6px",top:'2px' }}></i>
                            <div title={item} className="mt-1 me-4 chat-item ">{item.slice(0,22)}.. 
                            
                            </div>
                            <i className="fas fa-ellipsis-v" style={{ position: "relative", left: "0%",top:"4px"}}></i>
                        </div>
                    ))}
                </>
            )}
        </div>
    );
};

export default Sidebar;
