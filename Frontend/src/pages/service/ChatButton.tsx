import React, { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCommentDots } from '@fortawesome/free-solid-svg-icons';
import ChatApp from './ChatApp';
import './ChatButton.css';

interface ChatButtonProps {
  createNewTicket: (description: string) => string;
  doesExistTicket: (srNumber: string) => boolean; // Function to check ticket existence
}

const ChatButton: React.FC<ChatButtonProps> = ({ createNewTicket, doesExistTicket }) => {
  const [isOpen, setIsOpen] = useState(false);

  const openChat = () => {
    setIsOpen(true);
  };

  const closeChat = () => {
    setIsOpen(false);
  };

  return (
    <div className="chat-button-container">
      {!isOpen && (
        <button className="chat-toggle-button" onClick={openChat}>
          <FontAwesomeIcon icon={faCommentDots} />
        </button>
      )}
      {isOpen && <ChatApp onClose={closeChat}  createNewTicket={createNewTicket} doesExistTicket={doesExistTicket}/>}
    </div>
  );
};

export default ChatButton;
