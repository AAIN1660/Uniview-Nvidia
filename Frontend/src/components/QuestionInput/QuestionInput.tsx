import React, { useEffect, useState } from "react";
import { Stack, TextField } from "@fluentui/react";
import { Send28Filled } from "@fluentui/react-icons";
import styles from "./QuestionInput.module.css";
import { Audioconvert } from "../Audioconverter/index";

interface Props {
  onSend: (question: string) => void;
  disabled: boolean;
  placeholder?: string;
  clearOnSend?: boolean;
  userquestion?: string;
  sidbarQuestion?:string
}

export const QuestionInput = ({
  onSend,
  disabled,
  placeholder,
  clearOnSend,
  userquestion,
  sidbarQuestion,
  setSidbarQuestion
}: Props) => {
  const [question, setQuestion] = useState<string>("");
  const [audio, setaudio] = useState<Boolean>(false);
  const [isChecked, setIsChecked] = useState(false)
  const [hasAnswer, setHasAnswer] = useState(false);
  const [askedQuestion, setAskedQuestion] = useState<boolean>(false); // Track if a question was asked


  const handleCheckboxChange = (event) => {
    setIsChecked(event.target.checked)
  }

  useEffect(() => {
    if (userquestion) {
      setQuestion(userquestion);
    }
  }, [userquestion]);
  const sendQuestion = () => {
    console.log(question, "question in question inout");
    if (disabled || !question.trim()) {
      return;
    }
    onSend(question,isChecked);
    setHasAnswer(true); // Set to true after sending the question
    setAskedQuestion(true); 

    // if (clearOnSend) {
    //   setQuestion("");
    // }
  };

  const onEnterPress = (ev: React.KeyboardEvent<Element>) => {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      sendQuestion();
    }
  };

  const onQuestionChange = (
    _ev: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>,
    newValue?: string
  ) => {
    setQuestion(newValue || "");
    setSidbarQuestion(newValue)
  };

  useEffect(() => {
    if (sidbarQuestion){
      setQuestion(sidbarQuestion)
    }
  
   
  }, [sidbarQuestion])
  

  const sendQuestionDisabled = disabled || !question.trim();

  return (
    <Stack horizontal className={`${styles.questionInputContainer} ${
      hasAnswer ? styles.hasAnswer : ""
    }`}>
      <TextField
        className={styles.questionInputTextArea}
        placeholder={audio ? "I'm listening..." : placeholder}
        multiline
        resizable={false}
        borderless
        value={question ||sidbarQuestion}
        onChange={onQuestionChange}
        onKeyDown={onEnterPress}
        autoComplete="off"
        styles={{
          root: {
            height: '50px',
          },
          fieldGroup: {
            border: 'none',
            boxShadow: 'none',
          },
          field: {
            outline: 'none',
            border: 'none',
            boxShadow: 'none',
            height: '100%',
          },
        }}

      />
      <div className="checkbox-container">
        <input type="checkbox" id="explain-code" checked={isChecked} onChange={handleCheckboxChange}/>
        <label for="explain-code">Explain Code</label>
      </div>
      <div className={styles.questionInputButtonsContainer}>
        <Audioconvert
          setQuestion={setQuestion}
          onSend={onSend}
          setaudio={setaudio}
          audio={audio}
        />
        <div
          className={`${styles.questionInputSendButton} ${sendQuestionDisabled ? styles.questionInputSendButtonDisabled : ""
            }`}
          aria-label="Ask question button"
          onClick={sendQuestion}
        >
          <i className="fa-solid fa-paper-plane"></i>
        </div>
      </div>
    </Stack>
  );
};
