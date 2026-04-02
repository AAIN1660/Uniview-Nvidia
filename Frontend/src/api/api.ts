import { AskRequest, WorkflowAskRequest, AskResponse, ChatRequest, updateFeedBackRequest } from "./models";
import axios from 'axios'
let baseURL = import.meta.env.VITE_APP_API_URL

export async function askApi(email:string, options: AskRequest, useai: number): Promise<AskResponse> {
  const response = await fetch(baseURL+"/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      question: options.question,
      approach: options.approach,
      email: email,
      index_type:options.index_type,
      overrides: {
        retrieval_mode: options.overrides?.retrievalMode,
        semantic_ranker: options.overrides?.semanticRanker,
        semantic_captions: options.overrides?.semanticCaptions,
        top: options.overrides?.top,
        temperature: options.overrides?.temperature,
        prompt_template: options.overrides?.promptTemplate,
        prompt_template_prefix: options.overrides?.promptTemplatePrefix,
        prompt_template_suffix: options.overrides?.promptTemplateSuffix,
        include_category: options.overrides?.include_category,
        category_status_flag: options.overrides?.category_status_flag,
        summarize: options.overrides?.summarize,
        batchThreshold: options.overrides?.batchThreshold
      },
      useai: useai
    })
  });

  const parsedResponse: AskResponse = await response.json();
  if (response.status > 299 || !response.ok) {
    throw Error(parsedResponse.error || "Unknown error");
  }

  return parsedResponse;
}

export async function workflowAskApi(email:string, options: WorkflowAskRequest, useai: number): Promise<AskResponse> {
  const response = await fetch(baseURL+"/workflow_ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      question: options.question,
      approach: options.approach,
      email: email,
      overrides: {
        retrieval_mode: options.overrides?.retrievalMode,
        semantic_ranker: options.overrides?.semanticRanker,
        semantic_captions: options.overrides?.semanticCaptions,
        top: options.overrides?.top,
        temperature: options.overrides?.temperature,
        prompt_template: options.overrides?.promptTemplate,
        prompt_template_prefix: options.overrides?.promptTemplatePrefix,
        prompt_template_suffix: options.overrides?.promptTemplateSuffix,
        include_category: options.overrides?.include_category
      },
      useai: useai
    })
  });

  const parsedResponse: AskResponse = await response.json();
  if (response.status > 299 || !response.ok) {
    throw Error(parsedResponse.error || "Unknown error");
  }

  return parsedResponse;
}

export async function chatApi(email: string,options: ChatRequest): Promise<AskResponse> {
  const response = await fetch(baseURL+"/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      history: options.history,
      approach: options.approach,
      email: email,
      index_type:options.index_type,
      overrides: {
        retrieval_mode: options.overrides?.retrievalMode,
        semantic_ranker: options.overrides?.semanticRanker,
        semantic_captions: options.overrides?.semanticCaptions,
        top: options.overrides?.top,
        temperature: options.overrides?.temperature,
        prompt_template: options.overrides?.promptTemplate,
        prompt_template_prefix: options.overrides?.promptTemplatePrefix,
        prompt_template_suffix: options.overrides?.promptTemplateSuffix,
        include_category: options.overrides?.includeCategory,
        category_status_flag: options.overrides?.category_status_flag,
        suggest_followup_questions: options.overrides?.suggestFollowupQuestions
            }
    })
  });

  const parsedResponse: AskResponse = await response.json();
  if (response.status > 299 || !response.ok) {
    throw Error(parsedResponse.error || "Unknown error");
  }

  return parsedResponse;
}

export async function updateFeedBack(options: updateFeedBackRequest): Promise<AskResponse> {
  // const payload = new FormData();
  // payload.append("id", options.id);
  // payload.append("feedback", options.feedback);
  const response = await fetch(baseURL+"/documentService/questionFeedback", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      id: options.id,
      feedback: options.feedback
    })
  });

  const parsedResponse: AskResponse = await response.json();
  if (response.status > 299 || !response.ok) {
    throw Error(parsedResponse.error || "Unknown error");
  }

  return parsedResponse;
}

export function getCitationFilePath(filename): string {
  
      // Split the string by the comma
      // console.log('filename', filename)
      // const parts = filename.split('.');
      // console.log('====================================');
      // console.log(baseURL);
      // console.log('====================================');
      // const page_number = parseInt(parts[0].split('-').slice(-1)[0])+1;
      // // const page_number = 0;
      console.log('filename:', filename);

      // Extract the part before the last '.'
      const nameWithoutExt = filename.substring(0, filename.lastIndexOf('.'));

      console.log('Processed Name:', nameWithoutExt);

      // Extract the last numeric part after '-'
      const lastPart = nameWithoutExt.split('-').slice(-1)[0];

      console.log('Last Part:', lastPart);

      // Convert to integer and increment
      const page_number = parseInt(lastPart, 10) + 1;

      console.log('Page Number:', page_number);
      const blob_name = filename;

  return `${baseURL}/citationPdf?blob_name=${blob_name}&page_number=${page_number}`;
}
