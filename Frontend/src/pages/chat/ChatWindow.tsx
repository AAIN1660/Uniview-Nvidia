import React, { useCallback, useEffect, useRef, useState } from "react";
import "./ChatWindow.css";
import Sidebar from "./Sidebar";
import { QuestionInput } from "../../components/QuestionInput";
import { UserChatMessage } from "../../components/UserChatMessage";
import ChatAnswer from "../../components/UnifiedAnswer/ChatAnswer";
import UnfiedLogo from "../../assets/uv-logo_red.png";
import { trackPromise } from "react-promise-tracker";
import categoryService from "../../api/categoryService"
import askService from "../../api/askService"
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";
import useCredit from "../../api/userCredit";
import configurationService from "../../api/configurationService";
import { Span } from "@chakra-ui/react";
import { AnswerLoading } from "../../components/Answer";
import dbConnectionService from '../../api/dbConnectionService';

const ChatWindow = () => {

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const lastQuestionRef = useRef<string>("");
  const [messages, setMessages] = useState<string[]>([]); // Store messages
  const [categoryList, setcategoryList] = useState<any>([]);
  const [comboBoxOptions, setComboBoxOptions] = useState<any>([]);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [includeCategory, setIncludedCategory] = useState<any>([]);
  const [categoryIds, setCategoryIds] = useState([]);
  const [answerResponse, setanswerResponse] = useState([])
  const [sidbarQuestion, setSidbarQuestion] = useState("")
  const [askedQuestion, setAskedQuestion] = useState([])
  const { creditBalance, setCreditBalance } = useCredit()
  const [lastQuestion, setLastQuestion] = useState("")
  const [configData, setConfigData] = useState<ConfigItem[]>([]);
  const [index, setIndex] = useState("Vector RAG");
  // const [useAi, setUseAi] = useState(0)
  const [lastChecked, setLastChecked] = useState(false)

  const [hover, setHover] = useState(false);
  const [showbadge, setShowbadge] = useState(true);
  const email = localStorage.getItem("email");
  const [userSelectedTables, setuserSelectedTables] = useState([]);
  const [userSelectedDatabase, setuserSelectedDatabase] = useState('uniview');
  


  
  useEffect(() => {
      dbConnectionService
        .get_user_tables(email)
        .then((res) => {
          setuserSelectedTables(res.data.tables_list);
          // setuserSelectedDatabase(res.data.selected_database)
        })
        .catch(() => {
          alert("Error");
        });
  }, [email]);

  const makeApiRequest = async (question: string, isChecked: boolean, useAi: Number = 0) => {
    setShowbadge(false);

    try {
      if (creditBalance > 0) {
        setIsLoading(true); // Start loading
        setMessages((prevMessages) => [question]);

        const email = localStorage.getItem('email');


        const payload = JSON.stringify({
          question,
          email,
          index_type: index,
          overrides: {
            top: 3,
            include_category: categoryIds,
            category_status_flag: false,

          },
          explain_code: isChecked,
          useai: useAi,
        });


        const response = await askService.askQuestion(payload);
        console.log("API Response:", response);
        response?.data?.balance != null && setCreditBalance(response?.data?.balance);
        // let data = JSON.parse(response.data)
        getQuestions()
        setanswerResponse(response.data);
        setLastQuestion(question)
        setLastChecked(isChecked)


        console.log("API call completed for:", question);
      } else {
        alert("You dont have enough credit balance")
      }




    } catch (error) {
      console.error("Error in API request:", error);
    } finally {
      setIsLoading(false); // End loading
    }

  };

  console.log({ "answerResponse": answerResponse });






  const handleOptionClick = (selectedOption: string) => {
    // alert(selectedOption)
    // Make API request with the selected option
    setSidbarQuestion(selectedOption)
    // alert(sidbarQuestion)
    // makeApiRequest(selectedOption);
  };

  const getQuestions = async () => {
    const email = localStorage.getItem('email');
    let payload = { "email": email }
    const response = await askService.getQuestion(payload);
    console.log('====================================');
    console.log(response);
    setAskedQuestion(response.data)
    console.log('====================================');

  }

  useEffect(() => {

    getQuestions()
    fetchConfigData()
    getCategoryList()

  }, [])



  const fetchConfigData = async () => {
    setIsLoading(true);
    try {

      const response = await configurationService.getConfigurationDetails();
      const transformedData = transformResponse(response.data.config_data);
      setConfigData(transformedData);
      setIndex(transformedData[0].search_type)

    } catch (error) {
      console.error("Error fetching configuration data:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const transformResponse = (data: any[]) => {
    return data.map((item) => ({
      id: item.id,
      Total_User_License: item.total_license,
      Pending_User_License: item.pending_license,
      Use_Credit_Pool: item.use_credit_pool,
      Total_Credit_Pool: item.credit_pool_assigned,
      Balance_Credit_Pool: item.credit_pool_balance,
      Token_Per_Credit: item.tokens,
      search_type: item.search_type
    }));
  };



  // useEffect(() => getCategoryList(), []);
  let categoryListLoaded = false;

  const getCategoryList =() => {
    if (categoryListLoaded) return; // Prevent multiple calls
    categoryListLoaded = true;
    const email = localStorage.getItem('email');
    trackPromise(
      categoryService.getCategory({ email: email, type: "user" }).then((res) => {
        let existingCategory = [];
        let catergoryList2 = [...res?.data?.CategoryList];
        let categoryIds: any = [];
        catergoryList2 = catergoryList2.filter(
          (category) => category.status === 1
        )
        setcategoryList(catergoryList2);
        console.log({ "catergoryList2": catergoryList2 });

        let comboboxoptions: any = [];
        let include_category: any = [];
        catergoryList2.forEach((category) => {
          comboboxoptions.push({
            value: category.id,
            label: category.category_name,
          });
          include_category.push({
            value: category.id,
            label: category.category_name,
            selected: true,
          });
          categoryIds.push(category.id);
        });
        setComboBoxOptions(comboboxoptions);
        setOptionsLoading(false);
        setIncludedCategory(include_category);
        setCategoryIds(categoryIds)
      })
    );
  } ;


  const onReload = () => {
    setanswerResponse([])
    setMessages([])
  }



  return (
    <div className="chat-container">
      {/* Sidebar */}
      <Sidebar onOptionClick={handleOptionClick} askedQuestion={askedQuestion} />
      {/* Main Chat Section */}
      <div className="chat-main">
     { showbadge && <div
      className="relative p-1 w-10 bg-gradient-to-r text-white rounded-sm shadow-md cursor-pointer transition-all custom-badge"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <h6 className="textcls">Selected Database : <span className="textcls3">{userSelectedDatabase}</span></h6>
      <h6 className="textcls"> Selected Tables :</h6> <h6 className="textcls3"> {userSelectedTables.length > 0
          ? ` ${userSelectedTables[0]} +${userSelectedTables.length - 1} more`
          : " No tables selected"} 
        </h6>
      {hover && (
        <div className="absolute left-0 mt-3 w-20 bg-gray-300 p-1 rounded-md shadow-md text-xs overflow-y-scroll border border-gray-400 custom-hover">
          {userSelectedTables.map((table, index) => (
            <p key={index} className="text-black border-b border-gray-400 last:border-0 truncate p-1">
              {table}
            </p>
          ))}
        </div>
      )}
    </div> }
        {messages.length === 0 && !isLoading && (
          <div className="chat-header-content">
            <img src={UnfiedLogo} className="img-icon" />
            <h2 className="mt-3">Chat with Unified View</h2>
            <p>Write your prompt to start chatting with Unified View</p>
          </div>
        )}
        <div className="chat-messages" style={{
          marginBottom: isLoading ? '119px' : '',
          width: isLoading ? '100%' : '',
        }}>
          {messages.map((msg, index) => (
            <>

              <UserChatMessage key={index} message={msg} />
              {isLoading && <AnswerLoading />}
              {!isLoading ? <ChatAnswer answerResponse={answerResponse} isLoading={isLoading} onRefresh={() => makeApiRequest(lastQuestion, lastChecked, 1)}  onReload= {onReload}
              /> : null} 
            </>

          ))}
        </div>

        <QuestionInput
          clearOnSend
          placeholder="Type a new question"
          disabled={isLoading}
          onSend={(question, isChecked) => makeApiRequest(question, isChecked, 0)}
          sidbarQuestion={sidbarQuestion}
          setSidbarQuestion={setSidbarQuestion}
        />
      </div>
    </div>
  );
};

export default ChatWindow;
