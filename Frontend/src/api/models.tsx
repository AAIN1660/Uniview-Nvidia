export const enum Approaches {
    RetrieveThenRead = "rtr",
    // ReadRetrieveRead = "rrr",
    // ReadDecomposeAsk = "rda",
    RetrieveThenReadBatch = 'rtrb',
    RetrieveThenReadBatchThreshold = 'rtrbt',
    RetrieveThenReadBatchPercentiles = 'rtrbp',
    EvaluationAgent = 'eval'
}

export const enum RetrievalMode {
    Hybrid = "hybrid",
    Vectors = "vectors",
    Text = "text"
}

export type AskRequestOverrides = {
    retrievalMode?: RetrievalMode;
    semanticRanker?: boolean;
    semanticCaptions?: boolean;
    excludeCategory?: string;
    includeCategory?: string;
    top?: number;
    temperature?: number;
    promptTemplate?: string;
    promptTemplatePrefix?: string;
    promptTemplateSuffix?: string;
    suggestFollowupQuestions?: boolean;
    include_category?:any;
    category_status_flag?:any;
    summarize?:any;
    batchThreshold?:any;
};

export type AskRequest = {
    index_type: any;
    question: string;
    approach: Approaches;
    overrides?: AskRequestOverrides;
};

export type updateFeedBackRequest = {
    id: string,
    feedback: number
}

export type AskResponse = {
    answer: string;
    thoughts: string | null;
    data_points: string[];
    error?: string;
    agent_chat?: string;
};

export type ChatTurn = {
    user: string;
    bot?: string;
};

export type ChatRequest = {
    index_type: any;
    history: ChatTurn[];
    approach: Approaches;
    overrides?: AskRequestOverrides;
};
