import { useEffect, useMemo, useState } from "react";
import { Stack, IconButton, Async } from "@fluentui/react";
import DOMPurify from "dompurify";
import React from "react";
import { jsPDF } from "jspdf";
import html2pdf from "html2pdf.js";
import { ClipLoader } from "react-spinners";
import styles from "./Answer.module.css";
import { SpeakerMute24Filled, Speaker224Filled, DocumentPdf24Filled } from "@fluentui/react-icons";
import { AskResponse, getCitationFilePath, updateFeedBack, updateFeedBackRequest } from "../../api";
import { parseAnswerToHtml } from "./AnswerParser";
import { AnswerIcon } from "./AnswerIcon";
import * as sdk from 'microsoft-cognitiveservices-speech-sdk';

interface Props {
    answer: AskResponse;
    isSelected?: boolean;
    onCitationClicked: (filePath: string) => void;
    onThoughtProcessClicked: () => void;
    onSupportingContentClicked: () => void;
    onFollowupQuestionClicked?: (question: string) => void;
    showFollowupQuestions?: boolean;
    question: string,
    onRefreshedClicked: (question: string) => void;
}

export const Answer = ({
    answer,
    isSelected,
    onCitationClicked,
    onThoughtProcessClicked,
    onSupportingContentClicked,
    onFollowupQuestionClicked,
    showFollowupQuestions,
    question,
    onRefreshedClicked
}: Props) => {
    const AZUREAPIKEY = import.meta.env.VITE_AZURE_SPEECH_KEY;
    const REGION = import.meta.env.VITE_AZURE_OPENAI_API_REGION;
    const [synth, setSynth] = useState<any>(null);
    const [startspeak, setstartSpeak] = useState<Boolean>(false);
    const [csvData, setCSVData] = useState('');
    const [answerStatus, setAnswerStatus] = useState<number>(0);
    const [sanitizedAnswerHtml, setSanitizedAnswerHtml] = useState("");
    const [downloadHref, setDownloadHref] = useState('');
    const [thumbsUpLoading, setThumbsUpLoading] = useState(false);
    const [thumbsDownLoading, setThumbsDownLoading] = useState(false);

    const convertTableToCSV = (tableContent) => {

        // Create a temporary element to parse the HTML content
        const tempElement = document.createElement('div');
        tempElement.innerHTML = tableContent;

        // Find the table element in the parsed HTML
        const table = tempElement.querySelector('table');

        // Initialize a CSV string
        let csvString = '';

        // Extract data from each row in the table
        table.querySelectorAll('tr').forEach((row) => {
            const rowData = Array.from(row.children)
                .map((cell) => {
                    // Replace commas in cell content with double quotes
                    const cellText = cell.innerText.replace(/,/g, '\,');
                    return `"${cellText}"`;
                })
                .join(',');

            csvString += rowData + '\n';
        });

        // Update state with the CSV data
        setCSVData(csvString);

        // Optionally, you can save the CSV data to a file or perform any other action
        // For example:
        const blob = new Blob([csvString], { type: 'text/csv' });
        setDownloadHref(window.URL.createObjectURL(blob));
    };

    useEffect(() => {
        const parsedAnswer = parseAnswerToHtml(answer.answer, onCitationClicked);
        const sanitizedAnswerHtml = DOMPurify.sanitize(parsedAnswer.answerHtml);
        setSanitizedAnswerHtml(sanitizedAnswerHtml);
        const parser = new DOMParser();
        const doc = parser.parseFromString(sanitizedAnswerHtml, 'text/html');
        const tableElement = doc.querySelector('table');

        if (tableElement) {
            const tableHTML = tableElement.outerHTML;
            convertTableToCSV(tableHTML);
        }
    }, [answer]);


    const extractArrayContent = (string) => {
        // Check if the string is null or undefined
        if (string === null || string === undefined) {
            return null;
        }

        // Define a regular expression pattern to match content inside square brackets
        const pattern = /\[(.*?)\]/;

        // Use RegExp.prototype.exec() to find the first occurrence of the pattern in the string
        const matches = pattern.exec(string);

        // Regular expression to match the filename
        const regex = /[^\/]+\.pdf\b/i;

        // Check if the string matches the regex pattern
        if (typeof string === 'string') {
            // Match the filename using the regular expression
            const matches2 = string.match(regex);

            if (matches && matches.length > 1) {
                return matches[1]; // Return the content inside square brackets
            } else if (matches2 && matches2.length > 0) {
                return matches2[0]; // Return the extracted document name
            }
        }

        return ''; // Neither array nor filename found, return null
    }


    // let getPageNumber = (filename:any) => {
    //     // Get the base name of the file without extension
    //     console.log('filename', filename)

    //     if(filename == null) {
    //       return 0
    //     } else {
    //     const baseName = filename.split('.')[0];
    //     // Split the base name using '-' as delimiter and return the last part
    //     const parts = baseName.split('-');
    //     return parts[parts.length - 1];
    //     }      
    // }



    // const citation_file_name = extractArrayContent(answer.answer);




    // let page_number = getPageNumber(citation_file_name)

    // let page_number = 0


    // Regular expression pattern to capture the part before "-X.pdf" where X can be any number
    // const regex = /^(.?)-\d+\.pdf/;

    // Extract the part before "-X.pdf"
    // if(citation_file_name) {
    // const match = citation_file_name.match(regex);

    // // Check if a match is found
    // if (match) {
    //     // Retrieve the captured part
    //     var blob_name = match[1];
    //     blob_name = blob_name + '.pdf';
    //     // console.log(prefix);
    // } else {
    //     blob_name = ''
    // }
    // } else {
    //     blob_name = ''
    // }



    const removeSourceText = (inputText) => {
        // Remove text within square brackets
        let textWithoutSquareBrackets = inputText.replace(/\[.*?\]/g, '');

        // Remove text within parentheses
        let textWithoutParentheses = textWithoutSquareBrackets.replace(/\(.*?\)/g, '');

        // Remove leading and trailing whitespace
        let finalText = textWithoutParentheses.trim();

        return finalText;
    }

    var cleanedtext = removeSourceText(answer.answer)

    const parsedAnswer = useMemo(() => parseAnswerToHtml(answer.answer, onCitationClicked), [answer]);

    const makeUpdateFeedbackApiRequest = async (id: string, feedback: number = 0) => {
        try {
            const request: updateFeedBackRequest = {
                id,
                feedback
            };
            if (feedback == 1) {
                setThumbsUpLoading(true);
            } else {
                setThumbsDownLoading(true);
            }
            const result = await updateFeedBack(request);
            setAnswerStatus(feedback);
            if (feedback == 1) {
                setThumbsUpLoading(false);
            } else {
                setThumbsDownLoading(false);
            }
        } catch (e) {

        }
    };
    useEffect(() => {
        let synth = window.speechSynthesis;
        setSynth(synth)

        //   return ()=>{
        //     setSynth(null)
        //   }
        //   const speechConfig = sdk.SpeechConfig.fromSubscription(AZUREAPIKEY, REGION);
        //   speechConfig.speechRecognitionLanguage = "en-US";
        //   speechConfig.speechSynthesisVoiceName = "en-US-JennyNeural";

        //   const audioConfig = sdk.AudioConfig.fromDefaultSpeakerOutput();
        //   const synthesizer = new sdk.SpeechSynthesizer(speechConfig, audioConfig);

        //   setSynth(synthesizer)
    }, [])

    const speakText = async (e, text: string) => {
        e.preventDefault();
        if (synth) {
            setstartSpeak(true)
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.voice = speechSynthesis.getVoices().filter(function (voice) {
                // return voice.name == "Google UK English Female"
                return voice.name == "Microsoft Zira - English (United States)"

            })[0];
            synth.speak(utterance);
        }

    };

    const stopSpeak = (e) => {
        e.preventDefault();
        // WINDOWS DEFAULT METHOD
        if (synth) {
            synth.cancel();
            setstartSpeak(false)
        }

    }

    const downloadPdfFile = (content) => {
        // Create a temporary element
        const tempElement = document.createElement("div");
        const titleElement = document.createElement("h1");
        titleElement.innerText = "Evaluation Agent Thought Process"; // Set your title text

        // Add styles to the title element for centering
        titleElement.style.textAlign = "center"; // Center the title
        titleElement.style.marginBottom = "40px";
        titleElement.style.zIndex = "-100";

        tempElement.innerHTML = content; // Inject the mixed content
        0
        // Add styles to the temporary element
        tempElement.style.padding = "40px"; // Add padding around the content
        tempElement.style.margin = "0"; // Ensure no margins
        tempElement.style.width = "100%"; // Ensure full width
        tempElement.style.zIndex = "-100";

        // Append the title to the temporary element
        tempElement.prepend(titleElement);

        const options = {
            margin: 1,
            filename: 'evaluation_agent_thought_process.pdf',
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2 },
            jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' },
        };

        // Generate PDF from the temporary element
        html2pdf()
            .from(tempElement)
            .set(options)
            .save()
    };

    return (
        <Stack className={`${styles.answerContainer} ${isSelected && styles.selected}`} verticalAlign="space-between">
            <Stack.Item>
                <Stack horizontal horizontalAlign="space-between">
                    {answer?.dbresponse != undefined ? answer?.dbresponse == 0 ? <div>
                        <em data-toggle="tooltip" data-placement="top" title="This response has been generated from AI" style={{ fontSize: '20px', padding: '0px', borderRadius: '5px', color: 'rgb(115, 118, 225)' }} className="darkericons fas fa-robot"></em>
                    </div> : <div>
                        <em data-toggle="tooltip" data-placement="top" title="This response has been generated from database." style={{ fontSize: '16px', padding: '0px', borderRadius: '5px', color: 'rgb(115, 118, 225)', marginRight: '16px' }} className="darkericons fa fa-database"></em>
                    </div>
                        : <AnswerIcon />}
                    <div>
                        {startspeak == false ? <Speaker224Filled onClick={(e) => speakText(e, sanitizedAnswerHtml)} primaryFill="rgba(115, 118, 225, 1)" className={styles.speaker_container} /> :
                            <SpeakerMute24Filled onClick={stopSpeak} primaryFill="#fa3d37" className={styles.speaker_container} />
                        }
                        {answer.dbresponse == 1 && <em
                            className={`fa-solid fa-arrows-rotate darkericons ${styles.refreshicon}`}
                            data-toggle="tooltip" data-placement="top" title="This response has been generated from database, click here to fetch response from AI for the same query."
                            onClick={onRefreshedClicked}
                        ></em>}

                        <IconButton
                            style={{ color: "black" }}
                            iconProps={{ iconName: "Lightbulb" }}
                            title="Show thought process"
                            ariaLabel="Show thought process"
                            onClick={() => onThoughtProcessClicked()}
                            disabled={!answer.thoughts}
                        />
                        {answer?.agent_chat && <IconButton
                            style={{ color: "black" }}
                            iconProps={{ iconName: "PDF" }}
                            title="Download thought process"
                            ariaLabel="Download thought process"
                            onClick={() => downloadPdfFile(answer?.agent_chat)}
                            disabled={!answer.agent_chat}
                        />}
                        <IconButton
                            style={{ color: "black" }}
                            iconProps={{ iconName: "ClipboardList" }}
                            title="Show supporting content"
                            ariaLabel="Show supporting content"
                            onClick={() => onSupportingContentClicked()}
                            disabled={!answer.data_points.length}
                        />
                        {downloadHref && (
                            <IconButton
                                style={{ color: "black" }}
                                iconProps={{ iconName: "Download" }}
                                title="Export to CSV"
                                ariaLabel="Export to CSV"
                                onClick={() => {
                                    if (downloadHref) {
                                        const link = document.createElement('a');
                                        link.href = downloadHref;
                                        link.download = 'table_data.csv';
                                        link.click();
                                    }
                                }}
                            />
                        )
                        }
                    </div>
                </Stack>
            </Stack.Item>

            <Stack.Item grow>
                <div className={styles.answerText} dangerouslySetInnerHTML={{ __html: sanitizedAnswerHtml }}></div>
            </Stack.Item>

            {!!parsedAnswer.citations.length && (
                <Stack.Item>
                    <Stack horizontal wrap tokens={{ childrenGap: 5 }}>
                        <span className={styles.citationLearnMore}>Citations:</span>
                        {parsedAnswer.citations.map((x, i) => {
                            const path = getCitationFilePath(x);
                            return (
                                <a key={i} className={styles.citation} title={x} onClick={() => onCitationClicked(path)}>
                                    {`${i + 1}. ${x}`}
                                </a>
                            );
                        })}
                    </Stack>
                </Stack.Item>
            )}

            {!!parsedAnswer.followupQuestions.length && showFollowupQuestions && onFollowupQuestionClicked && (
                <Stack.Item>
                    <Stack horizontal wrap className={`${!!parsedAnswer.citations.length ? styles.followupQuestionsList : ""}`} tokens={{ childrenGap: 6 }}>
                        <span className={styles.followupQuestionLearnMore}>Follow-up questions:</span>
                        {parsedAnswer.followupQuestions.map((x, i) => {
                            return (
                                <a key={i} className={styles.followupQuestion} title={x} onClick={() => onFollowupQuestionClicked(x)}>
                                    {`${x}`}
                                </a>
                            );
                        })}
                    </Stack>
                </Stack.Item>
            )}
            {answer?.dbresponse !== undefined && answer?.dbresponse === 0 && <div className={styles.feedbackicons}>
                <em
                    style={{ width: 'fit-content', paddingRight: `${thumbsUpLoading ? '5px' : '15px'}` }}
                    className={
                        answerStatus === 1
                            ? "fa fa-thumbs-up thumbStyle text-success"
                            : "fa fa-thumbs-o-up thumbStyle text-success"
                    }
                    onClick={() => {
                        makeUpdateFeedbackApiRequest(answer.uid, 1);
                    }}
                ></em>
                {thumbsUpLoading &&
                    <span style={{ marginTop: '-2px' }}>
                        <ClipLoader size={"11px"} />
                    </span>
                }
                <em
                    style={{ width: 'fit-content', paddingRight: `${thumbsDownLoading ? '5px' : '15px'}`, paddingLeft: '15px' }}
                    className={
                        answerStatus === -1
                            ? "fa fa-thumbs-down thumbStyle text-danger"
                            : "fa fa-thumbs-o-down thumbStyle text-danger"
                    }
                    onClick={() => {
                        makeUpdateFeedbackApiRequest(answer.uid, -1);
                    }}
                ></em>
                {thumbsDownLoading &&
                    <span style={{ marginTop: '-2px' }}><ClipLoader size={"11px"} /> </span>}
            </div>}

        </Stack >
    );
};