import React, { useState, ChangeEvent, useRef, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faRobot, faUser, faTimes } from "@fortawesome/free-solid-svg-icons";
import "./InventoryChatApp.css";

interface Message {
  sender: "bot" | "user";
  text: string | JSX.Element; // Allow text to be JSX.Element for rendering components
  isLink?: boolean;
  srNumber?: string;
}

interface InventoryChatAppProps {
  onClose: () => void;
}

const InventoryChatApp: React.FC<InventoryChatAppProps> = ({ onClose }) => {
  const name = localStorage.getItem('name')?.split(" ")?.[0] || "";
  const [messages, setMessages] = useState<Message[]>([
    { sender: "bot", text: `Hey ${name}` },
  ]);
  const [input, setInput] = useState<string>("");
  const [issueReported, setIssueReported] = useState<boolean>(false);
  const [srNumberRequested, setSrNumberRequested] = useState<boolean>(false);
  const [descriptionRequested, setDescriptionRequested] = useState<boolean>(false);

  const chatWindowRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const generateTableHTML = (data) => {
    return (
      <table className="chat-table">
        <thead>
          <tr>
            <th style={{ fontSize: '10px !important' }} title="Description">SKU</th>
            <th style={{ fontSize: '10px !important' }} title="Description">Description</th>
            <th style={{ fontSize: '10px !important' }} title="Current Stock">Current Stock</th>
            <th style={{ fontSize: '10px !important' }} title="Reorder Level">Reorder Level</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => (
            <tr key={index}>
              <td style={{ fontSize: '10px !important' }}>{row.sku}</td>
              <td style={{ fontSize: '10px !important' }}>{row.description}</td>
              <td style={{ fontSize: '10px !important' }}>{row.stock}</td>
              <td style={{ fontSize: '10px !important' }}>{row.reorder}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  const tableData = [
    { sku: "SKU-12345", description: "Widget A", stock: "20 units", reorder: "50 units" },
    { sku: "SKU-23456", description: "Gizmo B", stock: "15 units", reorder: "30 units" },
    { sku: "SKU-45678", description: "Doodad D", stock: "18 units", reorder: "40 units" },
    { sku: "SKU-56789", description: "Widget E", stock: "12 units", reorder: "35 units" },
  ];

  const handleSend = (inputVal) => {
    if (inputVal.trim()) {
      const newMessages = [...messages, { sender: "user", text: inputVal }];
      setMessages(newMessages);
      setInput("");
      setTimeout(() => handleBotResponse(newMessages, inputVal.trim()), 1000);
    }
  };

  const handleBotResponse = (newMessages: Message[], lastMessage: string) => {
    let botMessage: Message = { sender: "bot", text: "" };
    const lowerCaseMessage = lastMessage.trim().toLowerCase();

    if (lowerCaseMessage === "hi" || lowerCaseMessage === "hello") {
      botMessage.text = `Hey ${name}, How can I help you?`;
      setMessages([...newMessages, botMessage]);
    } else if (!issueReported && lowerCaseMessage.includes("sku")) {
      botMessage.text = "Sure. I can help you with that. Here is the list of SKUs that are understocked";
      setMessages([...newMessages, botMessage]);
      setTimeout(() => {
        const tableMessage: Message = {
          sender: "bot",
          text: generateTableHTML(tableData),
        };
        setMessages((prevMessages) => [...prevMessages, tableMessage]);
      }, 1000);
      setIssueReported(true);
    } else if (issueReported && lowerCaseMessage.includes("sku")) {
      botMessage.text = "I have already provided the list of SKUs that are understocked. Here it is again:";
      setMessages([...newMessages, botMessage]);
      setTimeout(() => {
        const tableMessage: Message = {
          sender: "bot",
          text: generateTableHTML(tableData),
        };
        setMessages((prevMessages) => [...prevMessages, tableMessage]);
      }, 1000);
    } else if (lowerCaseMessage.includes("safety stock") && lowerCaseMessage.includes("turbine blades")) {
      botMessage.text = "The safety stock for turbine blades is 150 units.";
      setMessages([...newMessages, botMessage]);
    } else if (lowerCaseMessage.includes("safety stock") && lowerCaseMessage.includes("fuel nozzles")) {
      botMessage.text = "The safety stock for fuel nozzles is 180 units.";
      setMessages([...newMessages, botMessage]);
    } else if (!srNumberRequested && lowerCaseMessage === "yes") {
      botMessage.text = "Please provide your SR number.";
      setMessages([...newMessages, botMessage]);
      setSrNumberRequested(true);
    } else if (!srNumberRequested && lowerCaseMessage === "no") {
      botMessage.text = "Thank you. Can you describe the issue in more detail?";
      setMessages([...newMessages, botMessage]);
      setDescriptionRequested(true);
    } else if (srNumberRequested) {
      const srNumber = lastMessage.trim(); // Keep the original case
      const ticketExists = true;
      const link = `<a href='${window.location.origin.toString()}/layout/service/${srNumber}' /> Ticket Link`;
      if (ticketExists) {
        botMessage = {
          sender: "bot",
          text: "You can proceed with your SR number here",
          isLink: true,
          srNumber, // Original case SR number for link
        };
        setSrNumberRequested(false);
      } else {
        botMessage.text = `No ticket found for SR number ${srNumber}.`;
      }
      setMessages([...newMessages, botMessage]);
    } else if (descriptionRequested) {
      const description = lastMessage.trim(); // Keep the original case
      const generatedSrNumber = "test";
      botMessage.text = `I have created a ticket for you. Here is your SR number: ${generatedSrNumber}.`;
      setMessages([...newMessages, botMessage]);
      setDescriptionRequested(false);
    } else {
      botMessage.text = "Sorry but I am not able to understand your question. Can you please elaborate?";
      setMessages([...newMessages, botMessage]);
    }
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      if (e.target.value !== "") {
        handleSend(e.target.value);
        setInput("");
      }
    }
  };

  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  return (
    <div className="chatbot-container">
      <div className="chat-header">
        <h5 className="me-4">Demand & Inventory Assistant</h5>
        <button className="close-button" onClick={onClose}>
          <FontAwesomeIcon icon={faTimes} />
        </button>
      </div>
      <div className="chat-window" ref={chatWindowRef}>
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.sender} ${message.text?.type === 'table' ? 'no-background' : ''}`}>
            <div className="icon">
              <FontAwesomeIcon
                icon={message.sender === "bot" ? faRobot : faUser}
              />
            </div>
            <div className="message-text">
              {message.isLink ? (
                <a
                  href={`/layout/service/${message.srNumber}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {message.text}
                </a>
              ) : (
                <div>{message.text}</div>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="chat-input-container">
        <input
          type="text"
          ref={inputRef}
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Type here..."
        />
        <button onClick={() => handleSend(input)}>Send</button>
      </div>
    </div>
  );
};

export default InventoryChatApp;
