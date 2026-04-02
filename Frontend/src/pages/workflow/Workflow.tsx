import React from 'react';
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
} from "@fluentui/react";
import {
    workflowAskApi,
    Approaches,
    AskResponse,
    AskRequest,
    RetrievalMode,
    updateFeedBack,
    updateFeedBackRequest,
} from "../../api";
import { Answer, AnswerError, AnswerLoading } from "../../components/Answer";
import {
    AnalysisPanel,
    AnalysisPanelTabs,
} from "../../components/AnalysisPanel";
import { Eye16Filled } from '@fluentui/react-icons';
import Button from "react-bootstrap/Button";
import { MultiSelect } from "react-multi-select-component";
import { SettingsButton } from '../../components/SettingsButton';
import { trackPromise } from "react-promise-tracker";
import categoryService from "../../api/categoryService";
import useCredit from "../../api/userCredit";
import UploadFilesWorkflow from './UploadFilesWorkflow';

import "./Workflow.scss";
import LoadingOverlay from '../../components/LoadingOverlay/LoadingOverlay';

const prompts = [
    {
        "title": "Tabularizing resumes",
        "value": "For all the resumes without missing any, please give me the names of the candidates, number of years they have worked for and the key skill sets they have mentioned in their work experience without missing any companies or institutions they have worked in, in a tabular format."
    },
    {
        "title": "Screening resumes",
        "value": "Please provide a summary of the candidates, including their names, a recommendation on whether to interview them for the role described in the JD file, and the rationale behind each recommendation. The recommendation should consider whether the candidates have sufficient work experience, some team lead experience, and if their core skills at least partially match the job description. Present this information in a table format."
    },
    {
        "title": "Interview assistance",
        "value": "Based on the JD provided, please give me a list of 5 questions to ask each of the candidates recommended for interview. The objective of the interview is to ensure that the candidate does have the skills and experience as they claim in the resume."
    }
]

const Workflow = () => {
    const [showAddDataset, setShowAddDataset] = useState(false);

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();
    const [answer, setAnswer] = useState<AskResponse>();
    const [userQuestion, setUserQuestion] = useState<string>("");
    const [categoryOptions, setCategoryOptions] = useState([]);
    const [categoryOptionsLoading, setCategoryOptionsLoading] = useState(true);
    const [selectedCategory, setSelectedCategory] = useState([]);
    const lastQuestionRef = useRef<string>("");
    const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);

    const [activeCitation, setActiveCitation] = useState<string>();
    const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<
        AnalysisPanelTabs | undefined
    >(undefined);

    const [selectedAnswer, setSelectedAnswer] = useState<number>(0);
    const [answers, setAnswers] = useState<
        [user: string, response: AskResponse][]
    >([]);
    const [categoryList, setcategoryList] = useState<any>([]);
    const [excludeCategory, setExcludedCategory] = useState<any>([]);
    const { creditBalance, setCreditBalance } = useCredit()

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

    useEffect(() => getCategoryList(), []);

    const getCategoryList = () => {
        const email = localStorage.getItem('email');
        trackPromise(
            categoryService.getCategory({ email: email, type: "user" }).then((res) => {
                let existingCategory = [];
                let catergoryList = [...res?.data?.CategoryList];
                setcategoryList(catergoryList);
                let categoryOptions: any = [];
                catergoryList.forEach((category) => {
                    const option = {
                        label: category.category_name,
                        value: category.id,
                    }
                    if (category.category_name === "Recruitment") {
                        setSelectedCategory([option]);
                    }
                    categoryOptions.push(option);
                });
                setCategoryOptions(categoryOptions);
                setCategoryOptionsLoading(false);
            }).catch(err => setCategoryOptionsLoading(false))
        );
    };

    const makeApiRequest = async (question: string, useai: number = 0) => {
        error && setError(undefined);
        try {

            if (creditBalance <= 0) {
                // Display an alert indicating insufficient balance
                alert('Insufficient balance. Please recharge your account.');
                return;
            }
            else if (selectedCategory.length < 1) {
                alert("Please choose category")
            }
            else {
                lastQuestionRef.current = question;
                setUserQuestion(question);
                setIsLoading(true);
                const email = localStorage.getItem('email');
                const request = {
                    email: email,
                    question,
                    approach: "rtr",
                    overrides: {
                        include_category: [selectedCategory[0]?.value],
                        top: 9,
                        retrievalMode: "hybrid",
                        semanticRanker: false,
                        semanticCaptions: false,
                    },
                };
                const result = await workflowAskApi(email, request, useai);
                setCreditBalance(result?.balance)
                setAnswer(result);

            }

        } catch (e) {
            setError(e);
        } finally {
            setIsLoading(false);
        }
    };

    const _onButtonClick = () => {
        setShowAddDataset(true);
    };


    const clearState = (datasetName) => {
        setShowAddDataset(false);
    };

    return (
        <div className='workflow'>
            <div className="workflow_sidebar">
                <p className='sidebar_header'>Saved Workflows</p>
                <div className='sidebar_content'>
                    {prompts.map(prompt => (
                        <a
                            className={`prompt ${categoryOptionsLoading ? '' : 'pointer'} ${lastQuestionRef.current === prompt.title ? 'selected_prompt' : ''}`}
                            onClick={() => makeApiRequest(prompt.value)}
                            aria-disabled={setCategoryOptionsLoading}
                        >
                            {prompt.title}
                            <a title={prompt.value} ><Eye16Filled /></a>
                        </a>
                    ))}
                </div>
            </div>
            <div className="workflow_content">
                <div className="d-flex mb-2" style={{ justifyContent: "center", alignItems: 'center' }}>
                    <h4 className="ml-8" >Category</h4>
                    <MultiSelect
                        options={categoryOptions}
                        value={selectedCategory}
                        onChange={(val => {
                            // only sending the last object as we r modifying multi select to single select
                            setSelectedCategory([val[val.length - 1]])
                        })}
                        labelledBy="Select"
                        hasSelectAll={false}
                        ClearIcon={null}
                        ClearSelectedIcon={null}
                        isLoading={categoryOptionsLoading}
                        disabled={true}
                        closeOnChangedValue
                        className='ml-8'
                    />
                </div>
                <div className="chatMessageStream">
                    {!isLoading && answer && !error && (
                        <div className="oneshotAnswerContainer">
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
                    {activeAnalysisPanelTab && answer && (
                        <AnalysisPanel
                            className="oneshotAnalysisPanel"
                            activeCitation={activeCitation}
                            onActiveTabChanged={(x) => onToggleTab(x)}
                            citationHeight="600px"
                            answer={answer}
                            activeTab={activeAnalysisPanelTab}
                        />
                    )}
                    {isLoading && (
                        <>
                            <div className="chatMessageGptMinWidth">
                                <AnswerLoading />
                            </div>
                        </>
                    )}
                    {error ? (
                        <>
                            <div className="chatMessageGptMinWidth">
                                <AnswerError
                                    error={error.toString()}
                                    onRetry={() => makeApiRequest(lastQuestionRef.current)}
                                />
                            </div>
                        </>
                    ) : null}
                    <div ref={chatMessageStreamEnd} />
                </div>
            </div>
        </div>
    )
}

export default Workflow;