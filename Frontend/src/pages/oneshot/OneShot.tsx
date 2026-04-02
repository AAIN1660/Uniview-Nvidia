import { useEffect, useRef, useState } from "react";
import {
  Checkbox,
  ChoiceGroup,
  IChoiceGroupOption,
  Panel,
  DefaultButton,
  Spinner,
  TextField,
  SpinButton,
  IDropdownOption,
  Dropdown,
  IComboBox,
  ComboBox,
  Stack,
  Toggle
} from "@fluentui/react";
import { MultiSelect } from "react-multi-select-component";
import RetravierLogo from "../../assets/ErylLogo.png";
import styles from "./OneShot.module.css";
import React from "react";
import {
  askApi,
  Approaches,
  AskResponse,
  AskRequest,
  RetrievalMode,
  updateFeedBack,
  updateFeedBackRequest,
} from "../../api";
import { Answer, AnswerError } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { ExampleList } from "../../components/Example";
import {
  AnalysisPanel,
  AnalysisPanelTabs,
} from "../../components/AnalysisPanel";
import { SettingsButton } from "../../components/SettingsButton/SettingsButton";
import { trackPromise } from "react-promise-tracker";
import categoryService from "../../api/categoryService";
import useCredit from "../../api/userCredit";
import documentService from "../../api/documentService";
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";

export function Component(): JSX.Element {
  const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
  const [approach, setApproach] = useState<Approaches>(
    Approaches.RetrieveThenRead
  );
  const [promptTemplate, setPromptTemplate] = useState<string>("");
  const [promptTemplatePrefix, setPromptTemplatePrefix] = useState<string>("");
  const [promptTemplateSuffix, setPromptTemplateSuffix] = useState<string>("");
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(
    RetrievalMode.Hybrid
  );
  const [retrieveCount, setRetrieveCount] = useState<number>(3);
  const [useSemanticRanker, setUseSemanticRanker] = useState<boolean>(true);
  const [useSemanticCaptions, setUseSemanticCaptions] =
    useState<boolean>(false);

  const lastQuestionRef = useRef<string>("");

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<unknown>();
  const [answer, setAnswer] = useState<AskResponse>();
  const [userQuestion, setUserQuestion] = useState<string>("");

  const [activeCitation, setActiveCitation] = useState<string>();
  const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<
    AnalysisPanelTabs | undefined
  >(undefined);

  const [categoryList, setcategoryList] = useState<any>([]);
  const [comboBoxOptions, setComboBoxOptions] = useState<any>([]);
  const comboBoxRef = useRef<IComboBox>(null);
  const [excludeCategory, setExcludedCategory] = useState<any>([]);
  const [includeCategory, setIncludedCategory] = useState<any>([]);
  const { creditBalance, setCreditBalance } = useCredit()

  const [isInculdeMode, setisInculdeMode] = useState(false);
  const [panelType, setPanelType] = useState('upload');
  const [sharepointfiles, setsharepointfiles] = useState<any>([]);
  const [loaderMessage, setLoaderMessage] = useState('------------')
  const [loading, setLoading] = useState(false);
  const [categoryIds, setCategoryIds] = useState([]);
  const [optionsLoading, setOptionsLoading] = useState(true);

  const handleRadioChange = (ev, checked) => {
    setisInculdeMode(checked);
  };


  useEffect(() => getCategoryList(), []);


  const getCategoryList = () => {
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
  };

  const makeApiRequest = async (question: string, useai: number = 0) => {
    lastQuestionRef.current = question;
    setUserQuestion(question);
    const excludeResults = excludeCategory.map((cat) => cat.value);
    const includeResults = includeCategory.map((cat) => cat.value);
    error && setError(undefined);
    setIsLoading(true);
    setActiveCitation(undefined);
    setActiveAnalysisPanelTab(undefined);

    try {

      if (creditBalance <= 0) {
        // Display an alert indicating insufficient balance
        alert('Insufficient balance. Please recharge your account.');
        return;
      }
      else {
        const email = localStorage.getItem('email');
        if (includeResults.length < 1) {
          alert("No Category included");
          return;
        }
        else {
          const request: AskRequest = {
            email: email,
            question,
            approach,
            overrides: {
              promptTemplate:
                promptTemplate.length === 0 ? undefined : promptTemplate,
              promptTemplatePrefix:
                promptTemplatePrefix.length === 0
                  ? undefined
                  : promptTemplatePrefix,
              promptTemplateSuffix:
                promptTemplateSuffix.length === 0
                  ? undefined
                  : promptTemplateSuffix,
              include_category: includeResults,
              categories: categoryIds,
              category_status_flag: isInculdeMode,
              top: retrieveCount,
              retrievalMode: retrievalMode,
              semanticRanker: useSemanticRanker,
              semanticCaptions: useSemanticCaptions,
            },
            index_type: panelType
          };
          const result = await askApi(email, request, useai);
          setCreditBalance(result.balance)
          setAnswer(result);
        }

      }

    } catch (e) {
      setError(e);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleUploadSharePoint = (ev, checked) => {
    setPanelType(checked ? 'upload' : 'sharepoint');
  };

  const PullSharePoint = () => {
    setLoaderMessage("Fetching SharePoint files...")
    setLoading(true);
    trackPromise(
      documentService.getSharePointData()
        .then((res) => {
          setsharepointfiles(res.data.unique_titles)
          setLoading(false)
        })
        .catch((err) => {
          console.log(err)
          setLoading(false)
        })

    );
  }

  const onPromptTemplateChange = (
    _ev?: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>,
    newValue?: string
  ) => {
    setPromptTemplate(newValue || "");
  };

  const onPromptTemplatePrefixChange = (
    _ev?: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>,
    newValue?: string
  ) => {
    setPromptTemplatePrefix(newValue || "");
  };

  const onPromptTemplateSuffixChange = (
    _ev?: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>,
    newValue?: string
  ) => {
    setPromptTemplateSuffix(newValue || "");
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

  const onApproachChange = (
    _ev?: React.FormEvent<HTMLElement | HTMLInputElement>,
    option?: IChoiceGroupOption
  ) => {
    setApproach((option?.key as Approaches) || Approaches.RetrieveThenRead);
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

  const onExampleClicked = (example: string) => {
    makeApiRequest(example);
  };

  const onShowCitation = (citation: string) => {
    if (
      activeCitation === citation &&
      activeAnalysisPanelTab === AnalysisPanelTabs.CitationTab
    ) {
      setActiveAnalysisPanelTab(undefined);
    } else {
      setActiveCitation(citation);
      setActiveAnalysisPanelTab(AnalysisPanelTabs.CitationTab);
    }
  };

  const onToggleTab = (tab: AnalysisPanelTabs) => {
    if (activeAnalysisPanelTab === tab) {
      setActiveAnalysisPanelTab(undefined);
    } else {
      setActiveAnalysisPanelTab(tab);
    }
  };

  const approaches: IChoiceGroupOption[] = [
    {
      key: Approaches.RetrieveThenRead,
      text: "Retrieve-Then-Read",
    },
    {
      key: Approaches.EvaluationAgent,
      text: "Evaluation-Agent",
    },
    // {
    //   key: Approaches.ReadRetrieveRead,
    //   text: "Read-Retrieve-Read",
    // },
    // {
    //   key: Approaches.ReadDecomposeAsk,
    //   text: "Read-Decompose-Ask",
    // },
  ];

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
      <div className={styles.oneshotContainer}>
        <div className={styles.oneshotTopSection}>
          <SettingsButton
            className={styles.settingsButton}
            onClick={() => setIsConfigPanelOpen(!isConfigPanelOpen)}
          />
          <h1 className={styles.oneshotTitle}>
            Ask
            <img
              src={RetravierLogo}
              className="d-inline-block align-left"
              width="110px"
            />
          </h1>
          <div className={styles.oneshotQuestionInput}>
            <QuestionInput
              placeholder="Type a new question"
              disabled={isLoading}
              onSend={(question) => makeApiRequest(question)}
              userquestion={userQuestion}
            />
          </div>
        </div>
        <div className={styles.oneshotBottomSection}>
          {isLoading && <Spinner label="Generating answer" />}
          {!lastQuestionRef.current && (
            <ExampleList onExampleClicked={onExampleClicked} />
          )}
          {!isLoading && answer && !error && (
            <div className={styles.oneshotAnswerContainer}>
              <Answer
                answer={answer}
                onCitationClicked={(x) => onShowCitation(x)}
                onThoughtProcessClicked={() =>
                  onToggleTab(AnalysisPanelTabs.ThoughtProcessTab)
                }
                onSupportingContentClicked={() =>
                  onToggleTab(AnalysisPanelTabs.SupportingContentTab)
                }
                question={userQuestion}
                onRefreshedClicked={() => makeApiRequest(userQuestion, 1)}
              />
            </div>
          )}
          {error ? (
            <div className={styles.oneshotAnswerContainer}>
              <AnswerError
                error={error.toString()}
                onRetry={() => makeApiRequest(lastQuestionRef.current)}
              />
            </div>
          ) : null}
          {activeAnalysisPanelTab && answer && (
            <AnalysisPanel
              className={styles.oneshotAnalysisPanel}
              activeCitation={activeCitation}
              onActiveTabChanged={(x) => onToggleTab(x)}
              citationHeight="600px"
              answer={answer}
              activeTab={activeAnalysisPanelTab}
            />
          )}
        </div>

        <Panel
          headerText="Configure answer generation"
          isOpen={isConfigPanelOpen}
          isBlocking={false}
          onDismiss={() => setIsConfigPanelOpen(false)}
          closeButtonAriaLabel="Close"
          onRenderFooterContent={() => (
            <DefaultButton onClick={() => setIsConfigPanelOpen(false)}>
              Close
            </DefaultButton>
          )}
          isFooterAtBottom={true}
        >
          <Stack tokens={{ childrenGap: 10 }}>
            <div className={styles.toggleContainer}>
              <span className={styles.leftLabel}>SharePoint</span>
              <Toggle
                inlineLabel
                checked={panelType === 'upload'}
                onChange={toggleUploadSharePoint}
                className={styles.whiteColor}
                styles={{
                  thumb: {

                    backgroundColor: panelType === 'upload' ? 'green' : 'red',
                  },
                  root: {
                    backgroundColor: 'white',
                  },
                }}
              />
              <span className={styles.rightLabel}>Date Source Eryl</span>
            </div>
            {panelType === 'upload' ? (
              <>
                <ChoiceGroup
                  className={styles.oneshotSettingsSeparator}
                  label="Approach"
                  options={approaches}
                  defaultSelectedKey={approach}
                  onChange={onApproachChange}
                />

                {(approach === Approaches.RetrieveThenRead ||
                  approach === Approaches.ReadDecomposeAsk || approach === Approaches.EvaluationAgent) && (
                    <TextField
                      className={styles.oneshotSettingsSeparator}
                      defaultValue={promptTemplate}
                      label="Override prompt template"
                      multiline
                      autoAdjustHeight
                      onChange={onPromptTemplateChange}
                    />
                  )}

                {(approach === Approaches.ReadRetrieveRead) && (
                  <>
                    <TextField
                      className={styles.oneshotSettingsSeparator}
                      defaultValue={promptTemplatePrefix}
                      label="Override prompt prefix template"
                      multiline
                      autoAdjustHeight
                      onChange={onPromptTemplatePrefixChange}
                    />
                    <TextField
                      className={styles.oneshotSettingsSeparator}
                      defaultValue={promptTemplateSuffix}
                      label="Override prompt suffix template"
                      multiline
                      autoAdjustHeight
                      onChange={onPromptTemplateSuffixChange}
                    />
                  </>
                )}

                <SpinButton
                  className={styles.oneshotSettingsSeparator}
                  label="Retrieve this many documents from search:"
                  min={1}
                  max={50}
                  defaultValue={retrieveCount.toString()}
                  onChange={onRetrieveCountChange}
                />


                <Stack tokens={{ childrenGap: 5 }} style={{ marginTop: '10px' }}>
                  <span className={styles.labelWeight}>Filter Categories</span>
                  <Stack >
                    <Stack horizontal verticalAlign="center" tokens={{ childrenGap: 10 }}>
                      <span className={styles.labelWeight}>Exclude</span>
                      <Toggle
                        inlineLabel
                        checked={!isInculdeMode}
                        className={styles.whiteColor}
                        styles={{
                          thumb: {
                            backgroundColor: isInculdeMode ? 'red' : 'green'
                          },
                          root: {
                            backgroundColor: 'white'
                          }
                        }}
                        onChange={(ev, checked) => handleRadioChange(ev, !checked)}
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
                {
                  <Checkbox
                    className={styles.oneshotSettingsSeparator}
                    checked={useSemanticRanker}
                    label="Use semantic ranker for retrieval"
                    onChange={onUseSemanticRankerChange}
                  />
                  /*<Checkbox
                            className={styles.oneshotSettingsSeparator}
                            checked={useSemanticCaptions}
                            label="Use query-contextual summaries instead of whole documents"
                            onChange={onUseSemanticCaptionsChange}
                            disabled={!useSemanticRanker}
                        /> */
                }
                <Dropdown
                  className={styles.oneshotSettingsSeparator}
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
                <DefaultButton text="Fetch SharePoint Files" onClick={PullSharePoint} />
                <a href="https://affineindia.sharepoint.com/sites/ERYL-SharepointIndexer" className="sharepoint-link" target="_blank" rel="noopener noreferrer">
                  https://affineindia.sharepoint.com/sites/ERYL-SharepointIndexer
                </a>
                <div style={{ marginTop: '10px' }}>
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
  );
}

Component.displayName = "OneShot";