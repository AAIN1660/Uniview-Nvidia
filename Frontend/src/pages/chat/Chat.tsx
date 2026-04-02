import { useRef, useState, useEffect } from "react";
import {
  Checkbox,
  Panel,
  DefaultButton,
  TextField,
  SpinButton,
  Dropdown,
  IDropdownOption,
  ComboBox,
  IComboBox,
  Stack,
  Toggle,
} from "@fluentui/react";
import { SparkleFilled } from "@fluentui/react-icons";
import { MultiSelect } from "react-multi-select-component";
import RetravierLogo from "../../assets/ErylLogo.png";
import styles from "./Chat.module.css";

import {
  chatApi,
  RetrievalMode,
  Approaches,
  AskResponse,
  ChatRequest,
  ChatTurn,
} from "../../api";
import { Answer, AnswerError, AnswerLoading } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { ExampleList } from "../../components/Example";
import { UserChatMessage } from "../../components/UserChatMessage";
import {
  AnalysisPanel,
  AnalysisPanelTabs,
} from "../../components/AnalysisPanel";
import { SettingsButton } from "../../components/SettingsButton";
import { ClearChatButton } from "../../components/ClearChatButton";
import { trackPromise } from "react-promise-tracker";
import categoryService from "../../api/categoryService";
import React from "react";
import useCredit from "../../api/userCredit";
import documentService from "../../api/documentService";
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";

const Chat = () => {
  const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
  const [promptTemplate, setPromptTemplate] = useState<string>("");
  const [retrieveCount, setRetrieveCount] = useState<number>(3);
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(
    RetrievalMode.Hybrid
  );
  const [useSemanticRanker, setUseSemanticRanker] = useState<boolean>(true);
  const [useSemanticCaptions, setUseSemanticCaptions] =
    useState<boolean>(false);
  const [useSuggestFollowupQuestions, setUseSuggestFollowupQuestions] =
    useState<boolean>(false);

  const lastQuestionRef = useRef<string>("");
  const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<unknown>();

  const [activeCitation, setActiveCitation] = useState<string>();
  const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<
    AnalysisPanelTabs | undefined
  >(undefined);

  const [selectedAnswer, setSelectedAnswer] = useState<number>(0);
  const [answers, setAnswers] = useState<
    [user: string, response: AskResponse][]
  >([]);

  const [categoryList, setcategoryList] = useState<any>([]);
  const [comboBoxOptions, setComboBoxOptions] = useState<any>([]);
  const comboBoxRef = useRef<IComboBox>(null);
  const [excludeCategory, setExcludedCategory] = useState<any>([]);
  const [includeCategory, setIncludedCategory] = useState<any>([]);
  const [categoryIds, setCategoryIds] = useState([]);
  const { creditBalance, setCreditBalance } = useCredit();
  // let excludeCategory : any = [];

  const [isInculdeMode, setisInculdeMode] = useState(false);
  const [sharepointfiles, setsharepointfiles] = useState<any>([]);
  const [panelType, setPanelType] = useState("upload");
  const [loaderMessage, setLoaderMessage] = useState("------------");
  const [loading, setLoading] = useState(false);
  const [optionsLoading, setOptionsLoading] = useState(true);

  const handleRadioChange = (ev, checked) => {
    setisInculdeMode(checked);
  };

  const toggleUploadSharePoint = (ev, checked) => {
    setPanelType(checked ? "upload" : "sharepoint");
  };

  const makeApiRequest = async (question: string) => {
    lastQuestionRef.current = question;
    const excludeResults = excludeCategory.map((cat) => cat.value);
    const includeResults = includeCategory.map((cat) => cat.value);

    error && setError(undefined);
    setIsLoading(true);
    setActiveCitation(undefined);
    setActiveAnalysisPanelTab(undefined);

    try {
      // Check if the decrypted balance is sufficient
      if (creditBalance <= 0) {
        // Display an alert indicating insufficient balance
        alert("Insufficient balance. Please recharge your account.");
        return;
      } else {
        const email = localStorage.getItem('email');
        if (includeResults.length < 1) {
          alert("No Category included");
          return;
        }
        else {
          const history: ChatTurn[] = answers.map((a) => ({ user: a[0], bot: a[1].answer }));
          const request: ChatRequest = {
            history: [...history, { user: question, bot: undefined }],
            email: email,
            approach: Approaches.ReadRetrieveRead,
            overrides: {
              promptTemplate:
                promptTemplate.length === 0 ? undefined : promptTemplate,
              excludeCategory: excludeResults,
              includeCategory: includeResults,
              categories: categoryIds,
              category_status_flag: isInculdeMode,
              top: retrieveCount,
              retrievalMode: retrievalMode,
              semanticRanker: useSemanticRanker,
              semanticCaptions: useSemanticCaptions,
              suggestFollowupQuestions: useSuggestFollowupQuestions,
            },
            index_type: panelType,
          };
          const result = await chatApi(email, request);
          setCreditBalance(result.balance);
          setAnswers([...answers, [question, result]]);
        }
      }
    } catch (e) {
      setError(e);
    } finally {
      setIsLoading(false);
    }
  };

  const PullSharePoint = () => {
    setLoaderMessage("Fetching SharePoint files...");
    setLoading(true);
    trackPromise(
      documentService
        .getSharePointData()
        .then((res) => {
          setsharepointfiles(res.data.unique_titles);
          console.log(sharepointfiles);
          setLoading(false);
        })
        .catch((err) => {
          console.log(err);
          setLoading(false);
        })
    );
  };

  const clearChat = () => {
    lastQuestionRef.current = "";
    error && setError(undefined);
    setActiveCitation(undefined);
    setActiveAnalysisPanelTab(undefined);
    setAnswers([]);
  };

  useEffect(
    () => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" }),
    [isLoading]
  );
  useEffect(() => getCategoryList(), []);

  const onPromptTemplateChange = (
    _ev?: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>,
    newValue?: string
  ) => {
    setPromptTemplate(newValue || "");
  };

  const onRetrieveCountChange = (
    _ev?: React.SyntheticEvent<HTMLElement, Event>,
    newValue?: string
  ) => {
    setRetrieveCount(parseInt(newValue || "3"));
  };

  const onRetrievalModeChange = (
    _ev: React.FormEvent<HTMLDivElement>,
    option?: IDropdownOption<RetrievalMode> | undefined,
    index?: number | undefined
  ) => {
    setRetrievalMode(option?.data || RetrievalMode.Hybrid);
  };

  const onUseSemanticRankerChange = (
    _ev?: React.FormEvent<HTMLElement | HTMLInputElement>,
    checked?: boolean
  ) => {
    setUseSemanticRanker(!!checked);
  };

  const onUseSemanticCaptionsChange = (
    _ev?: React.FormEvent<HTMLElement | HTMLInputElement>,
    checked?: boolean
  ) => {
    setUseSemanticCaptions(!!checked);
  };

  const onUseSuggestFollowupQuestionsChange = (
    _ev?: React.FormEvent<HTMLElement | HTMLInputElement>,
    checked?: boolean
  ) => {
    setUseSuggestFollowupQuestions(!!checked);
  };

  const onExampleClicked = (example: string) => {
    makeApiRequest(example);
  };

  const onShowCitation = (citation: string, index: number) => {
    if (
      activeCitation === citation &&
      activeAnalysisPanelTab === AnalysisPanelTabs.CitationTab &&
      selectedAnswer === index
    ) {
      setActiveAnalysisPanelTab(undefined);
    } else {
      setActiveCitation(citation);
      setActiveAnalysisPanelTab(AnalysisPanelTabs.CitationTab);
    }

    setSelectedAnswer(index);
  };

  const onToggleTab = (tab: AnalysisPanelTabs, index: number) => {
    if (activeAnalysisPanelTab === tab && selectedAnswer === index) {
      setActiveAnalysisPanelTab(undefined);
    } else {
      setActiveAnalysisPanelTab(tab);
    }

    setSelectedAnswer(index);
  };

  const getCategoryList = () => {
    const email = localStorage.getItem('email');
    trackPromise(
      categoryService.getCategory({ email: email, type: "user" }).then((res) => {
        let catergoryList2 = [...res?.data?.CategoryList];
        let categoryIds: any = [];
        catergoryList2 = catergoryList2.filter(
          (category) => category.status === 1
        );
        setcategoryList(catergoryList2);
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
        if (!localStorage.getItem("userCategories")) {
          localStorage.setItem(
            "userCategories",
            JSON.stringify(comboBoxOptions.map((each) => each.key))
          );
        }
      })
    );
  };

  const handleSelectionChange = (selectedOptions) => {
    const selectedKeys = selectedOptions.map(option => option.value)
    if (isInculdeMode) {
      // Add options to the included category if they are not part of the selected options in exclude mode
      const newIncludedCategory = [
        ...includeCategory,
        ...excludeCategory.filter(
          (cat) => !selectedKeys.includes(cat.value) && !includeCategory.some(inc => inc.value === cat.value)
        ),
      ];
      const cleanedIncludedCategory = newIncludedCategory.filter(
        (cat) => !selectedKeys.includes(cat.value)
      );
      setIncludedCategory(cleanedIncludedCategory);
      setExcludedCategory(selectedOptions);
    } else {
      // Add options to the excluded category if they are not part of the selected options in include mode
      const newExcludedCategory = [
        ...excludeCategory,
        ...includeCategory.filter(
          (cat) => !selectedKeys.includes(cat.value) && !excludeCategory.some(ex => ex.value === cat.value)
        ),
      ];
      const cleanedExcludedCategory = newExcludedCategory.filter(
        (cat) => !selectedKeys.includes(cat.value)
      );
      setExcludedCategory(cleanedExcludedCategory);
      setIncludedCategory(selectedOptions);
    }
  };

  return (
    <div>
      {loading && <LoadingOverlay message={loaderMessage} />}
      <div className={styles.container}>
        <div className={styles.commandsContainer}>
          <ClearChatButton
            className={styles.commandButton}
            onClick={clearChat}
            disabled={!lastQuestionRef.current || isLoading}
          />
          <SettingsButton
            className={styles.commandButton}
            onClick={() => setIsConfigPanelOpen(!isConfigPanelOpen)}
          />
        </div>
        <div className={styles.chatRoot}>
          <div className={styles.chatContainer}>
            {!lastQuestionRef.current ? (
              <div className={styles.chatEmptyState}>
                <SparkleFilled
                  fontSize={"120px"}
                  primaryFill={"rgba(115, 118, 225, 1)"}
                  aria-hidden="true"
                  aria-label="Chat logo"
                />
                <h1 className={styles.chatEmptyStateTitle}>
                  Chat with
                  <img
                    src={RetravierLogo}
                    className="d-inline-block align-left"
                    width="100px"
                  />
                </h1>
                {/* <h2 className={styles.chatEmptyStateSubtitle}>
                Ask anything or try an example
              </h2> */}
                <ExampleList onExampleClicked={onExampleClicked} />
              </div>
            ) : (
              <div className={styles.chatMessageStream}>
                {answers.map((answer, index) => (
                  <div key={index}>
                    <UserChatMessage message={answer[0]} />
                    <div className={styles.chatMessageGpt}>
                      <Answer
                        key={index}
                        answer={answer[1]}
                        isSelected={
                          selectedAnswer === index &&
                          activeAnalysisPanelTab !== undefined
                        }
                        onCitationClicked={(c) => onShowCitation(c, index)}
                        onThoughtProcessClicked={() =>
                          onToggleTab(
                            AnalysisPanelTabs.ThoughtProcessTab,
                            index
                          )
                        }
                        onSupportingContentClicked={() =>
                          onToggleTab(
                            AnalysisPanelTabs.SupportingContentTab,
                            index
                          )
                        }
                        onFollowupQuestionClicked={(q) => makeApiRequest(q)}
                        showFollowupQuestions={
                          useSuggestFollowupQuestions
                        }
                        question=""
                        onRefreshedClicked={() => { }}
                      />
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <>
                    <UserChatMessage message={lastQuestionRef.current} />
                    <div className={styles.chatMessageGptMinWidth}>
                      <AnswerLoading />
                    </div>
                  </>
                )}
                {error ? (
                  <>
                    <UserChatMessage message={lastQuestionRef.current} />
                    <div className={styles.chatMessageGptMinWidth}>
                      <AnswerError
                        error={error.toString()}
                        onRetry={() => makeApiRequest(lastQuestionRef.current)}
                      />
                    </div>
                  </>
                ) : null}
                <div ref={chatMessageStreamEnd} />
              </div>
            )}

            <div className={styles.chatInput}>
              <QuestionInput
                clearOnSend
                placeholder="Type a new question"
                disabled={isLoading}
                onSend={(question) => makeApiRequest(question)}
              />
            </div>
          </div>

          {answers.length > 0 && activeAnalysisPanelTab && (
            <AnalysisPanel
              className={styles.chatAnalysisPanel}
              activeCitation={activeCitation}
              onActiveTabChanged={(x) => onToggleTab(x, selectedAnswer)}
              citationHeight="810px"
              answer={answers[selectedAnswer][1]}
              activeTab={activeAnalysisPanelTab}
            />
          )}

          <Panel
            headerText="Configure answer generation"
            isOpen={isConfigPanelOpen}
            isBlocking={false}
            onDismiss={() => setIsConfigPanelOpen(false)}
            closeButtonAriaLabel="Close"
            onRenderFooterContent={() => (
              <div>
                <DefaultButton onClick={() => setIsConfigPanelOpen(false)}>
                  Close
                </DefaultButton>
              </div>
            )}
            isFooterAtBottom={true}
          >
            <Stack tokens={{ childrenGap: 10 }}>
              <div className={styles.toggleContainer}>
                <span className={styles.leftLabel}>SharePoint</span>
                <Toggle
                  inlineLabel
                  checked={panelType === "upload"}
                  onChange={toggleUploadSharePoint}
                  className={styles.whiteColor}
                  styles={{
                    thumb: {
                      backgroundColor: panelType === "upload" ? "green" : "red",
                    },
                    root: {
                      backgroundColor: "white",
                    },
                  }}
                />
                <span className={styles.rightLabel}>Date Source Eryl</span>
              </div>
              {panelType === "upload" ? (
                <>
                  {/* <div>
                <Label>Upload File</Label>
                <input type="file" onChange={handleFileUpload} />
              </div> */}
                  <TextField
                    className={styles.chatSettingsSeparator}
                    defaultValue={promptTemplate}
                    label="Override prompt template"
                    multiline
                    autoAdjustHeight
                    onChange={onPromptTemplateChange}
                  />

                  <SpinButton
                    className={styles.chatSettingsSeparator}
                    label="Retrieve this many documents from search:"
                    min={1}
                    max={50}
                    defaultValue={retrieveCount.toString()}
                    onChange={onRetrieveCountChange}
                  />

                  <Stack
                    tokens={{ childrenGap: 5 }}
                    style={{ marginTop: "10px" }}
                  >
                    <span className={styles.labelWeight}>
                      Filter Categories
                    </span>
                    <Stack>
                      <Stack
                        horizontal
                        verticalAlign="center"
                        tokens={{ childrenGap: 10 }}
                      >
                        <span className={styles.labelWeight}>Exclude</span>
                        <Toggle
                          inlineLabel
                          checked={!isInculdeMode}
                          className={styles.whiteColor}
                          styles={{
                            thumb: {
                              backgroundColor: isInculdeMode ? "red" : "green",
                            },
                            root: {
                              backgroundColor: "white",
                            },
                          }}
                          onChange={(ev, checked) =>
                            handleRadioChange(ev, !checked)
                          }
                        />
                        <span className={styles.labelWeight}>Include</span>
                      </Stack>
                    </Stack>
                    <MultiSelect
                      options={comboBoxOptions}
                      value={isInculdeMode ? excludeCategory : includeCategory}
                      onChange={handleSelectionChange}
                      labelledBy="Select Domains"
                      isLoading={optionsLoading}
                    />
                  </Stack>

                  {/* <Checkbox
                        className={styles.chatSettingsSeparator}
                        checked={useSemanticRanker}
                        label="Use semantic ranker for retrieval"
                        onChange={onUseSemanticRankerChange}
                    />
                    <Checkbox
                        className={styles.chatSettingsSeparator}
                        checked={useSemanticCaptions}
                        label="Use query-contextual summaries instead of whole documents"
                        onChange={onUseSemanticCaptionsChange}
                        disabled={!useSemanticRanker}
                    /> */}
                  <Checkbox
                    className={styles.chatSettingsSeparator}
                    checked={useSuggestFollowupQuestions}
                    label="Suggest follow-up questions"
                    onChange={onUseSuggestFollowupQuestionsChange}
                  />
                  <Dropdown
                    className={styles.chatSettingsSeparator}
                    label="Retrieval mode"
                    options={[
                      {
                        key: "hybrid",
                        text: "Vectors + Text (Hybrid)",
                        selected: retrievalMode == RetrievalMode.Hybrid,
                        data: RetrievalMode.Hybrid,
                      },
                      {
                        key: "vectors",
                        text: "Vectors",
                        selected: retrievalMode == RetrievalMode.Vectors,
                        data: RetrievalMode.Vectors,
                      },
                      {
                        key: "text",
                        text: "Text",
                        selected: retrievalMode == RetrievalMode.Text,
                        data: RetrievalMode.Text,
                      },
                    ]}
                    required
                    onChange={onRetrievalModeChange}
                  />
                </>
              ) : (
                <div>
                  <DefaultButton
                    text="Fetch SharePoint Files"
                    onClick={PullSharePoint}
                  />
                  <a
                    href="https://affineindia.sharepoint.com/sites/ERYL-SharepointIndexer"
                    className="sharepoint-link"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    https://affineindia.sharepoint.com/sites/ERYL-SharepointIndexer
                  </a>
                  <div style={{ marginTop: "10px" }}>
                    <ul>
                      {/* Map through unique_titles array to render each title */}
                      {sharepointfiles.map((title, index) => (
                        <li key={index}>{title}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </Stack>
          </Panel>
        </div>
      </div>
    </div>
  );
};

export default Chat;
