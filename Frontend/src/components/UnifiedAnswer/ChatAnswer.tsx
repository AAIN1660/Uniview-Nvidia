import React, { useEffect, useMemo, useState, useRef } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, LabelList, Cell } from "recharts";
import "./ChatAnswer.css";
import { Stack, IconButton, Async } from "@fluentui/react";
import {
	AnalysisPanel,
	AnalysisPanelTabs,
} from "../../components/AnalysisPanel";
import { parseAnswerToHtml } from "../Answer/AnswerParser";
import { getCitationFilePath } from "../../api";
import DOMPurify from "dompurify";
import styles from "../Answer/Answer.module.css";
import { SpeakerMute24Filled, Speaker224Filled, DocumentPdf24Filled, LightbulbFilamentRegular, ArrowDownloadRegular, ThumbLikeRegular, CopyRegular } from "@fluentui/react-icons";
import html2pdf from "html2pdf.js";
import { CaretDown24Filled, CaretUp24Filled, Download } from "@fluentui/react-icons";
import askService from "../../api/askService";
import { ClipLoader } from "react-spinners";






const ChatAnswer: React.FC<{
	answerResponse: any;
	isLoading: boolean;
	onRefresh: () => void;
	onReload:() => void;
  }> = ({ answerResponse, isLoading, onRefresh, onReload }) => {
  
	const [showSqlExplanation, setShowSqlExplanation] = useState(false);
	const [activeTab, setActiveTab] = useState("insights");
	const [activeCitation, setActiveCitation] = useState<string>();
	const [key, setKey] = useState(0);
	const [sanitizedAnswerHtml, setSanitizedAnswerHtml] = useState("");
	const [csvData, setCSVData] = useState('');
	const [downloadHref, setDownloadHref] = useState('');
	const [startspeak, setstartSpeak] = useState<Boolean>(false);
	const [synth, setSynth] = useState<any>(null);
	const [showPythonExplanation, setShowPythonExplanation] = useState(false);
	const [activeButton, setActiveButton] = useState(null);
	const [thumbsUpLoading, setThumbsUpLoading] = useState(false);
	const [thumbsDownLoading, setThumbsDownLoading] = useState(false);
	let answerId = answerResponse?.uid
	console.log(isLoading);

	console.log(answerResponse)

	const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<
		AnalysisPanelTabs | undefined
	>(undefined);


	const onThoughtProcessClicked = () => {
		onToggleTab(AnalysisPanelTabs.ThoughtProcessTab);
	}; // <-- Add semicolon here

	const onToggleTab = (tab: AnalysisPanelTabs) => {
		if (activeAnalysisPanelTab === tab) {
			setActiveAnalysisPanelTab(undefined);
		} else {
			setActiveAnalysisPanelTab(tab);
		}
	};

	const handleReload = () => {

		setKey((prevKey) => prevKey + 1); // Update the key to trigger a re-render
	};

	// const combined_context_contextString = JSON.stringify(answerResponse || "");

	// if (combined_context_contextString.includes('combined_context')) {
		
	// 	const startIdx_sources = answerResponse?.data_points?.combined_context.indexOf("'sources': [");
	// 	if (startIdx_sources !== -1) {
	// 		const endIdx_sources = answerResponse?.data_points?.combined_context.indexOf("]", startIdx_sources);
	// 		const sources_string = answerResponse?.data_points?.combined_context.substring(startIdx_sources + 10, endIdx_sources + 1);
	// 		console.log(JSON.parse(sources_string.replace(/'/g, '"')));
	// 		var sources =  JSON.parse(sources_string.replace(/'/g, '"'));

	// 	}

	// 	const startIdx_chunks = answerResponse?.data_points?.combined_context.indexOf("'chunks': [");
	// 	if (startIdx_chunks !== -1) {
	// 		const endIdx_chunks = answerResponse?.data_points?.combined_context.indexOf("], 'sources'", startIdx_chunks);
	// 		const chunks_string = answerResponse?.data_points?.combined_context.substring(startIdx_chunks + 10, endIdx_chunks + 1);
	// 		console.log(JSON.parse(chunks_string));
	// 		var chunks = JSON.parse(chunks_string);

	// 	}

	// 	var vector_context = { 
	// 		"sources" : sources,
	// 		"chunks" : chunks
							
	// 	}

    // 	console.log('vector_context_combined', vector_context);
		
	// } else {
		var vector_context = answerResponse?.data_points?.vector_context || null;
		var graph_context = answerResponse?.data_points?.graph_context || null;
		
		console.log('vector_context', vector_context);

	// }
	


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

	// const parsedAnswer = useMemo(() => parseAnswerToHtml(vector_context, onShowCitation), [answerResponse]);

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

	// useEffect(() => {
	//   const parsedAnswer = parseAnswerToHtml(answerResponse?.answer, onShowCitation);
	//   const sanitizedAnswerHtml = DOMPurify.sanitize(parsedAnswer.answerHtml);
	//   setSanitizedAnswerHtml(sanitizedAnswerHtml);
	//   const parser = new DOMParser();
	//   const doc = parser.parseFromString(sanitizedAnswerHtml, 'text/html');
	//   const tableElement = doc.querySelector('table');

	//   if (tableElement) {
	//     const tableHTML = tableElement.outerHTML;
	//     convertTableToCSV(tableHTML);
	//   }
	// }, [answerResponse]);

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

	useEffect(() => {
		let synth = window.speechSynthesis;
		setSynth(synth)
	}, [])
	const stopSpeak = (e) => {
		e.preventDefault();
		// WINDOWS DEFAULT METHOD
		if (synth) {
			synth.cancel();
			setstartSpeak(false)
		}

	}

	const handleThumbsUp = async () => {
		setThumbsUpLoading(true)
		const payload = {
			"id": answerId,
			"feedback": 1
		}
		setActiveButton((prev) => (prev === "like" ? null : "like")); // Toggle like
		const response = await askService.questionFeedback(payload);
		setThumbsUpLoading(false)

	};

	const handleThumbsDown = async () => {
		setThumbsDownLoading(true)
		const payload = {
			"id": answerId,
			"feedback": 0
		}
		setActiveButton((prev) => (prev === "dislike" ? null : "dislike")); // Toggle dislike
		const response = await askService.questionFeedback(payload);
		setThumbsDownLoading(false)

	};

	const downloadImage = () => {
		const imgSrc = answerResponse?.plot_base64;

		if (imgSrc) {
			// Create a link element
			const link = document.createElement('a');
			link.href = imgSrc;
			link.download = 'chart-image.png'; // Specify the default filename
			document.body.appendChild(link);

			// Trigger the download
			link.click();

			// Clean up
			document.body.removeChild(link);
		} else {
			console.error("Image source not found");
		}
	};

	// const handleRefresh = () => {
	// 	
    //     // Toggle the useAi value (or update it based on your logic)
    //     setUseAi(1);

    //     // Call the API request function
    //     makeApiRequest();
    // };
	
	// const clearChat =() => {
	// 	answerResponse?.python_code = null
	// }

	
	const handleClick = () => {
		console.log("Refresh button clicked");
		if (onRefresh) {
		  onRefresh(); // Call the parent function
		} else {
		  console.error("onRefresh function is not defined.");
		}
	}

	const handleChatRefresh = () => {
		onReload()
	}

	const copyToClipboard = (text) => {
		navigator.clipboard.writeText(text).then(() => {
		}).catch(err => {
		  console.error("Failed to copy text: ", err);
		});
	  };
	
	
	
	
	



	return (

		<div className="chat-answer-container">
			{/* Insights Section */}
			<div className="insights-section">
				{/* Tabs and Icons Row */}
				<div className="tabs-icons-row">
					<div className="tab-container">
						<div
							className={`tab ${activeTab === "insights" ? "active" : ""}`}
							onClick={() => setActiveTab("insights")}
						>
							Insights
						</div>
						{answerResponse?.python_code && (
							<div
								className={`tab ${activeTab === "python" ? "active" : ""}`}
								onClick={() => setActiveTab("python")}
							>
								Python Code
							</div>
						)}

					</div>

					<div className="icon-container">
					{answerResponse?.dbresponse !== undefined  && answerResponse?.dbresponse == 0 ?
						<div>
                        <em data-toggle="tooltip" data-placement="top" title="This response has been generated from AI" style={{ fontSize: '18px', padding: '0px', borderRadius: '5px', color: 'rgb(61,61,61)' }} className="darkericons fas fa-robot"></em>
                    </div> : <div>
                        <em data-toggle="tooltip" data-placement="top" title="This response has been generated from database." style={{ fontSize: '18px', padding: '0px', borderRadius: '5px', color: 'rgb(61,61,61)', marginRight: '8px', marginTop: '4px' }} className="darkericons fa fa-database"></em>
                    </div>
					}
						{!startspeak ? (
							activeTab === "python" ? (
								<Speaker224Filled
									onClick={(e) => speakText(e, answerResponse?.python_code)}
									primaryFill="rgb(61,61,61)"
									className={styles.speaker_container}
								/>
							) : (
								<Speaker224Filled
									onClick={(e) => speakText(e, answerResponse?.answer.final_answer[0].text + answerResponse?.answer.final_answer[1].text)}
									primaryFill="rgb(61,61,61)"
									className={styles.speaker_container}
								/>
							)
						) : (
							<SpeakerMute24Filled
								onClick={stopSpeak}
								primaryFill="rgb(61,61,61)"
								className={styles.speaker_container}
							/>
						)}

						<IconButton
							style={{ color: "black", marginTop: "-3px", zIndex: "1001" }}
							iconProps={{ iconName: "Lightbulb" }}
							title="Show thought process"
							ariaLabel="Show thought process"
							onClick={() => onThoughtProcessClicked()}
							disabled={!answerResponse?.thoughts}
							onRenderIcon={() => <LightbulbFilamentRegular style={{ fontSize: 24 }} />}
						/>
					</div>
				</div>
			</div>

			<div className="text-section mb-1">
			
				{activeTab === "insights" && (
					

					<ul style={{ padding: "0 0.8rem" }}>
					{/* Split by newline for better formatting */}
					{answerResponse?.answer && 
					Array.isArray(answerResponse?.answer.final_answer) &&
					answerResponse?.answer.final_answer.map((item, index) => (
						item.text.split(/\n+/).map((sentence, i) => (
							<li 
								key={`answer-${index}-${i}`} 
								style={{ color: item.type === "llm" ? "#7815bf" : "#cf2035" }}
							>
								{sentence.trim()}
							</li>
						))
					))
				}


					</ul>

				)}

				{activeTab === "python" && (
					<p className="python-code">{answerResponse?.python_code}</p>
				)}
				
			</div>


			{/* Chart Section */}
			{answerResponse?.plot_base64 && activeTab === "insights" && (<div className="chart-section mt-2">
				<span className="download-arrow-icon" onClick={() => downloadImage()}>
					<ArrowDownloadRegular style={{ color: "black" }} />
				</span>

				<img className="grpahimage" src={`${answerResponse?.plot_base64}`} />


			</div>)}

			{/* SQL Query Section */}
			{answerResponse?.sql_query && activeTab === "insights" && (<div className="sql-section mt-2">
				<div style={{
					float: "right",
					top: "16px",
					right: "22px",
					position: "relative"
				}}>
					{startspeak == false ? <Speaker224Filled onClick={(e) => speakText(e, answerResponse?.sql_query)} primaryFill="rgb(255, 255, 255)" className={styles.speaker_container} /> :
						<SpeakerMute24Filled onClick={stopSpeak} primaryFill="rgb(255, 255, 255)" className={styles.speaker_container} />
					}
					<span style={{ bottom: "4px", position: "relative", left: "5px", cursor: "pointer" }} onClick={() => copyToClipboard(answerResponse?.sql_query)}
					>
						<CopyRegular primaryFill="rgb(255, 255, 255)" style={{ fontSize: "x-large" }} />

					</span>
				</div>

				<p className="p-3" style={{color:"white", fontSize:"14px"}}>{answerResponse?.sql_query}</p>
			</div>)}



			{/* Interactive Section */}
			<div className="interactive-section mt-2">
				{answerResponse?.sql_explanation && activeTab === "insights" && (
					<div className="explanation-bar">
						<div
							className="explanation-header"
							onClick={() => setShowSqlExplanation(!showSqlExplanation)}
						>
							<p className="code-explanation">View Code Explanation</p>
							<div className="icon-wrapper">
								{showSqlExplanation ? (
									<CaretUp24Filled aria-label="Collapse" style={{ color: "white" }} />
								) : (
									<CaretDown24Filled aria-label="Expand" style={{ color: "white" }} />
								)}
							</div>
						</div>
						{showSqlExplanation && (
							<div className="sql-explanation">
								<p>{answerResponse?.sql_explanation}</p>
							</div>
						)}
					</div>
				)}

				{answerResponse?.python_code_explanation && activeTab === "python" && (
					<div className="explanation-bar">
						<div
							className="explanation-header"
							onClick={() => setShowPythonExplanation(!showPythonExplanation)}
						>
							<p className="code-explanation">View Code Explanation</p>
							<div className="icon-wrapper">
								{showPythonExplanation ? (
									<CaretUp24Filled aria-label="Collapse" className="collapse" style={{ color: "white" }} />
								) : (
									<CaretDown24Filled aria-label="Expand" className="expand" style={{ color: "white" }} />
								)}
							</div>
						</div>
						{showPythonExplanation && (
							<div className="sql-explanation">
								<p>{answerResponse?.python_code_explanation}</p>
							</div>
						)}
					</div>
				)}


			</div>

			{/* {citation part} */}
			{!!vector_context?.sources?.length && (
				<div className="citations-container">
					<span className="citations-title">Citations:</span>
					<div className="citations-list">
						{vector_context.sources.map((source, index) => {
							
							const path = getCitationFilePath(source);

							return (
								<a
									key={index}
									className="citation-link"
									title={source}
									onClick={() => onShowCitation(path)}
								>
									{`${index + 1}. ${source}`}
								</a>
							);
						})}
					</div>
				</div>
			)}

			<div className="row">
				<div className="col-6">
					<div className="icon-section">
						<div className="actions ps-3">
							<button className="icon-button" onClick={handleThumbsUp}>
								<i
									className={`fa-regular fa-thumbs-up ${activeButton === "like" ? "green" : ""}`}
									style={{ color: activeButton === "like" ? "green" : "inherit" }}
								></i> {thumbsUpLoading &&
									<span style={{ marginTop: '-2px' }}>
										<ClipLoader size={"11px"} />
									</span>
								}
							</button>

							<button className="icon-button" onClick={handleThumbsDown}>
								<i
									className={`fa-regular fa-thumbs-down ${activeButton === "dislike" ? "red" : ""}`}
									style={{ color: activeButton === "dislike" ? "red" : "inherit" }}
								></i>
								{thumbsDownLoading &&
													<span style={{ marginTop: '-2px' ,marginLeft:"6px"}}><ClipLoader size={"11px"} /> </span>}
							</button>

							{answerResponse?.dbresponse !== undefined  && answerResponse?.dbresponse == 1  && <button className="icon-button" onClick={handleClick}>
								<i className="fa-solid fa-rotate-right"></i>
							</button>}
						</div>

					</div>
				</div>
				<div className="col-6 ps-5" style={{ display:"flex" }}>


					<button className="link-button  ps-3 clear-chat-style" onClick={handleChatRefresh} >
						<i className="fas fa-trash"></i> <span className="clear-icon">Clear Chat</span>
					</button>


					<button className="link-button ms-2" onClick={() => downloadPdfFile(answerResponse?.thoughts)} style={{float:"right"}}>
						<i className="fas fa-file-download"></i> <span className="download-icon" >Download PDF</span>
					</button>




				</div>
			</div>


			{activeAnalysisPanelTab && answerResponse && (
				<AnalysisPanel
					className="oneshotAnalysisPanel"
					activeCitation={activeCitation}
					onActiveTabChanged={(x) => onToggleTab(x)}
					citationHeight="600px"
					answer={answerResponse}
					activeTab={activeAnalysisPanelTab}
					vector_context={vector_context}
					graph_context={graph_context}
				/>
			)}
		</div>
	);
}


export default ChatAnswer;
