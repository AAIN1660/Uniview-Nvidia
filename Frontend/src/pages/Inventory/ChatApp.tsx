import React, { useState, ChangeEvent, useRef, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faRobot, faUser, faTimes } from "@fortawesome/free-solid-svg-icons";
import "./ChatApp.css";

interface Message {
  sender: "bot" | "user";
  text: string;
  isLink?: boolean;
  srNumber?: string; // Add srNumber field for link messages
}

interface ChatAppProps {
  onClose: () => void;
  createNewTicket: (description: string) => string;
  doesExistTicket: (srNumber: string) => boolean; // Function to check if ticket exists
}

const ChatApp: React.FC<ChatAppProps> = ({
  onClose,
  createNewTicket,
  doesExistTicket,
}) => {
  const [messages, setMessages] = useState<Message[]>([
    { sender: "bot", text: "Hey, How can I help you?" },
  ]);
  const [input, setInput] = useState<string>("");
  const [issueReported, setIssueReported] = useState<boolean>(false);
  const [srNumberRequested, setSrNumberRequested] = useState<boolean>(false);
  const [descriptionRequested, setDescriptionRequested] =
    useState<boolean>(false);

  const chatWindowRef = useRef<HTMLDivElement>(null);

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

    if (
      lastMessage.toLowerCase() === "hi" ||
      lastMessage.toLowerCase() === "hello"
    ) {
      botMessage.text = "Hey, How can I help you?";
    } else if (!issueReported) {
      botMessage.text =
        "Sure. I can help you with that. Do you have a pre-existing SR number.";
      setIssueReported(true);
    } else if (!srNumberRequested && lastMessage.toLowerCase() === "yes") {
      botMessage.text = "Please provide your SR number.";
      setSrNumberRequested(true);
    } else if (!srNumberRequested && lastMessage.toLowerCase() === "no") {
      botMessage.text = "Thank you. Can you describe the issue in more detail?";
      setDescriptionRequested(true);
    } else if (srNumberRequested) {
      // Handle SR number input from user
      const srNumber = lastMessage.trim(); // Keep the original case
      const ticketExists = doesExistTicket(srNumber);
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
    } else if (descriptionRequested) {
      const description = lastMessage.trim(); // Keep the original case
      const generatedSrNumber = createNewTicket(description);
      botMessage.text = `I have created a ticket for you. Here is your SR number: ${generatedSrNumber}.`;
      setDescriptionRequested(false);
    }

    setMessages([...newMessages, botMessage]);
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.value !== "") {
      setInput(e.target.value);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      if (e.target.value !== "") {
        handleSend(e.target.value)
        setInput("");
      }
    }
  };

  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="chatbot-container">
      <div className="chat-header">
        <h5 className="me-4">AEROINTERACT ASSISTANT</h5>
        <button className="close-button" onClick={onClose}>
          <FontAwesomeIcon icon={faTimes} />
        </button>
      </div>
      <div className="chat-window" ref={chatWindowRef}>
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.sender}`}>
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
                <div dangerouslySetInnerHTML={{ __html: message.text }} />
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="chat-input-container">
        <input
          type="text"
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

export default ChatApp;
